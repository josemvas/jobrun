# -*- coding: utf-8 -*-
from time import sleep
from shutil import copyfile
from os import path, execv, getcwd
from subprocess import call, DEVNULL, CalledProcessError
from importlib import import_module
from getpass import getuser 
from . import dialogs
from . import messages
from .exceptions import NotAbsolutePath, InputFileError
from .jobparse import cluster, remote, jobspecs, options, files
from .utils import pathjoin, remove, makedirs, alnum, natsort, p, q, sq, catch_keyboard_interrupt
from .jobdigest import keywords, jobcomments, environment, commandline, parameters, head, node
from .classes import Bunch, AbsPath, IdentityList
from .boolparse import BoolParser

def nextfile():
    
    file = files.pop(0)

    try:
        filepath = AbsPath(file)
    except NotAbsolutePath:
        filepath = AbsPath(getcwd(), file)

    inputdir = filepath.parent()
    basename = filepath.name
    
    if filepath.isfile():
        for key in (k for i in jobspecs.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                inputname = basename[:-len(key)-1]
                inputext = key
                break
        else:
            messages.failure('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobspecs.progname)
            raise InputFileError()
    elif filepath.isdir():
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'es un directorio')
        raise InputFileError()
    elif filepath.exists():
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no es un archivo regular')
        raise InputFileError()
    else:
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no existe')
        raise InputFileError()

    return inputdir, inputname, inputext

@catch_keyboard_interrupt
def wait():
    sleep(options.wait)

@catch_keyboard_interrupt
def upload():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError:
        return

    relparentdir = path.relpath(inputdir, cluster.homedir)
    remotefiles.append(pathjoin(remote.share, remote.user, relparentdir, (inputname, inputext)))

    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(inputdir, (inputname, key))):
            remoteinputfiles.append(pathjoin(cluster.homedir, '.', relparentdir, (inputname, key)))

@catch_keyboard_interrupt
def remit():
    if options.molfile:
        relmolpath = path.relpath(options.molfile, cluster.homedir)
        options.molfile = pathjoin(remote.share, remote.user, relmolpath)
        remoteinputfiles.append(pathjoin(cluster.homedir, '.', relmolpath))
    call(['rsync', '-R', '-t', '-z', '-e', 'ssh -q', '-q'] + remoteinputfiles + [remote.tohost + ':' + pathjoin(remote.share, remote.user)])
    execv('/usr/bin/ssh', [__file__, '-q', '-t', remote.tohost, 'TELEGRAM_BOT_URL=' + cluster.telegram, 'TELEGRAM_CHAT_ID=' + cluster.chatid, cluster.program, '--remote-from={user}'.format(user=remote.user)] + ['--{opt}={val}'.format(opt=opt, val=val) for opt, val in options.items() if val not in IdentityList(None, True, False)] + ['--{opt}'.format(opt=opt) for opt in options if options[opt] is True] + remotefiles)

@catch_keyboard_interrupt
def submit():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError:
        return

    versionkey = jobspecs.progkey + alnum(options.version)
    scheduler = import_module('.schedulers.' + jobspecs.scheduler, package='job2q')
    jobformat = Bunch(scheduler.jobformat)
    jobenvars = Bunch(scheduler.jobenvars)
    queuejob = scheduler.queuejob
    checkjob = scheduler.checkjob

    filebools = {}

    for key in jobspecs.filekeys:
        filebools[key] = path.isfile(pathjoin(inputdir, (inputname, key)))

    if 'filecheck' in jobspecs:
        if not BoolParser(jobspecs.filecheck).ev(filebools):
            messages.failure('No se encontraron todos los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobspecs:
        if BoolParser(jobspecs.fileclash).ev(filebools):
            messages.failure('Hay un conflicto entre los archivos de entrada')
            return
    
    if inputname.endswith('.' + versionkey):
        jobname = inputname[:-len(versionkey)-1]
    elif inputname.endswith('.' + jobspecs.progkey):
        jobname = inputname[:-len(jobspecs.progkey)-1]
    else:
        jobname = inputname

    if options.jobname:
        jobname = '.'.join((options.jobname, jobname))
        actualname = '.'.join((options.jobname, inputname))
    else:
        actualname = inputname

    if options.outdir:
        try:
            outputdir = AbsPath(options.outdir)
        except NotAbsolutePath:
            outputdir = AbsPath(inputdir, options.outdir)
    else:
        outputdir = AbsPath(jobspecs.defaults.outputdir, inputdir=inputdir, jobname=jobname)
        
    hiddendir = AbsPath(outputdir, ('.' + jobname, versionkey))
    outputname = '.'.join((jobname, versionkey))

    inputfiles = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            inputfiles.append((pathjoin(outputdir, (actualname, key)), pathjoin(node.workdir, jobspecs.filekeys[key])))
    
    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append((pathjoin(node.workdir, jobspecs.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    for key in jobspecs.parameters:
        try:
            parameterdir = AbsPath(jobspecs.parameters[key], inputdir=inputdir, **cluster)
        except NotAbsolutePath:
            messages.cfgerror('La ruta al conjunto de parámetros', key, 'debe ser absoluta')
        try:
            items = parameterdir.listdir()
        except FileNotFoundError:
            messages.cfgerror('El directorio de parámetros', parameterdir, 'no existe')
        except NotADirectoryError:
            messages.cfgerror('El directorio de parámetros', parameterdir, 'no es un directorio')
        if not items:
            messages.cfgerror('El directorio de parámetros', parameterdir, 'está vacío')
        if options[key]:
            parameterset = options[key]
        else:
            if key in jobspecs.defaults.parameters:
                parameterset = jobspecs.defaults.parameters[key]
            else:
                parameterset = dialogs.chooseone('Seleccione un conjunto de parámetros', p(key), choices=sorted(items, key=natsort))
        if path.exists(path.join(parameterdir, parameterset)):
            parameters.append(AbsPath(parameterdir, parameterset))
        else:
            messages.opterror('La ruta de parámetros', path.join(parameterdir, parameterset), 'no existe')
    
    for parameter in parameters:
        if parameter.isfile():
            inputfiles.append((parameter, pathjoin(node.workdir, parameter)))
        elif parameter.isdir():
            for item in parameter.listdir():
                inputfiles.append((pathjoin(parameter, item), pathjoin(node.workdir, item)))

    if outputdir.isdir():
        if hiddendir.isdir():
            try:
                with open(pathjoin(hiddendir, 'jobid'), 'r') as t:
                    jobid = t.read()
                    jobstate = checkjob(jobid)
                    if callable(jobstate):
                        messages.failure(jobstate(jobname=jobname, jobid=jobid))
                        return
            except FileNotFoundError:
                pass
        elif hiddendir.exists():
            messages.failure('No se puede crear la carpeta', hiddendir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(hiddendir)
        if not set(outputdir.listdir()).isdisjoint(pathjoin((outputname, k)) for i in jobspecs.outputfiles for k in i.split('|')):
            if options.no is True or (options.yes is False and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                return
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                remove(pathjoin(outputdir, (outputname, key)))
        if inputdir != outputdir:
            for item in jobspecs.inputfiles:
                for key in item.split('|'):
                    remove(pathjoin(outputdir, (actualname, key)))
    elif outputdir.exists():
        messages.failure('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outputdir)
        makedirs(hiddendir)
    
    if options.template:
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (inputname, key))):
                    with open(pathjoin(inputdir, (inputname, key)), 'r') as t, open(pathjoin(outputdir, (actualname, key)), 'w') as f:
                        try:
                            f.write(t.read().format(**keywords))
                        except KeyError as e:
                            messages.failure('Debe definir la variable', q(e.args[0]), 'referida en la plantilla', pathjoin((inputname, key)))
                            return
    elif inputdir != outputdir:
        action = path.rename if options.move else copyfile
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (inputname, key))):
                    action(pathjoin(inputdir, (inputname, key)), pathjoin(outputdir, (inputname, key)))
    
    jobcomments.append(jobformat.name(jobname))

    offscript = []

    for line in jobspecs.offscript:
        try:
           offscript.append(line.format(jobname=jobname, **cluster))
        except KeyError:
           pass

    jobscript = pathjoin(hiddendir, 'jobscript')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash' + '\n')
        f.write(''.join(i + '\n' for i in jobcomments))
        f.write(''.join(i + '\n' for i in environment))
        f.write('for host in ${hosts[*]}; do echo "<host>$host</host>"; done' + '\n')
        f.write(node.mkdir(node.workdir) + '\n')
        f.write(''.join(node.fetch(i, j) + '\n' for i, j in inputfiles))
        f.write(node.chdir(node.workdir) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.prescript))
        f.write(' '.join(commandline) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.postscript))
        f.write(''.join(head.fetch(i, j) + '\n' for i, j in outputfiles))
        f.write(node.deletedir(node.workdir) + '\n')
        f.write(''.join(head.run(i) + '\n' for i in offscript))
    
    try:
        jobid = queuejob(jobscript)
    except CalledProcessError as error:
        messages.failure('El sistema de colas no envió el trabajo porque ocurrió un error:')
        messages.failure(error)
        return
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(options.ncore), 'núcleo(s) de CPU con el jobid', jobid)
        with open(pathjoin(hiddendir, 'jobid'), 'w') as f:
            f.write(jobid)
    
remotefiles = []
remoteinputfiles = []

if __name__ == '__main__':
    submit()

