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
from .fileutils import AbsPath, NotAbsolutePath, formatpath, mkdir, copyfile, symlink

def install(relpath=False):

    pylibs = []
    syslibs = []
    configured = []
    clusternames = {}
    clusterspeckeys = {}
    clusterschedulers = {}
    packagenames = {}
    packagespeckeys = {}
    schedulernames = {}
    schedulerspeckeys = {}
    defaults = {}
    
    rootdir = dialogs.inputpath('Escriba la ruta donde se instalarán los programas', check=os.path.isdir)
    bindir = formatpath(rootdir, 'bin')
    etcdir = formatpath(rootdir, 'etc')
    specdir = formatpath(etcdir, 'jobspecs')

    mkdir(bindir)
    mkdir(etcdir)
    mkdir(specdir)
    
    sourcedir = AbsPath(__file__).parent
    hostspecdir = formatpath(sourcedir, 'specs', 'hosts')
    queuespecdir = formatpath(sourcedir, 'specs', 'queues')

    for specname in os.listdir(hostspecdir):
        if not os.path.isfile(formatpath(hostspecdir, specname, 'clusterspecs.json')):
            messages.warning('El directorio', specname, 'no contiene ningún archivo de configuración')
        clusterspecs = readspec(formatpath(hostspecdir, specname, 'clusterspecs.json'))
        clusternames[specname] = clusterspecs.clustername
        clusterspeckeys[clusterspecs.clustername] = specname
        if 'scheduler' in clusterspecs:
            clusterschedulers[specname] = clusterspecs.scheduler

    if os.path.isfile(formatpath(etcdir, 'clusterspecs.json')):
        defaulthost = readspec(formatpath(etcdir, 'clusterspecs.json')).clustername
        if defaulthost not in clusternames.values():
            defaulthost = 'Otro'
    else:
        defaulthost = None

    selhostname = dialogs.chooseone('¿Qué clúster desea configurar?', choices=sorted(sorted(clusternames.values()), key='Otro'.__eq__), default=defaulthost)
    selhost = clusterspeckeys[selhostname]
    
    if not os.path.isfile(formatpath(etcdir, 'clusterspecs.json')) or readspec(formatpath(hostspecdir, selhost, 'clusterspecs.json')) == readspec(formatpath(etcdir, 'clusterspecs.json')) or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(formatpath(hostspecdir, selhost, 'clusterspecs.json'), formatpath(etcdir, 'clusterspecs.json'))

    for specname in os.listdir(queuespecdir):
        queuespecs = readspec(formatpath(queuespecdir, specname, 'queuespecs.json'))
        schedulernames[specname] = queuespecs.schedulername
        schedulerspeckeys[queuespecs.schedulername] = specname

    if os.path.isfile(formatpath(etcdir, 'queuespecs.json')):
        defaultscheduler = readspec(formatpath(etcdir, 'queuespecs.json')).schedulername
    elif selhost in clusterschedulers:
        defaultscheduler = clusterschedulers[selhost]
    else:
        defaultscheduler = None

    selschedulername = dialogs.chooseone('Seleccione el gestor de trabajos adecuado', choices=sorted(schedulernames.values()), default=defaultscheduler)
    selscheduler = schedulerspeckeys[selschedulername]
    copyfile(formatpath(sourcedir, 'specs', 'queues', selscheduler, 'queuespecs.json'), formatpath(etcdir, 'queuespecs.json'))
         
    for specname in os.listdir(formatpath(hostspecdir, selhost, 'packages')):
        packagespecs = readspec(formatpath(sourcedir, 'specs', 'packages', specname, 'packagespecs.json'))
        packagenames[specname] = (packagespecs.packagename)
        packagespeckeys[packagespecs.packagename] = specname

    if not packagenames:
        messages.warning('No hay programas preconfigurados para este host')
        raise SystemExit()

    for specname in os.listdir(specdir):
        configured.append(readspec(formatpath(specdir, specname, 'packagespecs.json')).packagename)

    selpackagenames = dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=sorted(packagenames.values()), default=configured)

    for packagename in selpackagenames:
        package = packagespeckeys[packagename]
        mkdir(formatpath(specdir, package))
        symlink(formatpath(etcdir, 'clusterspecs.json'), formatpath(specdir, package, 'clusterspecs.json'))
        symlink(formatpath(etcdir, 'queuespecs.json'), formatpath(specdir, package, 'queuespecs.json'))
        copyfile(formatpath(sourcedir, 'specs', 'packages', package, 'packagespecs.json'), formatpath(specdir, package, 'packagespecs.json'))
        copypathspec = True
        if packagename not in configured or not os.path.isfile(formatpath(specdir, package, 'packageconf.json')) or readspec(formatpath(hostspecdir, selhost, 'packages', package, 'packageconf.json')) == readspec(formatpath(specdir, package, 'packageconf.json')) or dialogs.yesno('La configuración local del programa', q(packagenames[package]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?'):
            copyfile(formatpath(hostspecdir, selhost, 'packages', package, 'packageconf.json'), formatpath(specdir, package, 'packageconf.json'))

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match and match.group(1) not in syslibs:
            syslibs.append(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            libdir = os.path.dirname(match.group(1))
            if libdir not in syslibs:
                pylibs.append(libdir)

    installation = dict(
        python = sys.executable,
        libpath = os.pathsep.join(pylibs),
        moduledir = os.path.dirname(sourcedir),
        specdir = specdir,
    )

    with open(formatpath(sourcedir, 'bin', 'job2q'), 'r') as r, open(formatpath(bindir, 'job2q'), 'w') as w:
        w.write(r.read().format(**installation))

    with open(formatpath(sourcedir, 'bin', 'job2q.target'), 'r') as r, open(formatpath(bindir, 'job2q.target'), 'w') as w:
        w.write(r.read().format(**installation))

    for specname in os.listdir(specdir):
        symlink(formatpath(bindir, 'job2q.target'), formatpath(bindir, specname))

    copyfile(formatpath(sourcedir, 'bin','jobsync'), formatpath(bindir, 'jobsync'))

    os.chmod(formatpath(bindir, 'job2q'), 0o755)
    os.chmod(formatpath(bindir, 'job2q.target'), 0o755)
    os.chmod(formatpath(bindir, 'jobsync'), 0o755)

