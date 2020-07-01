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
    systemdir = path.join(bindir, 'enqueuer')
    specdir = path.join(systemdir, 'progspecs')
    makedirs(systemdir)
    makedirs(specdir)
    
    sourcedir = AbsPath(__file__).parent()
    platformspecs = path.join(sourcedir, 'specs', 'hosts')
    
    for dirname in listdir(platformspecs):
        if not path.isfile(path.join(platformspecs, dirname, 'hostspec.json')):
            messages.warning('El directorio', dirname, 'no contiene ningún archivo de configuración')
        hostspec = readspec(path.join(platformspecs, dirname, 'hostspec.json'))
        clusternames[dirname] = hostspec.clustername
        hostdirnames[hostspec.clustername] = dirname
        if hostspec.scheduler:
            if hostspec.scheduler in listdir(path.join(sourcedir, 'specs', 'queue')):
                schedulers[dirname] = hostspec.scheduler
            else:
                messages.error('El gestor de trabajos', hostspec.scheduler, 'no está soportado')

    if not clusternames:
        messages.warning('No hay hosts configurados')
        raise SystemExit()

    if path.isfile(path.join(systemdir, 'hostspec.json')):
        clustername = readspec(path.join(systemdir, 'hostspec.json')).clustername
        if clustername in clusternames.values():
            defaults['cluster'] = clustername

    selhostdir = hostdirnames[dialogs.chooseone('Seleccione la opción con la arquitectura más adecuada', choices=natsort(clusternames.values()), default=defaults.get('cluster', 'Generic'))]
    
    if not path.isfile(path.join(systemdir, 'hostspec.json')) or readspec(platformspecs, selhostdir, 'hostspec.json') == readspec(systemdir, 'hostspec.json') or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(path.join(platformspecs, selhostdir, 'hostspec.json'), path.join(systemdir, 'hostspec.json'))

    if selhostdir in schedulers:
        copyfile(path.join(sourcedir, 'specs', 'queue', schedulers[selhostdir], 'queuespec.json'), path.join(systemdir, 'queuespec.json'))
    else:
        messages.warning('Especifique el gestor de trabajos en el archivo hostspec.json y ejecute otra vez este comando')
        return
         
    for dirname in listdir(path.join(platformspecs, selhostdir, 'prog')):
        prognames[dirname] = readspec(path.join(sourcedir, 'specs', 'prog', dirname, 'progspec.json')).progname
        progdirnames[prognames[dirname]] = dirname

    if not prognames:
        messages.warning('No hay programas configurados para este host')
        raise SystemExit()

    for dirname in listdir(specdir):
        configured.append(dirname)

    selprogdirs = [progdirnames[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=natsort(prognames.values()), default=[prognames[i] for i in configured])]

    for progname in selprogdirs:
        makedirs(path.join(specdir, progname))
        hardlink(path.join(systemdir, 'hostspec.json'), path.join(specdir, progname, 'hostspec.json'))
        hardlink(path.join(systemdir, 'queuespec.json'), path.join(specdir, progname, 'queuespec.json'))
        copyfile(path.join(sourcedir, 'specs', 'prog', progname, 'progspec.json'), path.join(specdir, progname, 'progspec.json'))
        copypathspec = True
        if progname not in configured or not path.isfile(path.join(specdir, progname, 'hostprogspec.json')) or readspec(platformspecs, selhostdir, 'prog', progname, 'progspec.json') == readspec(specdir, progname, 'hostprogspec.json') or dialogs.yesno('La configuración local del programa', q(prognames[progname]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?', default=False):
            copyfile(path.join(platformspecs, selhostdir, 'prog', progname, 'progspec.json'), path.join(specdir, progname, 'hostprogspec.json'))

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

    copyfile(path.join(sourcedir, 'bin','jobsync'), path.join(bindir, 'jobsync'))
    chmod(path.join(bindir, 'jobsync'), 0o755)

    for dirname in listdir(specdir):
        if relpath:
            modulepath = path.join('${0%/*}', path.relpath(path.dirname(sourcedir), bindir))
            specpath = path.join('${0%/*}', path.relpath(path.join(specdir, dirname), bindir))
        else:
            modulepath = path.dirname(sourcedir)
            specpath = AbsPath(specdir, dirname)
        with open(path.join(sourcedir, 'bin', 'launcher'), 'r') as fr, open(path.join(bindir, dirname), 'w') as fw:
            fw.write(fr.read().format(
                python=sys.executable,
                pyldpath=pathsep.join(pyldpath),
                modulepath=modulepath,
                specpath=specpath,
            ))
        chmod(path.join(bindir, dirname), 0o755)

