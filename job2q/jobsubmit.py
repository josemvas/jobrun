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
from .decorators import catch_keyboard_interrupt
from .exceptions import NotAbsolutePath, InputFileError
from .jobdigest import keywords, jobcomments, environment, commandline, parameters, remotefiles
from .utils import pathjoin, remove, makedirs, alnum, p, q, sq
from .jobparse import cluster, jobspecs, options, files
from .classes import Bunch, Identity, AbsPath
from .strings import mpilibs

def nextfile():
    
    file = files.pop(0)

    try:
        filepath = AbsPath(file)
    except NotAbsolutePath:
        filepath = AbsPath(getcwd(), file)

    inputdir = filepath.parent
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

    jobfiles = []
    relparentdir = path.relpath(inputdir, cluster.homedir)
    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(inputdir, (inputname, key))):
            jobfiles.append(pathjoin(cluster.homedir, '.', relparentdir, (inputname, key)))
    call(['rsync', '-R'] + jobfiles + [cluster.remotehost + ':' + cluster.remoteshare])
    remotefiles.append(pathjoin(cluster.remoteshare, relparentdir, (inputname, inputext)))

@catch_keyboard_interrupt
def remit():
    execv('/usr/bin/ssh', [__file__, '-t', cluster.remotehost, cluster.program] + ['--{opt}={val}'.format(opt=opt, val=val) for opt, val in options.items() if Identity(val) not in (None, True, False)] + ['--{opt}'.format(opt=opt) for opt in options if options[opt] is True] + remotefiles)

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
        outputdir = AbsPath(jobspecs.defaults.outputdir.format(**{'/':path.sep, 'inputdir':inputdir, 'jobname':jobname}))
        
    hiddendir = AbsPath(outputdir, ('.' + jobname, versionkey))
    outputname = '.'.join([jobname, versionkey])

    if jobspecs.hostcopy == 'local':
        makeworkdir = 'mkdir -m 700 "\'$workdir\'"'.format
        removeworkdir = 'rm -rf "\'$workdir\'/*"'.format
        copyfromhead = 'cp "{}" "{}"'.format
        copyallfromhead = 'cp "{}"/* "{}"'.format
        copytohead = 'cp "{}" "{}"'.format
        runathead = 'ssh $head "{}"'.format
    elif jobspecs.hostcopy == 'remote':
        makeworkdir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -m 700 "\'$workdir\'"; done'.format
        removeworkdir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'$workdir\'/*"; done'.format
        copyfromhead = 'for host in ${{hosts[*]}}; do scp $head:"\'{}\'" $host:"\'{}\'"; done'.format
        copyallfromhead = 'for host in ${{hosts[*]}}; do scp $head:"\'{}\'/*" $host:"\'{}\'"; done'.format
        copytohead = 'scp "{}" $head:"\'{}\'"'.format
        runathead = 'ssh $head "{}"'.format
    elif jobspecs.hostcopy == 'headjump':
        makeworkdir = 'for host in ${{hosts[*]}}; do ssh $head ssh $host mkdir -m 700 "\'$workdir\'"; done'.format
        removeworkdir = 'for host in ${{hosts[*]}}; do ssh $head ssh $host rm -rf "\'$workdir\'/*"; done'.format
        copyfromhead = 'for host in ${{hosts[*]}}; do ssh $head scp "\'{}\'$host:"\'{}\'"; done'.format
        copyallfromhead = 'for host in ${{hosts[*]}}; do ssh $head scp "\'{}\'/*" $host:"\'{}\'"; done'.format
        copytohead = 'scp "{}" $head:"\'{}\'"'.format
        runathead = 'ssh $head "{}"'.format
    else:
        messages.cfgerror('El método de copia', q(jobspecs.hostcopy), 'no es válido')
    
    inputfiles = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            inputfiles.append(copyfromhead(pathjoin(outputdir, (actualname, key)), pathjoin('$workdir', jobspecs.filekeys[key])))
    
    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append(copytohead(pathjoin('$workdir', jobspecs.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    for parameter in parameters:
        try:
            parameter = AbsPath(parameter, expand=True)
        except NotAbsolutePath:
            parameter = AbsPath(inputdir, parameter, expand=True)
        if parameter.isfile():
            inputfiles.append(copyfromhead(parameter, '$workdir'))
        elif parameter.isdir():
            inputfiles.append(copyallfromhead(parameter, '$workdir'))
    
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
                        try: f.write(t.read().format(**keywords))
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

    with open(pathjoin(hiddendir, 'jobscript'), 'w') as t:
        t.write('#!/bin/bash' + '\n')
        t.write(''.join(i + '\n' for i in jobcomments))
        t.write(''.join(i + '\n' for i in environment))
        t.write(makeworkdir() + '\n')
        t.write(''.join(i + '\n' for i in inputfiles))
        t.write('cd "$workdir"' + '\n')
        t.write(''.join(i + '\n' for i in jobspecs.prescript))
        t.write(' '.join(commandline) + '\n')
        t.write(''.join(i + '\n' for i in jobspecs.postscript))
        t.write(''.join(i + '\n' for i in outputfiles))
        t.write(removeworkdir() + '\n')
        t.write(''.join(runathead(i) + '\n' for i in jobspecs.offscript))
    
    jobid = queuejob(t.name)

    if jobid is None:
        return

    messages.success('El trabajo', q(jobname), 'se correrá en', str(options.ncore), 'núcleo(s) de CPU con el jobid', jobid)
    with open(pathjoin(hiddendir, 'jobid'), 'w') as t:
        t.write(jobid)
    
if __name__ == '__main__':
    submit()

