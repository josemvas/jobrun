# -*- coding: utf-8 -*-
import re
import sys
from subprocess import check_output, DEVNULL
from os import path, listdir, chmod, pathsep
from argparse import ArgumentParser
from os.path import isfile, isdir
from . import dialogs
from . import messages
from .utils import natsort, q
from .specparse import readspec
from .fileutils import AbsPath, NotAbsolutePath, rmdir, makedirs, copyfile, hardlink

def setup(relpath=False):

    libpath = []
    pyldpath = []
    configured = []
    clusternames = {}
    hostdirnames = {}
    progdirnames = {}
    schedulers = {}
    prognames = {}
    defaults = {}
    
    bindir = dialogs.inputpath('Escriba la ruta donde se instalarán los programas', check=isdir)
    enqueuerdir = path.join(bindir, 'enqueuer')
    jobspecdir = path.join(enqueuerdir, 'jobspecs')
    makedirs(enqueuerdir)
    makedirs(jobspecdir)
    
    sourcedir = AbsPath(__file__).parent()
    execdir = path.join(sourcedir, 'execs')
    specdir = path.join(sourcedir, 'specs')
    corespecdir = path.join(specdir, 'core')
    hostspecdir = path.join(specdir, 'host')
    queuespecdir = path.join(specdir, 'queue')
    
    for dirname in listdir(hostspecdir):
        if not path.isfile(path.join(hostspecdir, dirname, 'hostspec.json')):
            messages.warning('El directorio', dirname, 'no contiene ningún archivo de configuración')
        hostspec = readspec(path.join(hostspecdir, dirname, 'hostspec.json'))
        clusternames[dirname] = hostspec.clustername
        hostdirnames[hostspec.clustername] = dirname
        if hostspec.scheduler:
            if hostspec.scheduler in listdir(queuespecdir):
                schedulers[dirname] = hostspec.scheduler
            else:
                messages.error('El gestor de trabajos', hostspec.scheduler, 'no está soportado')

    if not clusternames:
        messages.warning('No hay hosts configurados')
        raise SystemExit()

    if path.isfile(path.join(enqueuerdir, 'hostspec.json')):
        clustername = readspec(path.join(enqueuerdir, 'hostspec.json')).clustername
        if clustername in clusternames.values():
            defaults['cluster'] = clustername

    selhostdir = hostdirnames[dialogs.chooseone('Seleccione la opción con la arquitectura más adecuada', choices=natsort(clusternames.values()), default=defaults.get('cluster', 'Generic'))]
    
    if not path.isfile(path.join(enqueuerdir, 'hostspec.json')) or readspec(hostspecdir, selhostdir, 'hostspec.json') == readspec(enqueuerdir, 'hostspec.json') or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(path.join(hostspecdir, selhostdir, 'hostspec.json'), path.join(enqueuerdir, 'hostspec.json'))

    if selhostdir in schedulers:
        copyfile(path.join(queuespecdir, schedulers[selhostdir], 'queuespec.json'), path.join(enqueuerdir, 'queuespec.json'))
    else:
        messages.warning('Especifique el gestor de trabajos en el archivo hostspec.json y ejecute otra vez este comando')
        return
         
    for dirname in listdir(path.join(hostspecdir, selhostdir, 'pathspecs')):
        prognames[dirname] = readspec(path.join(corespecdir, dirname, 'corespec.json')).progname
        progdirnames[prognames[dirname]] = dirname

    if not prognames:
        messages.warning('No hay programas configurados para este host')
        raise SystemExit()

    for dirname in listdir(jobspecdir):
        configured.append(dirname)

    selprogdirs = [progdirnames[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=natsort(prognames.values()), default=[prognames[i] for i in configured])]

    for progdir in selprogdirs:
        makedirs(path.join(jobspecdir, progdir))
        hardlink(path.join(enqueuerdir, 'hostspec.json'), path.join(jobspecdir, progdir, 'hostspec.json'))
        hardlink(path.join(enqueuerdir, 'queuespec.json'), path.join(jobspecdir, progdir, 'queuespec.json'))
        copyfile(path.join(corespecdir, progdir, 'corespec.json'), path.join(jobspecdir, progdir, 'corespec.json'))
        copypathspec = True
        if progdir not in configured or not path.isfile(path.join(jobspecdir, progdir, 'pathspec.json')) or readspec(hostspecdir, selhostdir, 'pathspecs', progdir, 'pathspec.json') == readspec(jobspecdir, progdir, 'pathspec.json') or dialogs.yesno('La configuración local del programa', q(prognames[progdir]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?', default=False):
            copyfile(path.join(hostspecdir, selhostdir, 'pathspecs', progdir, 'pathspec.json'), path.join(jobspecdir, progdir, 'pathspec.json'))

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.search(r'^([^\t]+):$', line)
        if match and match.group(1) not in libpath:
            libpath.append(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.search(r'=> (.+) \(0x', line)
        if match:
            libdir = path.dirname(match.group(1))
            if libdir not in libpath and libdir not in pyldpath:
                pyldpath.append(libdir)

    copyfile(path.join(execdir, 'jobsync'), path.join(bindir, 'jobsync'))
    chmod(path.join(bindir, 'jobsync'), 0o755)

    for dirname in listdir(jobspecdir):
        if relpath:
            modulepath = path.join('${0%/*}', path.relpath(path.dirname(sourcedir), bindir))
            specpath = path.join('${0%/*}', path.relpath(path.join(jobspecdir, dirname), bindir))
        else:
            modulepath = path.dirname(sourcedir)
            specpath = AbsPath(jobspecdir, dirname)
        with open(path.join(execdir, 'launcher'), 'r') as fr, open(path.join(bindir, dirname), 'w') as fw:
            fw.write(fr.read().format(
                python=sys.executable,
                pyldpath=pathsep.join(pyldpath),
                modulepath=modulepath,
                specpath=specpath,
            ))
        chmod(path.join(bindir, dirname), 0o755)

