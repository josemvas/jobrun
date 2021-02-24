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
    clusternames = []
    clusterdirs = {}
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
    hostspecdir = path.join(sourcedir, 'specs', 'hosts')

    hostspec = readspec(path.join(sourcedir, 'specs', 'newhost', 'hostspec.json'))
    clusterdirs[hostspec.clustername] = path.join(sourcedir, 'specs', 'newhost')
    clusternames.append(hostspec.clustername)
    defaulthost = hostspec.clustername

    for spec in listdir(hostspecdir):
        if not path.isfile(path.join(hostspecdir, spec, 'hostspec.json')):
            messages.warning('El directorio', spec, 'no contiene ningún archivo de configuración')
        hostspec = readspec(path.join(hostspecdir, spec, 'hostspec.json'))
        clusternames.append(hostspec.clustername)
        clusterdirs[hostspec.clustername] = path.join(hostspecdir, spec)
        if hostspec.scheduler in listdir(path.join(sourcedir, 'specs', 'queue')):
            schedulers[hostspec.clustername] = hostspec.scheduler
        else:
            messages.error('El gestor de trabajos', hostspec.scheduler, 'no está soportado')

    if path.isfile(path.join(etcdir, 'hostspec.json')):
        clustername = readspec(path.join(etcdir, 'hostspec.json')).clustername
        if clustername in clusternames:
            defaulthost = clustername

    selhostname = dialogs.chooseone('¿Qué clúster desea configurar?', choices=clusternames, default=defaulthost)
    selhostdir = clusterdirs[selhostname]
    
    if not path.isfile(path.join(etcdir, 'hostspec.json')) or readspec(path.join(selhostdir, 'hostspec.json')) == readspec(path.join(etcdir, 'hostspec.json')) or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(path.join(selhostdir, 'hostspec.json'), path.join(etcdir, 'hostspec.json'))

    if selhostname in schedulers:
        copyfile(path.join(sourcedir, 'specs', 'queue', schedulers[selhostname], 'queuespec.json'), path.join(etcdir, 'queuespec.json'))
    else:
        messages.warning('Especifique el gestor de trabajos en el archivo', path.join(etcdir, 'queuespec.json'), 'y ejecute otra vez este comando')
        return
         
    for spec in listdir(path.join(selhostdir, 'progs')):
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
        if progname not in configured or not path.isfile(path.join(specdir, progname, 'hostprogspec.json')) or readspec(path.join(selhostdir, 'progs', progname, 'progspec.json')) == readspec(path.join(specdir, progname, 'hostprogspec.json')) or dialogs.yesno('La configuración local del programa', q(prognames[progname]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?', default=False):
            copyfile(path.join(selhostdir, 'progs', progname, 'progspec.json'), path.join(specdir, progname, 'hostprogspec.json'))

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

