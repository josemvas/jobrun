# -*- coding: utf-8 -*-
from time import sleep
from shutil import copyfile
from importlib import import_module
from os import execl, path, listdir, getcwd
from getpass import getuser 
from . import dialogs
from . import messages
from .readspec import BunchDict
from .utils import wordjoin, barejoin, pathjoin, remove, makedirs, normalpath, isabspath, alnum, p, q, sq
from .configure import jobconf, optconf, files, command, control, environment, keywords
from .decorators import catch_keyboard_interrupt
from .boolparse import BoolParser
from .strings import mpiLibs

def popfile():
    
    filepath = path.abspath(files.pop(0))
    basename = path.basename(filepath)

    if isabspath(filepath):
        localdir = path.dirname(normalpath(filepath))
    else:
        if optconf.cwdir:
            localdir = path.dirname(normalpath(optconf.cwdir, filepath))
        else:
            localdir = path.dirname(normalpath(path.getcwd(), filepath))
        filepath = normalpath(localdir, filepath)
    
    if path.isfile(filepath):
        for key in (k for i in jobconf.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                filename = basename[:-len(key)-1]
                break
        else:
            messages.failure('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobconf.packagename)
            return
    elif path.isdir(filepath):
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'es un directorio')
        return
    elif path.exists(filepath):
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no es un archivo regular')
        return
    else:
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no existe')
        return

    filebools = {}

    for key in jobconf.filekeys:
        filebools[key] = path.isfile(pathjoin(localdir, (filename, key)))

    if 'filecheck' in jobconf:
        if not BoolParser(jobconf.filecheck).ev(filebools):
            messages.failure('No se encontraron todos los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobconf:
        if BoolParser(jobconf.fileclash).ev(filebools):
            messages.failure('Hay un conflicto entre los archivos de entrada')
            return
    
    return localdir, filename

@catch_keyboard_interrupt
def submit():

    localdir, filename = popfile()
    versionkey = jobconf.packagekey + alnum(optconf.version)
    scheduler = import_module('.schedulers.' + jobconf.scheduler, package='job2q')
    jobstr = BunchDict(scheduler.jobstr)
    queuejob = scheduler.queuejob
    checkjob = scheduler.checkjob

    if filename.endswith('.' + versionkey):
        jobname = filename[:-len(versionkey)-1]
    elif filename.endswith('.' + jobconf.packagekey):
        jobname = filename[:-len(jobconf.packagekey)-1]
    else:
        jobname = filename

    if optconf.jobname:
        jobname = pathjoin((optconf.jobname, jobname))
        inputname = pathjoin((optconf.jobname, inputname))
    else:
        inputname = filename

    if optconf.outdir:
        if isabspath(optconf.outdir):
            outputdir = normalpath(optconf.outdir)
        else:
            outputdir = normalpath(localdir, optconf.outdir)
    else:
        outputdir = normalpath(localdir, jobname)
        
    hiddendir = pathjoin(outputdir, ('.' + jobname, versionkey))
    outputname = pathjoin((jobname, versionkey))

    if jobconf.hostcopy == 'local':
        makeworkdir = 'mkdir -m 700 "\'$workdir\'"'.format
        removeworkdir = 'rm -rf "\'$workdir\'/*"'.format
        copyfromhead = 'cp "{}" "{}"'.format
        copyallfromhead = 'cp "{}"/* "{}"'.format
        copytohead = 'cp "{}" "{}"'.format
        runathead = 'ssh $head "{}"'.format
    elif jobconf.hostcopy == 'remote':
        makeworkdir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -m 700 "\'$workdir\'"; done'.format
        removeworkdir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'$workdir\'/*"; done'.format
        copyfromhead = 'for host in ${{hosts[*]}}; do scp $head:"\'{}\'" $host:"\'{}\'"; done'.format
        copyallfromhead = 'for host in ${{hosts[*]}}; do scp $head:"\'{}\'/*" $host:"\'{}\'"; done'.format
        copytohead = 'scp "{}" $head:"\'{}\'"'.format
        runathead = 'ssh $head "{}"'.format
    elif jobconf.hostcopy == 'headjump':
        makeworkdir = 'for host in ${{hosts[*]}}; do ssh $head ssh $host mkdir -m 700 "\'$workdir\'"; done'.format
        removeworkdir = 'for host in ${{hosts[*]}}; do ssh $head ssh $host rm -rf "\'$workdir\'/*"; done'.format
        copyfromhead = 'for host in ${{hosts[*]}}; do ssh $head scp "\'{}\'$host:"\'{}\'"; done'.format
        copyallfromhead = 'for host in ${{hosts[*]}}; do ssh $head scp "\'{}\'/*" $host:"\'{}\'"; done'.format
        copytohead = 'scp "{}" $head:"\'{}\'"'.format
        runathead = 'ssh $head "{}"'.format
    else:
        messages.cfgerror('El método de copia', q(jobconf.hostcopy), 'no es válido')
    
    inputfiles = []

    for item in jobconf.inputfiles:
        for key in item.split('|'):
            inputfiles.append(copyfromhead(pathjoin(outputdir, (inputname, key)), pathjoin('$workdir', jobconf.filekeys[key])))
    
    outputfiles = []

    for item in jobconf.outputfiles:
        for key in item.split('|'):
            outputfiles.append(copytohead(pathjoin('$workdir', jobconf.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    for parameter in optconf.parameters:
        if not isabspath(parameter):
            parameter = normalpath(localdir, parameter)
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
        if not set(listdir(outputdir)).isdisjoint(pathjoin((outputname, k)) for i in jobconf.outputfiles for k in i.split('|')):
            if optconf.defaultanswer is False or (optconf.defaultanswer is not True and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                return
        for item in jobconf.outputfiles:
            for key in item.split('|'):
                remove(pathjoin(outputdir, (outputname, key)))
        if localdir != outputdir:
            for item in jobconf.inputfiles:
                for key in item.split('|'):
                    remove(pathjoin(outputdir, (inputname, key)))
    elif path.exists(outputdir):
        messages.failure('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outputdir)
        makedirs(hiddendir)
    
    if optconf.template:
        for item in jobconf.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(localdir, (filename, key))):
                    with open(pathjoin(localdir, (filename, key)), 'r') as t, open(pathjoin(outputdir, (inputname, key)), 'w') as f:
                        try: f.write(t.read().format(**keywords))
                        except KeyError as e:
                            messages.failure('Hay variables indefinidas en la plantilla', pathjoin((filename, key)), p(e.args[0]))
                            return
    elif localdir != outputdir:
        action = path.rename if optconf.move else copyfile
        for item in jobconf.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(localdir, (filename, key))):
                    action(pathjoin(localdir, (filename, key)), pathjoin(outputdir, (filename, key)))
    
    control.append(jobstr.jobname(jobname))
    environment.append("jobname=" + sq(jobname))

    with open(pathjoin(hiddendir, 'jobscript'), 'w') as t:
        t.write('#!/bin/bash' + '\n')
        t.write(barejoin(i + '\n' for i in control))
        t.write(barejoin(i + '\n' for i in environment))
        t.write(makeworkdir() + '\n')
        t.write(barejoin(i + '\n' for i in inputfiles))
        t.write('cd "$workdir"' + '\n')
        t.write(barejoin(i + '\n' for i in jobconf.prescript))
        t.write(wordjoin(command) + '\n')
        t.write(''.join(i + '\n' for i in jobconf.postscript))
        t.write(barejoin(i + '\n' for i in outputfiles))
        t.write(removeworkdir() + '\n')
        t.write(barejoin(runathead(i) + '\n' for i in jobconf.offscript))
    
    jobid = queuejob(t.name)

    if jobid is None:
        return

    messages.success('El trabajo', q(jobname), 'se correrá en', str(optconf.ncore), 'núcleo(s) de CPU con el jobid', jobid)
    with open(pathjoin(hiddendir, 'jobid'), 'w') as t:
        t.write(jobid)
    
@catch_keyboard_interrupt
def upload():
    localdir, filename = popfile()

@catch_keyboard_interrupt
def transmit():
# Unpacking requires python 3.5
#    os.execl('ssh', optconf.remote, *sys.argv, '--cwdir={}@{}'.format(getuser(), jobconf.headname), '--move')
    pass

@catch_keyboard_interrupt
def wait():
    sleep(optconf.waitime)

if __name__ == '__main__':
    submit()

