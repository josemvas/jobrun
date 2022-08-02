import os
import sys
import re
from string import Template
from argparse import ArgumentParser
from subprocess import check_output, DEVNULL
from clinterface import Selector, Completer
from . import messages
from .utils import q, natsorted as sorted
from .readspec import readspec
from .fileutils import AbsPath, pathjoin, mkdir, copyfile, symlink

selector = Selector()
completer = Completer()

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

    completer.message = 'Escriba la ruta donde se instalarán los programas'
    rootdir = AbsPath(completer.directory_path(), cwd=os.getcwd())

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
        clusternames[diritem] = clusterconf.clustername
        clusterspeckeys[clusterconf.clustername] = diritem
        clusterschedulers[diritem] = clusterconf.schedulername

    for diritem in os.listdir(srcqueuespecdir):
        queuespecs = readspec(pathjoin(srcqueuespecdir, diritem, 'queuespec.json'))
        schedulernames[diritem] = queuespecs.schedulername
        schedulerspeckeys[queuespecs.schedulername] = diritem

    if os.path.isfile(pathjoin(specdir, 'clusterconf.json')):
        selector.message = '¿Qué clúster desea configurar?'
        selector.options = sorted(sorted(clusternames.values()), key='Nuevo'.__eq__, reverse=True)
        clusterconf = readspec(pathjoin(specdir, 'clusterconf.json'))
        if clusterconf.clustername in clusternames.values():
            selector.default = clusterconf.clustername
        selhost = clusterspeckeys[selector.single_choice()]
        if clusternames[selhost] != clusterconf.clustername and readspec(pathjoin(srchostspecdir, selhost, 'clusterconf.json')) != readspec(pathjoin(specdir, 'clusterconf.json')):
            completer.message = 'Desea sobreescribir la configuración local del sistema?'
            completer.options = {True: ['si', 'yes'], False: ['no']}
            if completer.binary_choice():
                copyfile(pathjoin(srchostspecdir, selhost, 'clusterconf.json'), pathjoin(specdir, 'clusterconf.json'))
        selector.message = 'Seleccione el gestor de trabajos adecuado'
        selector.options = sorted(schedulernames.values())
        selector.default = clusterconf.schedulername
        selschedulername = selector.single_choice()
        selscheduler = schedulerspeckeys[selschedulername]
        copyfile(pathjoin(sourcedir, 'specs', 'queues', selscheduler, 'queuespec.json'), pathjoin(specdir, 'queuespec.json'))
    else:
        selector.message = '¿Qué clúster desea configurar?'
        selector.options = sorted(sorted(clusternames.values()), key='Nuevo'.__eq__, reverse=True)
        selhost = clusterspeckeys[selector.single_choice()]
        copyfile(pathjoin(srchostspecdir, selhost, 'clusterconf.json'), pathjoin(specdir, 'clusterconf.json'))
        selector.message = 'Seleccione el gestor de trabajos adecuado'
        selector.options = sorted(schedulernames.values())
        selector.default = clusterschedulers[selhost]
        selschedulername = selector.single_choice()
        selscheduler = schedulerspeckeys[selschedulername]
        copyfile(pathjoin(sourcedir, 'specs', 'queues', selscheduler, 'queuespec.json'), pathjoin(specdir, 'queuespec.json'))

    for diritem in os.listdir(pathjoin(srchostspecdir, selhost, 'packages')):
        progspecs = readspec(pathjoin(sourcedir, 'specs', 'packages', diritem, 'progspec.json'))
        packagenames[diritem] = (progspecs.progname)
        packagespeckeys[progspecs.progname] = diritem

    if not packagenames:
        messages.warning('No hay programas preconfigurados para este host')
        raise SystemExit()

    for diritem in os.listdir(specdir):
        if os.path.isdir(pathjoin(specdir, diritem)):
            configured.append(readspec(pathjoin(specdir, diritem, 'progspec.json')).progname)

    selector.message = 'Seleccione los programas que desea configurar o reconfigurar'
    selector.options = sorted(packagenames.values())
    selector.default = configured
    selpackagenames = selector.multiple_choice()

    for packagename in selpackagenames:
        package = packagespeckeys[packagename]
        mkdir(pathjoin(specdir, package))
        copyfile(pathjoin(sourcedir, 'specs', 'packages', package, 'progspec.json'), pathjoin(specdir, package, 'progspec.json'))
        copypathspec = True
        if not os.path.isfile(pathjoin(specdir, package, 'packageconf.json')):
            copyfile(pathjoin(srchostspecdir, selhost, 'packages', package, 'packageconf.json'), pathjoin(specdir, package, 'packageconf.json'))
#        elif readspec(pathjoin(srchostspecdir, selhost, 'packages', package, 'packageconf.json')) != readspec(pathjoin(specdir, package, 'packageconf.json')):
#            completer.message = _('La configuración local del programa $name difiere de la configuración por defecto, ¿desea sobreescribirla?').substitute(name=packagenames[package])
#            completer.options = {True: ['si', 'yes'], False: ['no']}
#            if completer.binary_choice():
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

    with open(pathjoin(sourcedir, 'bin', 'jobsubmit'), 'r') as r, open(pathjoin(bindir, 'jobsubmit'), 'w') as w:
        w.write(Template(r.read()).substitute(installation))

    for diritem in os.listdir(specdir):
        if os.path.isdir(pathjoin(specdir, diritem)):
            symlink(pathjoin(bindir, 'jobsubmit'), pathjoin(bindir, diritem))

    copyfile(pathjoin(sourcedir, 'bin','jobsync'), pathjoin(bindir, 'jobsync'))

    os.chmod(pathjoin(bindir, 'jobsubmit'), 0o755)
    os.chmod(pathjoin(bindir, 'jobsync'), 0o755)

