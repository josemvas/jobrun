# -*- coding: utf-8 -*-
import os
import sys
import re
from argparse import ArgumentParser
from subprocess import check_output, DEVNULL
from . import dialogs
from . import messages
from .utils import q
from .readspec import readspec
from .fileutils import AbsPath, NotAbsolutePath, buildpath, mkdir, copyfile, link, symlink

def install(relpath=False):

    libpath = []
    pyldpath = []
    configured = []
    clusternames = {}
    clusterspecnames = {}
    clusterschedulers = {}
    packagenames = {}
    packagespecnames = {}
    schedulernames = {}
    schedulerspecnames = {}
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
    queuespecdir = buildpath(sourcedir, 'specs', 'queues')

    for specname in os.listdir(hostspecdir):
        if not os.path.isfile(buildpath(hostspecdir, specname, 'clusterspecs.json')):
            messages.warning('El directorio', specname, 'no contiene ningún archivo de configuración')
        clusterspecs = readspec(buildpath(hostspecdir, specname, 'clusterspecs.json'))
        clusternames[specname] = clusterspecs.clustername
        clusterspecnames[clusterspecs.clustername] = specname
        if 'scheduler' in clusterspecs:
            clusterschedulers[specname] = clusterspecs.scheduler

    if os.path.isfile(buildpath(etcdir, 'clusterspecs.json')):
        defaulthost = readspec(buildpath(etcdir, 'clusterspecs.json')).clustername
    else:
        defaulthost = None

    selhost = clusterspecnames[dialogs.chooseone('¿Qué clúster desea configurar?', choices=sorted(sorted(clusternames.values()), key='Otro'.__eq__), default=defaulthost)]
    
    if not os.path.isfile(buildpath(etcdir, 'clusterspecs.json')) or readspec(buildpath(hostspecdir, selhost, 'clusterspecs.json')) == readspec(buildpath(etcdir, 'clusterspecs.json')) or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(buildpath(hostspecdir, selhost, 'clusterspecs.json'), buildpath(etcdir, 'clusterspecs.json'))

    for specname in os.listdir(queuespecdir):
        queuespecs = readspec(buildpath(queuespecdir, specname, 'queuespecs.json'))
        schedulernames[specname] = queuespecs.schedulername
        schedulerspecnames[queuespecs.schedulername] = specname

    if os.path.isfile(buildpath(etcdir, 'queuespecs.json')):
        defaultscheduler = readspec(buildpath(etcdir, 'queuespecs.json')).schedulername
    elif selhost in clusterschedulers:
        defaultscheduler = schedulernames[clusterschedulers[selhost]]
    else:
        defaultscheduler = None

    selscheduler = schedulerspecnames[dialogs.chooseone('Seleccione el gestor de trabajos adecuado', choices=sorted(schedulernames.values()), default=defaultscheduler)]
    copyfile(buildpath(sourcedir, 'specs', 'queues', selscheduler, 'queuespecs.json'), buildpath(etcdir, 'queuespecs.json'))
         
    for specname in os.listdir(buildpath(hostspecdir, selhost, 'packages')):
        packagespecs = readspec(buildpath(sourcedir, 'specs', 'packages', specname, 'packagespecs.json'))
        packagenames[specname] = (packagespecs.packagename)
        packagespecnames[packagespecs.packagename] = specname

    if not packagenames:
        messages.warning('No hay programas preconfigurados para este host')
        raise SystemExit()

    for specname in os.listdir(specdir):
        configured.append(readspec(buildpath(specdir, specname, 'packagespecs.json')).packagename)

    selpackages = [packagespecnames[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=sorted(packagenames.values()), default=configured)]

    for package in selpackages:
        mkdir(buildpath(specdir, package))
        link(buildpath(etcdir, 'clusterspecs.json'), buildpath(specdir, package, 'clusterspecs.json'))
        link(buildpath(etcdir, 'queuespecs.json'), buildpath(specdir, package, 'queuespecs.json'))
        copyfile(buildpath(sourcedir, 'specs', 'packages', package, 'packagespecs.json'), buildpath(specdir, package, 'packagespecs.json'))
        copypathspec = True
        if package not in configured or not os.path.isfile(buildpath(specdir, package, 'packageconf.json')) or readspec(buildpath(hostspecdir, selhost, 'packages', package, 'packageconf.json')) == readspec(buildpath(specdir, package, 'packageconf.json')) or dialogs.yesno('La configuración local del programa', q(packagenames[package]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?', default=False):
            copyfile(buildpath(hostspecdir, selhost, 'packages', package, 'packageconf.json'), buildpath(specdir, package, 'packageconf.json'))

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

    for specname in os.listdir(specdir):
        symlink(buildpath(bindir, 'job2q'), buildpath(bindir, specname))

    copyfile(buildpath(sourcedir, 'bin','jobsync'), buildpath(bindir, 'jobsync'))

    os.chmod(buildpath(bindir, 'jobsync'), 0o755)
    os.chmod(buildpath(bindir, 'job2q'), 0o755)

