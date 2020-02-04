# -*- coding: utf-8 -*-
from time import sleep
from shutil import copyfile
from os import path, execv, getcwd
from subprocess import call, DEVNULL
from importlib import import_module
from getpass import getuser 
from . import dialogs
from . import messages
from .boolparse import BoolParser
from .exceptions import NotAbsolutePath, InputFileError
from .jobparse import cluster, remote, jobspecs, options, files
from .utils import pathjoin, remove, makedirs, alnum, p, q, sq, catch_keyboard_interrupt
from .jobdigest import keywords, jobcomments, environment, commandline, parameters, node
from .classes import Bunch, AbsPath, IdentityList

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
    call(['rsync', '-R'] + remoteinputfiles + [remote.tohost + ':' + pathjoin(remote.share, remote.user)])
    execv('/usr/bin/ssh', [__file__, '-t', remote.tohost, 'TELEGRAM_BOT_URL=' + cluster.telegram, 'TELEGRAM_CHAT_ID=' + cluster.chatid, cluster.program, '--remote-from={user}'.format(user=remote.user)] + ['--{opt}={val}'.format(opt=opt, val=val) for opt, val in options.items() if val not in IdentityList(None, True, False)] + ['--{opt}'.format(opt=opt) for opt in options if options[opt] is True] + remotefiles)

@catch_keyboard_interrupt
def submit():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError:
        return

    versionkey = jobspecs.progkey + alnum(options.version)
    scheduler = import_module('.schedulers.' + jobspecs.scheduler, package='job2q')
    jobformat = Bunch(scheduler.jobformat)
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
        jobname = pathjoin((options.jobname, jobname))
        actualname = pathjoin((options.jobname, inputname))
    else:
        actualname = inputname

    if options.outdir:
        try:
            outputdir = AbsPath(options.outdir)
        except NotAbsolutePath:
            outputdir = AbsPath(inputdir, options.outdir)
    else:
        outputdir = AbsPath(jobspecs.defaults.outputdir.format(jobname=jobname, inputdir=inputdir, **{'/':path.sep}))
        
    hiddendir = AbsPath(outputdir, ('.' + jobname, versionkey))
    outputname = '.'.join([jobname, versionkey])

    inputfiles = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            inputfiles.append(node.copyfromhead(pathjoin(outputdir, (actualname, key)), pathjoin('$workdir', jobspecs.filekeys[key])))
    
    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append(node.copytohead(pathjoin('$workdir', jobspecs.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    for parameter in parameters:
        try:
            parameter = AbsPath(parameter, expand=True)
        except NotAbsolutePath:
            parameter = AbsPath(inputdir, parameter, expand=True)
        if parameter.isfile():
            inputfiles.append(node.copyfromhead(parameter, '$workdir'))
        elif parameter.isdir():
            inputfiles.append(node.copyallfromhead(parameter, '$workdir'))
    
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
                            messages.failure('Hay variables indefinidas en la plantilla', pathjoin((inputname, key)), p(e.args[0]))
                            return
    elif inputdir != outputdir:
        action = path.rename if options.move else copyfile
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (inputname, key))):
                    action(pathjoin(inputdir, (inputname, key)), pathjoin(outputdir, (inputname, key)))
    
    jobcomments.append(jobformat.jobname(jobname))
    environment.append("jobname=" + sq(jobname))

    offscript = []

    for line in jobspecs.offscript:
        try:
           offscript.append(line.format(jobname=jobname, **cluster))
        except KeyError:
           pass

    with open(pathjoin(hiddendir, 'jobscript'), 'w') as t:
        t.write('#!/bin/bash' + '\n')
        t.write(''.join(i + '\n' for i in jobcomments))
        t.write(''.join(i + '\n' for i in environment))
        t.write(node.makeworkdir() + '\n')
        t.write(''.join(i + '\n' for i in inputfiles))
        t.write('cd "$workdir"' + '\n')
        t.write(''.join(i + '\n' for i in jobspecs.prescript))
        t.write(' '.join(commandline) + '\n')
        t.write(''.join(i + '\n' for i in jobspecs.postscript))
        t.write(''.join(i + '\n' for i in outputfiles))
        t.write(node.removeworkdir() + '\n')
        t.write(''.join(node.runathead(i) + '\n' for i in offscript))
    
    jobid = queuejob(t.name)

    if jobid is None:
        return

    messages.success('El trabajo', q(jobname), 'se correrá en', str(options.ncore), 'núcleo(s) de CPU con el jobid', jobid)
    with open(pathjoin(hiddendir, 'jobid'), 'w') as t:
        t.write(jobid)
    
remotefiles = []
remoteinputfiles = []

if __name__ == '__main__':
    submit()

