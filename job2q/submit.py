# -*- coding: utf-8 -*-
from errno import ENOENT
from os import path, listdir
from socket import gethostname, gethostbyname
from tempfile import NamedTemporaryFile
from shutil import copyfile
from time import sleep

from . import dialogs
from . import messages
from .parsing import parsebool
from .utils import wordjoin, linejoin, pathjoin, remove, makedirs, realpath, alnum, p, q, qq
from .getconf import jobconf, queconf, optconf, inputlist, comments, environment, command, keywords
from .decorators import catch_keyboard_interrupt
from .strings import mpiLibs

@catch_keyboard_interrupt
def wait():
    sleep(optconf.waitime)

@catch_keyboard_interrupt
def submit():

    outputfiles = []
    inputfiles = []
    
    filepath = path.abspath(inputlist.pop(0))
    basename = path.basename(filepath)
    
    if path.isfile(filepath):
        localdir = path.dirname(filepath)
        for key in (k for i in jobconf.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                filename = basename[:-len(key)-1]
                break
        else:
            messages.failure('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobconf.pkgname)
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

    filebools = { i : path.isfile(pathjoin(localdir, (filename, i))) for i in jobconf.fileexts }

    if 'filecheck' in jobconf:
        if not parsebool(jobconf.filecheck, filebools):
            messages.failure('Falta(n) alguno(s) de los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobconf:
        if parsebool(jobconf.fileclash, filebools):
            messages.failure('Hay un conflicto entre algunos de los archivos de entrada')
            return
    
    inputname = filename
    versionkey = jobconf.pkgkey + alnum(optconf.version)

    if filename.endswith('.' + versionkey):
        jobname = filename[:-len(versionkey)-1]
    elif filename.endswith('.' + jobconf.pkgkey):
        jobname = filename[:-len(jobconf.pkgkey)-1]
    else:
        jobname = filename

    if optconf.jobname:
        inputname = pathjoin((optconf.jobname, inputname))
        jobname = pathjoin((optconf.jobname, jobname))

    outputdir = localdir if optconf.here or not jobconf.jobdir else pathjoin(localdir, jobname)
    hiddendir = pathjoin(outputdir, ('.' + jobname, versionkey))
    outputname = pathjoin((jobname, versionkey))
    master = gethostbyname(gethostname())
    
    for item in jobconf.inputfiles:
        for key in item.split('|'):
            inputfiles.append(wordjoin('ssh', master, 'scp', qq(pathjoin(outputdir, (inputname, key))), \
               '$ip:' + qq(pathjoin('$workdir', jobconf.fileexts[key]))))
    
    for item in jobconf.outputfiles:
        for key in item.split('|'):
            outputfiles.append(wordjoin('scp', q(pathjoin('$workdir', jobconf.fileexts[key])), \
                master + ':' + qq(pathjoin(outputdir, (outputname, key)))))
    
    for parset in optconf.parameters:
        if not path.isabs(parset):
            parset = pathjoin(localdir, parset)
        if path.isdir(parset):
            parset = pathjoin(parset, '.')
        inputfiles.append(wordjoin('ssh', master, 'scp -r', qq(parset), '$ip:' + qq('$workdir')))
    
    if path.isdir(outputdir):
        if path.isdir(hiddendir):
            try:
                lastjob = max(listdir(hiddendir), key=int)
            except ValueError:
                pass
            else:
                jobstate = queconf.checkjob(lastjob)
                if jobstate in queconf.jobstates:
                    messages.failure(queconf.jobstates[jobstate].format(jobname=jobname, jobid=lastjob))
                    return
        elif path.exists(hiddendir):
            messages.failure('No se puede crear la carpeta', hiddendir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(hiddendir)
        if not set(listdir(outputdir)).isdisjoint(pathjoin((outputname, k)) for i in jobconf.outputfiles for k in i.split('|')):
            if optconf.defaultanswer is None:
                optconf.defaultanswer = dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas (si/no)?')
            if optconf.defaultanswer is False:
                messages.failure('El trabajo', q(jobname), 'no se envió por solicitud del usuario')
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
    
    comments.append(queconf.jobname.format(jobname))
    environment.append("jobname=" + jobname)

    with NamedTemporaryFile(mode='w+t', delete=False) as t:
        t.write(linejoin(i for i in comments))
        t.write(linejoin(i for i in environment))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + wordjoin('ssh', master, 'ssh $ip mkdir -m 700 "\'$workdir\'"') + '\n')
        t.write(linejoin(' ' * 2 + i for i in inputfiles))
        t.write('done' + '\n')
        t.write('cd "$workdir"' + '\n')
        t.write(linejoin(i for i in jobconf.prescript))
        t.write(wordjoin(command) + '\n')
        t.write(linejoin(i for i in jobconf.postscript))
        t.write(linejoin(i for i in outputfiles))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + 'ssh $ip rm -f "\'$workdir\'/*"' + '\n')
        t.write(' ' * 2 + 'ssh $ip rmdir "\'$workdir\'"' + '\n')
        t.write('done' + '\n')
        t.write(linejoin(wordjoin('ssh', master, q(i)) for i in jobconf.offscript))
    
    try: jobid = queconf.submit(t.name)
    except RuntimeError as e:
        messages.failure('El sistema de colas rechazó el trabajo', q(jobname), 'con el mensaje', q(e.args[0]))
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(optconf.ncpu), 'núcleo(s) de CPU con el jobid', jobid)
        copyfile(t.name, pathjoin(hiddendir, jobid))
        remove(t.name)
    
if __name__ == '__main__':
    submit()

