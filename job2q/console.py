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
from .fileutils import AbsPath, pathjoin, mkdir, copyfile, symlink

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

    bindir = pathjoin(rootdir, 'bin')
    etcdir = pathjoin(rootdir, 'etc')
    specdir = pathjoin(etcdir, 'jobspecs')

    mkdir(bindir)
    mkdir(etcdir)
    mkdir(specdir)
    
    sourcedir = AbsPath(__file__).parent
    srchostspecdir = pathjoin(sourcedir, 'specs', 'hosts')
    srcqueuespecdir = pathjoin(sourcedir, 'specs', 'queues')

    for diritem in os.listdir(srchostspecdir):
        if not os.path.isfile(pathjoin(srchostspecdir, diritem, 'clusterconf.json')):
            messages.warning('El directorio', diritem, 'no contiene ningún archivo de configuración')
        clusterconf = readspec(pathjoin(srchostspecdir, diritem, 'clusterconf.json'))
        clusternames[diritem] = clusterconf.name
        clusterspeckeys[clusterconf.name] = diritem
        if 'scheduler' in clusterconf:
            clusterschedulers[diritem] = clusterconf.scheduler

    if os.path.isfile(pathjoin(specdir, 'clusterconf.json')):
        defaulthost = readspec(pathjoin(specdir, 'clusterconf.json')).name
        if defaulthost not in clusternames.values():
            defaulthost = 'Otro'
    else:
        defaulthost = None

    selhostname = dialogs.chooseone('¿Qué clúster desea configurar?', choices=sorted(sorted(clusternames.values()), key='Otro'.__eq__), default=defaulthost)
    selhost = clusterspeckeys[selhostname]
    
    if defaulthost is None:
        copyfile(pathjoin(srchostspecdir, selhost, 'clusterconf.json'), pathjoin(specdir, 'clusterconf.json'))
    elif selhostname != defaulthost and readspec(pathjoin(srchostspecdir, selhost, 'clusterconf.json')) != readspec(pathjoin(specdir, 'clusterconf.json')):
        if dialogs.yesno('Desea sobreescribir la configuración local del sistema?'):
            copyfile(pathjoin(srchostspecdir, selhost, 'clusterconf.json'), pathjoin(specdir, 'clusterconf.json'))

    for diritem in os.listdir(srcqueuespecdir):
        queuespecs = readspec(pathjoin(srcqueuespecdir, diritem, 'queuespec.json'))
        schedulernames[diritem] = queuespecs.schedulername
        schedulerspeckeys[queuespecs.schedulername] = diritem

    if os.path.isfile(pathjoin(specdir, 'queuespec.json')):
        defaultscheduler = readspec(pathjoin(specdir, 'queuespec.json')).schedulername
    elif selhost in clusterschedulers:
        defaultscheduler = clusterschedulers[selhost]
    else:
        defaultscheduler = None

    selschedulername = dialogs.chooseone('Seleccione el gestor de trabajos adecuado', choices=sorted(schedulernames.values()), default=defaultscheduler)
    selscheduler = schedulerspeckeys[selschedulername]
    copyfile(pathjoin(sourcedir, 'specs', 'queues', selscheduler, 'queuespec.json'), pathjoin(specdir, 'queuespec.json'))
         
    for diritem in os.listdir(pathjoin(srchostspecdir, selhost, 'packages')):
        progspecs = readspec(pathjoin(sourcedir, 'specs', 'packages', diritem, 'progspec.json'))
        packagenames[diritem] = (progspecs.longname)
        packagespeckeys[progspecs.longname] = diritem

    if not packagenames:
        messages.warning('No hay programas preconfigurados para este host')
        raise SystemExit()

    for diritem in os.listdir(specdir):
        if os.path.isdir(pathjoin(specdir, diritem)):
            configured.append(readspec(pathjoin(specdir, diritem, 'progspec.json')).longname)

    selpackagenames = dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=sorted(packagenames.values()), default=configured)

    for packagename in selpackagenames:
        package = packagespeckeys[packagename]
        mkdir(pathjoin(specdir, package))
        copyfile(pathjoin(sourcedir, 'specs', 'packages', package, 'progspec.json'), pathjoin(specdir, package, 'progspec.json'))
        copypathspec = True
        if not os.path.isfile(pathjoin(specdir, package, 'packageconf.json')):
            copyfile(pathjoin(srchostspecdir, selhost, 'packages', package, 'packageconf.json'), pathjoin(specdir, package, 'packageconf.json'))
#        elif readspec(pathjoin(srchostspecdir, selhost, 'packages', package, 'packageconf.json')) != readspec(pathjoin(specdir, package, 'packageconf.json')):
#            if dialogs.yesno('La configuración local del programa', q(packagenames[package]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?'):
#                copyfile(pathjoin(srchostspecdir, selhost, 'packages', package, 'packageconf.json'), pathjoin(specdir, package, 'packageconf.json'))

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

    with open(pathjoin(sourcedir, 'bin', 'job2q'), 'r') as r, open(pathjoin(bindir, 'job2q'), 'w') as w:
        w.write(r.read().format(**installation))

    with open(pathjoin(sourcedir, 'bin', 'job2q.target'), 'r') as r, open(pathjoin(bindir, 'job2q.target'), 'w') as w:
        w.write(r.read().format(**installation))

    for diritem in os.listdir(specdir):
        if os.path.isdir(pathjoin(specdir, diritem)):
            symlink(pathjoin(bindir, 'job2q.target'), pathjoin(bindir, diritem))

    copyfile(pathjoin(sourcedir, 'bin','jobsync'), pathjoin(bindir, 'jobsync'))

    os.chmod(pathjoin(bindir, 'job2q'), 0o755)
    os.chmod(pathjoin(bindir, 'job2q.target'), 0o755)
    os.chmod(pathjoin(bindir, 'jobsync'), 0o755)

