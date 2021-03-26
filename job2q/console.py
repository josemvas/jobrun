# -*- coding: utf-8 -*-
import os
import sys
import re
from argparse import ArgumentParser
from subprocess import check_output, DEVNULL
from . import dialogs
from . import messages
from .utils import natsort, q
from .readspec import readspec
from .fileutils import AbsPath, NotAbsolutePath, buildpath, mkdir, copyfile, link, symlink

def setup(relpath=False):

    libpath = []
    pyldpath = []
    configured = []
    clusternames = []
    clusterdirs = {}
    pkgdirlist = {}
    schedulers = {}
    packagename = {}
    defaults = {}
    
    rootdir = dialogs.inputpath('Escriba la ruta donde se instalarán los programas', check=os.path.isdir)
    bindir = buildpath(rootdir, 'bin')
    etcdir = buildpath(rootdir, 'etc')
    specdir = buildpath(etcdir, 'jobspecs')

    mkdir(bindir)
    mkdir(etcdir)
    mkdir(specdir)
    
    sourcedir = AbsPath(__file__).parent()
    hostspecdir = buildpath(sourcedir, 'specs', 'hosts')

    hostspecs = readspec(buildpath(sourcedir, 'specs', 'newhost', 'hostspecs.json'))
    clusterdirs[hostspecs.clustername] = buildpath(sourcedir, 'specs', 'newhost')
    clusternames.append(hostspecs.clustername)
    defaulthost = hostspecs.clustername

    for spec in os.listdir(hostspecdir):
        if not os.path.isfile(buildpath(hostspecdir, spec, 'hostspecs.json')):
            messages.warning('El directorio', spec, 'no contiene ningún archivo de configuración')
        hostspecs = readspec(buildpath(hostspecdir, spec, 'hostspecs.json'))
        clusternames.append(hostspecs.clustername)
        clusterdirs[hostspecs.clustername] = buildpath(hostspecdir, spec)
        if hostspecs.scheduler in os.listdir(buildpath(sourcedir, 'specs', 'queues')):
            schedulers[hostspecs.clustername] = hostspecs.scheduler
        else:
            messages.error('El gestor de trabajos', hostspecs.scheduler, 'no está soportado')

    if os.path.isfile(buildpath(etcdir, 'hostspecs.json')):
        clustername = readspec(buildpath(etcdir, 'hostspecs.json')).clustername
        if clustername in clusternames:
            defaulthost = clustername

    selhostname = dialogs.chooseone('¿Qué clúster desea configurar?', choices=clusternames, default=defaulthost)
    selhostdir = clusterdirs[selhostname]
    
    if not os.path.isfile(buildpath(etcdir, 'hostspecs.json')) or readspec(buildpath(selhostdir, 'hostspecs.json')) == readspec(buildpath(etcdir, 'hostspecs.json')) or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(buildpath(selhostdir, 'hostspecs.json'), buildpath(etcdir, 'hostspecs.json'))

    if selhostname in schedulers:
        copyfile(buildpath(sourcedir, 'specs', 'queues', schedulers[selhostname], 'queuespecs.json'), buildpath(etcdir, 'queuespecs.json'))
    else:
        messages.warning('Especifique el gestor de trabajos en el archivo', buildpath(etcdir, 'queuespecs.json'), 'y ejecute otra vez este comando')
        return
         
    for spec in os.listdir(buildpath(selhostdir, 'packages')):
        packagename[spec] = readspec(buildpath(sourcedir, 'specs', 'packages', spec, 'packagespecs.json')).packagename
        pkgdirlist[packagename[spec]] = spec

    if not packagename:
        messages.warning('No hay programas configurados para este host')
        raise SystemExit()

    for spec in os.listdir(specdir):
        configured.append(spec)

    selpkgdirlist = [pkgdirlist[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=natsort(packagename.values()), default=[packagename[i] for i in configured])]

    for pkgdir in selpkgdirlist:
        mkdir(buildpath(specdir, pkgdir))
        link(buildpath(etcdir, 'hostspecs.json'), buildpath(specdir, pkgdir, 'hostspecs.json'))
        link(buildpath(etcdir, 'queuespecs.json'), buildpath(specdir, pkgdir, 'queuespecs.json'))
        copyfile(buildpath(sourcedir, 'specs', 'packages', pkgdir, 'packagespecs.json'), buildpath(specdir, pkgdir, 'packagespecs.json'))
        copypathspec = True
        if pkgdir not in configured or not os.path.isfile(buildpath(specdir, pkgdir, 'packageconf.json')) or readspec(buildpath(selhostdir, 'packages', pkgdir, 'packageconf.json')) == readspec(buildpath(specdir, pkgdir, 'packageconf.json')) or dialogs.yesno('La configuración local del programa', q(packagename[pkgdir]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?', default=False):
            copyfile(buildpath(selhostdir, 'packages', pkgdir, 'packageconf.json'), buildpath(specdir, pkgdir, 'packageconf.json'))

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match and match.group(1) not in libpath:
            libpath.append(match.group(1))

    pyldpath.append('$LD_LIBRARY_PATH')
    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            libdir = os.path.dirname(match.group(1))
            if libdir not in libpath and libdir not in pyldpath:
                pyldpath.append(libdir)

    modulepath = os.path.dirname(sourcedir)

    with open(buildpath(sourcedir, 'bin', 'job2q'), 'r') as fr, open(buildpath(bindir, 'job2q'), 'w') as fw:
        fw.write(fr.read().format(
            python=sys.executable,
            pyldpath=os.pathsep.join(pyldpath),
            modulepath=modulepath,
            specdir=specdir
        ))

    for spec in os.listdir(specdir):
        symlink(buildpath(bindir, 'job2q'), buildpath(bindir, spec))

    copyfile(buildpath(sourcedir, 'bin','jobsync'), buildpath(bindir, 'jobsync'))

    os.chmod(buildpath(bindir, 'jobsync'), 0o755)
    os.chmod(buildpath(bindir, 'job2q'), 0o755)

