# -*- coding: utf-8 -*-
from time import sleep
from shutil import copyfile
from importlib import import_module
from subprocess import call, DEVNULL
from os import path, listdir, execv
from getpass import getuser 
from . import dialogs
from . import messages
from .boolparse import BoolParser
from .decorators import catch_keyboard_interrupt
from .utils import pathjoin, remove, makedirs, normalpath, isabspath, alnum, p, q, sq
from .jobparse import jobcomments, environment, commandline, jobspecs, options, cluster, files
from .jobdigest import keywords, remotefiles
from .classes import Bunch, Identity
from .strings import knownmpis

def nextfile():
    
    filepath = path.abspath(files.pop(0))
    basename = path.basename(filepath)

    if isabspath(filepath):
        parentdir = path.dirname(normalpath(filepath))
    else:
        if cluster.clientdir:
            parentdir = path.dirname(normalpath(cluster.clientdir, filepath))
        else:
            parentdir = path.dirname(normalpath(path.getcwd(), filepath))
        filepath = normalpath(parentdir, filepath)
    
    if path.isfile(filepath):
        for key in (k for i in jobspecs.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                filename = basename[:-len(key)-1]
                extension = key
                break
        else:
            messages.failure('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobspecs.progname)
            raise AssertionError()
    elif path.isdir(filepath):
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'es un directorio')
        raise AssertionError()
    elif path.exists(filepath):
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no es un archivo regular')
        raise AssertionError()
    else:
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no existe')
        raise AssertionError()

    return parentdir, filename, extension

@catch_keyboard_interrupt
def wait():
    sleep(options.wait)

@catch_keyboard_interrupt
def upload():

    try:
        parentdir, filename, extension = nextfile()
    except AssertionError:
        return

    jobfiles = []
    relparentdir = path.relpath(parentdir, cluster.homedir)
    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(parentdir, (filename, key))):
            jobfiles.append(pathjoin(cluster.homedir, '.', relparentdir, (filename, key)))
    call(['rsync', '-R'] + jobfiles + [cluster.remotehost + ':' + cluster.remoteshare])
    remotefiles.append(pathjoin(cluster.remoteshare, relparentdir, (filename, extension)))

@catch_keyboard_interrupt
def remit():
    execv('/usr/bin/ssh', [__file__, '-t', cluster.remotehost, 'REMOTECLIENT={user}@{host}'.format(user=cluster.user, host=cluster.master), cluster.program] + ['--{opt}={val}'.format(opt=opt, val=val) for opt, val in options.items() if Identity(val) not in (None, True, False)] + ['--{opt}'.format(opt=opt) for opt in options if options[opt] is True] + remotefiles)

@catch_keyboard_interrupt
def submit():

    try:
        parentdir, filename, extension = nextfile()
    except AssertionError:
        return

    versionkey = jobspecs.progkey + alnum(options.version)
    scheduler = import_module('.schedulers.' + jobspecs.scheduler, package='job2q')
    jobformat = Bunch(scheduler.jobformat)
    queuejob = scheduler.queuejob
    checkjob = scheduler.checkjob

    filebools = {}

    for key in jobspecs.filekeys:
        filebools[key] = path.isfile(pathjoin(parentdir, (filename, key)))

    if 'filecheck' in jobspecs:
        if not BoolParser(jobspecs.filecheck).ev(filebools):
            messages.failure('No se encontraron todos los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobspecs:
        if BoolParser(jobspecs.fileclash).ev(filebools):
            messages.failure('Hay un conflicto entre los archivos de entrada')
            return
    
    if filename.endswith('.' + versionkey):
        jobname = filename[:-len(versionkey)-1]
    elif filename.endswith('.' + jobspecs.progkey):
        jobname = filename[:-len(jobspecs.progkey)-1]
    else:
        jobname = filename

    if options.jobname:
        jobname = pathjoin((options.jobname, jobname))
        inputname = pathjoin((options.jobname, filename))
    else:
        inputname = filename

    if options.outdir:
        if isabspath(options.outdir):
            outputdir = normalpath(options.outdir)
        else:
            outputdir = normalpath(parentdir, options.outdir)
    else:
        outputdir = normalpath(parentdir, jobname)
        
    hiddendir = pathjoin(outputdir, ('.' + jobname, versionkey))
    outputname = pathjoin((jobname, versionkey))

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
            inputfiles.append(copyfromhead(pathjoin(outputdir, (inputname, key)), pathjoin('$workdir', jobspecs.filekeys[key])))
    
    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append(copytohead(pathjoin('$workdir', jobspecs.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    for parameter in options.parameters:
        if not isabspath(parameter):
            parameter = normalpath(parentdir, parameter)
        if path.isfile(parameter):
            inputfiles.append(copyfromhead(parameter, '$workdir'))
        elif path.isdir(parameter):
            inputfiles.append(copyallfromhead(parameter, '$workdir'))
    
    if path.isdir(outputdir):
        if path.isdir(hiddendir):
            try:
                with open(pathjoin(hiddendir, 'jobid'), 'r') as t:
                    jobid = t.read()
                    jobstate = checkjob(jobid)
                    if callable(jobstate):
                        messages.failure(jobstate(jobname=jobname, jobid=jobid))
                        return
            except FileNotFoundError:
                pass
        elif path.exists(hiddendir):
            messages.failure('No se puede crear la carpeta', hiddendir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(hiddendir)
        if not set(listdir(outputdir)).isdisjoint(pathjoin((outputname, k)) for i in jobspecs.outputfiles for k in i.split('|')):
            if options.no is True or (options.yes is False and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                return
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                remove(pathjoin(outputdir, (outputname, key)))
        if parentdir != outputdir:
            for item in jobspecs.inputfiles:
                for key in item.split('|'):
                    remove(pathjoin(outputdir, (inputname, key)))
    elif path.exists(outputdir):
        messages.failure('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outputdir)
        makedirs(hiddendir)
    
    if options.template:
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(parentdir, (filename, key))):
                    with open(pathjoin(parentdir, (filename, key)), 'r') as t, open(pathjoin(outputdir, (inputname, key)), 'w') as f:
                        try: f.write(t.read().format(**keywords))
                        except KeyError as e:
                            messages.failure('Hay variables indefinidas en la plantilla', pathjoin((filename, key)), p(e.args[0]))
                            return
    elif parentdir != outputdir:
        action = path.rename if options.move else copyfile
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(parentdir, (filename, key))):
                    action(pathjoin(parentdir, (filename, key)), pathjoin(outputdir, (filename, key)))
    
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

