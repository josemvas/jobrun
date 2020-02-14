# -*- coding: utf-8 -*-
from time import sleep
from os import path, execv, getcwd
from subprocess import call, DEVNULL
from importlib import import_module
from . import dialogs
from . import messages
from .jobsetup import parameters, script
from .fileutils import AbsPath, NotAbsolutePath, pathjoin, remove, makedirs, copyfile
from .utils import Bunch, IdentityList, alnum, natsort, p, q, sq, catch_keyboard_interrupt
from .jobparse import run, user, cluster, envars, jobspecs, options, keywords
from .jobutils import nextfile, InputFileError
from .boolparse import BoolParser

@catch_keyboard_interrupt
def wait():
    sleep(options.wait)

@catch_keyboard_interrupt
def offload():
    if remotefiles:
        call(['rsync', '-Rtzqe', 'ssh -q'] + remoteinputfiles + [run.remote + ':' + pathjoin(run.jobshare, run.userathost)])
        execv('/usr/bin/ssh', [__file__, '-Xqt', run.remote] + ['{envar}={value}'.format(envar=envar, value=value) for envar, value in envars.items()] + [run.program] + ['--{option}={value}'.format(option=option.replace('_', '-'), value=value) for option, value in options.items() if value not in IdentityList(None, True, False)] + ['--{option}'.format(option=option.replace('_', '-')) for option in options if options[option] is True] + remotefiles)

@catch_keyboard_interrupt
def dryrun():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError as e:
        messages.failure(e)
        return

@catch_keyboard_interrupt
def remoterun():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError as e:
        messages.failure(e)
        return

    relparentdir = path.relpath(inputdir, user.home)
    remotefiles.append(pathjoin(run.jobshare, run.userathost, relparentdir, (inputname, inputext)))
    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(inputdir, (inputname, key))):
            remoteinputfiles.append(pathjoin(user.home, '.', relparentdir, (inputname, key)))

@catch_keyboard_interrupt
def localrun():

    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError as e:
        messages.failure(e)
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
        try:
            outputdir = AbsPath(jobspecs.defaults.outputdir).keyexpand({'jobname':jobname})
        except NotAbsolutePath:
            outputdir = AbsPath(inputdir, jobspecs.defaults.outputdir).keyexpand({'jobname':jobname})

    hiddendir = AbsPath(outputdir, '.' + jobname + '.' + progkey)
    outputname = jobname + '.' + progkey

    inputfiles = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            if path.isfile(pathjoin(outputdir, (jobname, key))):
                inputfiles.append(((pathjoin(outputdir, (jobname, key))), pathjoin(script.workdir, jobspecs.filekeys[key])))
    
    inputdirs = []

    for parameter in parameters:
        if parameter.isfile():
            inputfiles.append((parameter, pathjoin(script.workdir, parameter)))
        elif parameter.isdir():
            inputdirs.append((pathjoin(parameter), script.workdir))

    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append((pathjoin(script.workdir, jobspecs.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    if outputdir.isdir():
        if hiddendir.isdir():
            try:
                with open(pathjoin(hiddendir, 'jobid'), 'r') as t:
                    jobid = t.read()
                    jobstate = checkjob(jobid)
                    if callable(jobstate):
                        messages.failure(jobstate({'jobname':jobname}, jobid=jobid))
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
           offscript.append(line.format({'jobname':jobname}, clustername=cluster.name, **envars))
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
        f.write(''.join(script.fetchdir(i, j) + '\n' for i, j in inputdirs))
        f.write(script.chdir(script.workdir) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.prescript))
        f.write(' '.join(script.command) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.postscript))
        f.write(''.join(script.remit(i, j) + '\n' for i, j in outputfiles))
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

