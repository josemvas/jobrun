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
from .utils import pathjoin, remove, makedirs, alnum, natsort, p, q, sq, catch_keyboard_interrupt
from .jobparse import run, user, cluster, envars, jobspecs, options, keywords
from .classes import Bunch, AbsPath, IdentityList
from .jobsetup import parameters, script

def nextfile():

    file = run.files.pop(0)

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

    if run.interpolate:
        templatename = inputname
        inputname = '.'.join((run.molname, inputname))
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (templatename, key))):
                    with open(pathjoin(inputdir, (templatename, key)), 'r') as fr, open(pathjoin(inputdir, (inputname, key)), 'w') as fw:
                        try:
                            fw.write(fr.read().format(**keywords))
                        except KeyError as e:
                            messages.failure('No se definió la variable de interpolación', q(e.args[0]), 'del archivo de entrada', pathjoin((templatename, key)))
                            raise InputFileError()

    return inputdir, inputname, inputext

@catch_keyboard_interrupt
def wait():
    sleep(options.wait)

@catch_keyboard_interrupt
def offload():
    if remotefiles:
        call(['rsync', '-Rtzqe', 'ssh -q'] + remoteinputfiles + [run.remote + ':' + pathjoin(run.jobshare, run.userathost)])
        execv('/usr/bin/ssh', [__file__, '-Xqt', run.remote] + ['{envar}={value}'.format(envar=envar, value=value) for envar, value in envars.items()] + [run.program] + ['--{option}={value}'.format(option=option, value=value) for option, value in options.items() if value not in IdentityList(None, True, False)] + ['--{option}'.format(option=option) for option in options if options[option] is True] + remotefiles)

@catch_keyboard_interrupt
def dryrun():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError:
        return

def remoterun():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError:
        return

    relparentdir = path.relpath(inputdir, user.home)
    remotefiles.append(pathjoin(run.jobshare, run.userathost, relparentdir, (inputname, inputext)))
    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(inputdir, (inputname, key))):
            remoteinputfiles.append(pathjoin(user.home, '.', relparentdir, (inputname, key)))

def localrun():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError:
        return

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
    
    progkey = jobspecs.progkey + alnum(options.version)

    if inputname.endswith('.' + progkey):
        bareinputname = inputname[:-len(progkey)-1]
    elif inputname.endswith('.' + jobspecs.progkey):
        bareinputname = inputname[:-len(jobspecs.progkey)-1]
    else:
        bareinputname = inputname

    if options.jobname:
        jobname = options.jobname
#        jobname = '.'.join((run.molname, bareinputname))
    else:
        jobname = bareinputname

    if options.outdir:
        try:
            outputdir = AbsPath(options.outdir)
        except NotAbsolutePath:
            outputdir = AbsPath(inputdir, options.outdir)
    else:
        outputdir = AbsPath(jobspecs.defaults.outputdir, inputdir=inputdir, jobname=jobname)
        
    hiddendir = AbsPath(outputdir, ('.' + jobname, progkey))
    outputname = '.'.join((jobname, progkey))

    inputfiles = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            inputfiles.append((pathjoin(outputdir, (jobname, key)), pathjoin(script.workdir, jobspecs.filekeys[key])))
    
    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append((pathjoin(script.workdir, jobspecs.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    for key in jobspecs.parameters:
        try:
            parameterdir = AbsPath(jobspecs.parameters[key], inputdir=inputdir, **user)
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
            inputfiles.append((parameter, pathjoin(script.workdir, parameter)))
        elif parameter.isdir():
            for item in parameter.listdir():
                inputfiles.append((pathjoin(parameter, item), pathjoin(script.workdir, item)))

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
                    remove(pathjoin(outputdir, (jobname, key)))
    elif outputdir.exists():
        messages.failure('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outputdir)
        makedirs(hiddendir)
    
    if inputdir != outputdir:
        action = path.rename if options.move else copyfile
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (inputname, key))):
                    action(pathjoin(inputdir, (inputname, key)), pathjoin(outputdir, (jobname, key)))
    
    script.comments.append(jobformat.name(jobname))

    offscript = []

    for line in jobspecs.offscript:
        try:
           offscript.append(line.format(jobname=jobname, clustername=cluster.name, **envars))
        except KeyError:
           pass

    jobscript = pathjoin(hiddendir, 'jobscript')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash' + '\n')
        f.write(''.join(i + '\n' for i in script.comments))
        f.write(''.join(i + '\n' for i in script.environ))
        f.write('for host in ${hosts[*]}; do echo "<host>$host</host>"; done' + '\n')
        f.write(script.mkdir(script.workdir) + '\n')
        f.write(''.join(script.fetch(i, j) + '\n' for i, j in inputfiles))
        f.write(script.chdir(script.workdir) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.prescript))
        f.write(' '.join(script.command) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.postscript))
        f.write(''.join(script.put(i, j) + '\n' for i, j in outputfiles))
        f.write(script.rmdir(script.workdir) + '\n')
        f.write(''.join(script.runathead(i) + '\n' for i in offscript))
    
    try:
        jobid = queuejob(jobscript)
    except RuntimeError as error:
        messages.failure('El sistema de colas no envió el trabajo porque ocurrió un error', p(error))
        return
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(options.ncore), 'núcleo(s) de CPU con el jobid', jobid)
        with open(pathjoin(hiddendir, 'jobid'), 'w') as f:
            f.write(jobid)
    
remotefiles = []
remoteinputfiles = []

if __name__ == '__main__':
    submit()

