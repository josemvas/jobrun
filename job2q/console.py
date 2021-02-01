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
from .readspec import readspec
from .fileutils import AbsPath, NotAbsolutePath, mkdir, copyfile, link, symlink

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
    
    rootdir = dialogs.inputpath('Escriba la ruta donde se instalarán los programas', check=isdir)
    bindir = path.join(rootdir, 'bin')
    etcdir = path.join(rootdir, 'etc')
    specdir = path.join(etcdir, 'jobspecs')

    mkdir(bindir)
    mkdir(etcdir)
    mkdir(specdir)
    
    sourcedir = AbsPath(__file__).parent()
    platformspecs = path.join(sourcedir, 'specs', 'hosts')
    
    for spec in listdir(platformspecs):
        if not path.isfile(path.join(platformspecs, spec, 'hostspec.json')):
            messages.warning('El directorio', spec, 'no contiene ningún archivo de configuración')
        hostspec = readspec(path.join(platformspecs, spec, 'hostspec.json'))
        clusternames[spec] = hostspec.clustername
        hostdirnames[hostspec.clustername] = spec
        if hostspec.scheduler:
            if hostspec.scheduler in listdir(path.join(sourcedir, 'specs', 'queue')):
                schedulers[spec] = hostspec.scheduler
            else:
                messages.error('El gestor de trabajos', hostspec.scheduler, 'no está soportado')

    if not clusternames:
        messages.warning('No hay hosts configurados')
        raise SystemExit()

    defaulthost = '[otro]'
    if path.isfile(path.join(etcdir, 'hostspec.json')):
        clustername = readspec(path.join(etcdir, 'hostspec.json')).clustername
        if clustername in clusternames.values():
            defaulthost = clustername

    selhostdir = hostdirnames[dialogs.chooseone('¿Qué clúster desea configurar?', choices=natsort(clusternames.values()), default=defaulthost)]
    
    if not path.isfile(path.join(etcdir, 'hostspec.json')) or readspec(path.join(platformspecs, selhostdir, 'hostspec.json')) == readspec(path.join(etcdir, 'hostspec.json')) or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(path.join(platformspecs, selhostdir, 'hostspec.json'), path.join(etcdir, 'hostspec.json'))

    if selhostdir in schedulers:
        copyfile(path.join(sourcedir, 'specs', 'queue', schedulers[selhostdir], 'queuespec.json'), path.join(etcdir, 'queuespec.json'))
    else:
        messages.warning('Especifique el gestor de trabajos en el archivo', path.join(etcdir, 'queuespec.json'), 'y ejecute otra vez este comando')
        return
         
    for spec in listdir(path.join(platformspecs, selhostdir, 'progs')):
        prognames[spec] = readspec(path.join(sourcedir, 'specs', 'progs', spec, 'progspec.json')).progname
        progdirnames[prognames[spec]] = spec

    if not prognames:
        messages.warning('No hay programas configurados para este host')
        raise SystemExit()

    for spec in listdir(specdir):
        configured.append(spec)

    selprogdirs = [progdirnames[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=natsort(prognames.values()), default=[prognames[i] for i in configured])]

    for progname in selprogdirs:
        mkdir(path.join(specdir, progname))
        link(path.join(etcdir, 'hostspec.json'), path.join(specdir, progname, 'hostspec.json'))
        link(path.join(etcdir, 'queuespec.json'), path.join(specdir, progname, 'queuespec.json'))
        copyfile(path.join(sourcedir, 'specs', 'progs', progname, 'progspec.json'), path.join(specdir, progname, 'progspec.json'))
        copypathspec = True
        if progname not in configured or not path.isfile(path.join(specdir, progname, 'hostprogspec.json')) or readspec(path.join(platformspecs, selhostdir, 'progs', progname, 'progspec.json')) == readspec(path.join(specdir, progname, 'hostprogspec.json')) or dialogs.yesno('La configuración local del programa', q(prognames[progname]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?', default=False):
            copyfile(path.join(platformspecs, selhostdir, 'progs', progname, 'progspec.json'), path.join(specdir, progname, 'hostprogspec.json'))

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.search(r'^([^\t]+):$', line)
        if match and match.group(1) not in libpath:
            libpath.append(match.group(1))

    pyldpath.append('$LD_LIBRARY_PATH')
    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.search(r'=> (.+) \(0x', line)
        if match:
            libdir = path.dirname(match.group(1))
            if libdir not in libpath and libdir not in pyldpath:
                pyldpath.append(libdir)

    modulepath = path.dirname(sourcedir)

    with open(path.join(sourcedir, 'bin', 'job2q'), 'r') as fr, open(path.join(bindir, 'job2q'), 'w') as fw:
        fw.write(fr.read().format(
            python=sys.executable,
            pyldpath=pathsep.join(pyldpath),
            modulepath=modulepath,
            specdir=specdir
        ))

    for spec in listdir(specdir):
        symlink(path.join(bindir, 'job2q'), path.join(bindir, spec))

    copyfile(path.join(sourcedir, 'bin','jobsync'), path.join(bindir, 'jobsync'))

    chmod(path.join(bindir, 'jobsync'), 0o755)
    chmod(path.join(bindir, 'job2q'), 0o755)

