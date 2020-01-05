# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from errno import ENOENT
from os import path, environ, listdir
from socket import gethostname, gethostbyname
from tempfile import NamedTemporaryFile
from shutil import copyfile
from time import sleep

from job2q import dialogs
from job2q import messages
from job2q.parsing import parsebool
from job2q.utils import wordjoin, linejoin, pathjoin, remove, makedirs, realpath, alnum, p, q, qq
from job2q.getconf import jobconf, sysconf, optconf, comments, environment, command
from job2q.decorators import catch_keyboard_interrupt
from job2q.spectags import scriptTags, MPILibs
from job2q.exceptions import * 

@catch_keyboard_interrupt
def wait():
    sleep(optconf.waitime)

@catch_keyboard_interrupt
def submit():

    exportfiles = []
    importfiles = []
    
    filepath = path.abspath(inputlist.pop(0))
    basename = path.basename(filepath)
    master = gethostbyname(gethostname())
    
    if not path.exists(filepath):
        messages.failure('El archivo de entrada', filepath, 'no existe')
        return
    elif path.isfile(filepath):
        localdir = path.dirname(filepath)
        makefolder = jobconf.makefolder
        for item in jobconf.inputfiles:
            for key in item.split('|'):
                if basename.endswith('.' + key):
                    filename = basename[:-len(key)-1]
                    break
            else: continue
            break
        else:
            messages.failure('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobconf.pkgname)
            return
    elif path.isdir(filepath):
        localdir = filepath
        makefolder = False
        filename = pathjoin((basename, jobconf.pkgkey))
        for listed in listdir(filepath):
            for item in jobconf.inputfiles:
                for key in item.split('|'):
                    if listed == pathjoin((filename, key)):
                        break
                else: continue
                break
            else: continue
            break
        else:
            messages.failure('Este trabajo no se envió porque el directorio', filepath, 'no contiene archivos de entrada de', jobconf.pkgname)
            return
    else:
        messages.failure('El archivo de entrada', filepath, 'no es un archivo regular')

    filebools = { i : path.isfile(pathjoin(localdir, (filename, i))) for i in jobconf.fileexts }
    versionkey = jobconf.pkgkey + alnum(optconf.version) if jobconf.pkgkey else 'v' +  alnum(optconf.version)
    if filename.endswith('.' + versionkey):
        jobname = filename[:-len(versionkey)-1]
    elif filename.endswith('.' + jobconf.pkgkey):
        jobname = filename[:-len(jobconf.pkgkey)-1]
    else:
        jobname = filename
    outputdir = pathjoin(localdir, jobname) if makefolder else localdir
    hiddendir = pathjoin(outputdir, ('.' + jobname))
    fullname = pathjoin((jobname, versionkey))
    
    if 'filecheck' in jobconf:
        if not parsebool(jobconf.filecheck, filebools):
            messages.failure('Falta(n) alguno(s) de los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobconf:
        if parsebool(jobconf.fileclash, filebools):
            messages.failure('Hay un conflicto entre algunos de los archivos de entrada')
            return
    
    for item in jobconf.inputfiles:
        for key in item.split('|'):
            importfiles.append(wordjoin('ssh', master, 'scp', qq(pathjoin(outputdir, (filename, key))), \
               '$ip:' + qq(pathjoin('$workdir', jobconf.fileexts[key]))))
    
    for item in jobconf.outputfiles:
        for key in item.split('|'):
            exportfiles.append(wordjoin('scp', q(pathjoin('$workdir', jobconf.fileexts[key])), \
                master + ':' + qq(pathjoin(outputdir, (fullname, key)))))
    
    for parset in optconf.parameters:
        if not path.isabs(parset):
            parset = pathjoin(localdir, parset)
        if path.isdir(parset):
            parset = pathjoin(parset, '.')
        importfiles.append(wordjoin('ssh', master, 'scp -r', qq(parset), '$ip:' + qq('$workdir')))
    
    if path.isdir(outputdir):
        if path.isdir(hiddendir):
            try:
                lastjob = max(listdir(hiddendir), key=int)
            except ValueError:
                pass
            else:
                jobstate = sysconf.checkjob(lastjob)
                if jobstate in sysconf.jobstates:
                    messages.failure('El trabajo', q(jobname), 'no se envió porque', sysconf.jobstates[jobstate], '(jobid {0})'.format(lastjob))
                    return
        elif path.exists(hiddendir):
            messages.failure('No se puede crear la carpeta', hiddendir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(hiddendir)
        if not set(listdir(outputdir)).isdisjoint(pathjoin((fullname, k)) for i in jobconf.outputfiles for k in i.split('|')):
            if optconf.defaultanswer is None:
                optconf.defaultanswer = dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas (si/no)?')
            if optconf.defaultanswer is False:
                messages.failure('El trabajo', q(jobname), 'no se envió por solicitud del usuario')
                return
        for item in jobconf.outputfiles:
            for key in item.split('|'):
                remove(pathjoin(outputdir, (fullname, key)))
        if localdir != outputdir:
            for item in jobconf.inputfiles:
                for key in item.split('|'):
                    remove(pathjoin(outputdir, (filename, key)))
    elif path.exists(outputdir):
        messages.failure('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outputdir)
        makedirs(hiddendir)
    
    if localdir != outputdir:
        for item in jobconf.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(localdir, (filename, key))):
                    copyfile(pathjoin(localdir, (filename, key)), pathjoin(outputdir, (filename, key)))
    
    for script in scriptTags:
        for line in jobconf[script]:
            for attr in line:
                if attr == 'var':
                    line.boolean = line[attr] in environ
                elif attr == 'file':
                    line.boolean = filebools[line[attr]]
                else:
                    messages.cfgerr(q(attr), 'no es un atributo válido de', script)
    
    comments.append(sysconf.jobname.format(jobname))
    environment.append("jobname=" + jobname)

    try:
        #TODO: Avoid writing unnecessary newlines or spaces
        t = NamedTemporaryFile(mode='w+t', delete=False)
        t.write(linejoin(i for i in comments))
        t.write(linejoin(i for i in environment))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + wordjoin('ssh', master, 'ssh $ip mkdir -m 700 "\'$workdir\'"') + '\n')
        t.write(linejoin(' ' * 2 + i for i in importfiles))
        t.write('done' + '\n')
        t.write('cd "$workdir"' + '\n')
        t.write(linejoin(str(i) for i in jobconf.prescript if i))
        t.write(wordjoin(command) + '\n')
        t.write(linejoin(str(i) for i in jobconf.postscript if i))
        t.write(linejoin(i for i in exportfiles))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + 'ssh $ip rm -f "\'$workdir\'/*"' + '\n')
        t.write(' ' * 2 + 'ssh $ip rmdir "\'$workdir\'"' + '\n')
        t.write('done' + '\n')
        t.write(linejoin(wordjoin('ssh', master, q(str(i))) for i in jobconf.offscript if i))
    finally:
        t.close()
    
    try: jobid = sysconf.submit(t.name)
    except RuntimeError as e:
        messages.failure('El sistema de colas rechazó el trabajo', q(jobname), 'con el mensaje', q(e.args[0]))
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(optconf.ncpu), 'núcleo(s) de CPU con el jobid', jobid)
        copyfile(t.name, pathjoin(hiddendir, jobid))
        remove(t.name)
    
inputlist = optconf.inputlist

if __name__ == '__main__':
    submit()

