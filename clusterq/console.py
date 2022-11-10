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

def configure():

    pylibs = []
    syslibs = []
    clusterkeys = {}
    clusternames = {}
    clusterschedulers = {}
    packagelist = []
    packagekeys = {}
    packagenames = {}
    enabledpackages = []
    queuekeys = {}
    queueschedulers = {}

    srcdir = AbsPath(__file__).parent

    completer.message = 'Escriba la ruta donde se instalarán los programas'
    installdir = AbsPath(completer.directory_path(), cwd=os.getcwd())

    bindir = pathjoin(installdir, 'bin')
    cfgdir = pathjoin(installdir, 'clusterq')

    mkdir(bindir)
    mkdir(cfgdir)

    mkdir(pathjoin(cfgdir, 'iospecs'))
    mkdir(pathjoin(cfgdir, 'packages'))

    for diritem in os.listdir(pathjoin(srcdir, 'config', 'hosts')):
        if not os.path.isfile(pathjoin(srcdir, 'config', 'hosts', diritem, 'clusterconf.json')):
            messages.warning('El directorio', diritem, 'no contiene ningún archivo de configuración')
        clusterconf = readspec(pathjoin(srcdir, 'config', 'hosts', diritem, 'clusterconf.json'))
        clusternames[diritem] = clusterconf.clustername
        clusterkeys[clusterconf.clustername] = diritem
        clusterschedulers[diritem] = clusterconf.scheduler

    for diritem in os.listdir(pathjoin(srcdir, 'config', 'queues')):
        scheduler = readspec(pathjoin(srcdir, 'config', 'queues', diritem, 'queueconf.json')).scheduler
        queueschedulers[diritem] = scheduler
        queuekeys[scheduler] = diritem

    for diritem in os.listdir(pathjoin(srcdir, 'config', 'iospecs')):
        mkdir(pathjoin(cfgdir, 'iospecs', diritem))
        copyfile(pathjoin(srcdir, 'config', 'iospecs', diritem, 'iospec.json'), pathjoin(cfgdir, 'iospecs', diritem, 'iospec.json'))

    if os.path.isfile(pathjoin(cfgdir, 'clusterconf.json')):
        selector.message = '¿Qué clúster desea configurar?'
        selector.options = sorted(sorted(clusternames.values()), key='Nuevo'.__eq__, reverse=True)
        clusterconf = readspec(pathjoin(cfgdir, 'clusterconf.json'))
        if clusterconf.clustername in clusternames.values():
            selector.default = clusterconf.clustername
        selcluster = clusterkeys[selector.single_choice()]
        if clusternames[selcluster] != clusterconf.clustername and readspec(pathjoin(srcdir, 'config', 'hosts', selcluster, 'clusterconf.json')) != readspec(pathjoin(cfgdir, 'clusterconf.json')):
            completer.message = 'Desea sobreescribir la configuración local del sistema?'
            completer.options = {True: ['si', 'yes'], False: ['no']}
            if completer.binary_choice():
                copyfile(pathjoin(srcdir, 'config', 'hosts', selcluster, 'clusterconf.json'), pathjoin(cfgdir, 'clusterconf.json'))
        selector.message = 'Seleccione el gestor de trabajos adecuado'
        selector.options = sorted(queueschedulers.values())
        selector.default = clusterconf.scheduler
        selscheduler = queuekeys[selector.single_choice()]
        copyfile(pathjoin(srcdir, 'config', 'queues', selscheduler, 'queueconf.json'), pathjoin(cfgdir, 'queueconf.json'))
    else:
        selector.message = '¿Qué clúster desea configurar?'
        selector.options = sorted(sorted(clusternames.values()), key='Nuevo'.__eq__, reverse=True)
        selcluster = clusterkeys[selector.single_choice()]
        copyfile(pathjoin(srcdir, 'config', 'hosts', selcluster, 'clusterconf.json'), pathjoin(cfgdir, 'clusterconf.json'))
        selector.message = 'Seleccione el gestor de trabajos adecuado'
        selector.options = sorted(queueschedulers.values())
        selector.default = clusterschedulers[selcluster]
        selscheduler = selector.single_choice()
        selscheduler = queuekeys[selscheduler]
        copyfile(pathjoin(srcdir, 'config', 'queues', selscheduler, 'queueconf.json'), pathjoin(cfgdir, 'queueconf.json'))

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
        moduledir = os.path.dirname(srcdir),
        cfgdir = cfgdir,
    )

    with open(pathjoin(srcdir, 'config', 'submit.sh.tpl'), 'r') as r, open(pathjoin(cfgdir, 'submit.sh'), 'w') as w:
        w.write(Template(r.read()).substitute(installation))

    os.chmod(pathjoin(cfgdir, 'submit.sh'), 0o755)

    for diritem in os.listdir(pathjoin(cfgdir, 'packages')):
        displayname = readspec(pathjoin(cfgdir, 'packages', diritem, 'packageconf.json')).displayname
        packagelist.append(diritem)
        packagekeys[displayname] = diritem
        packagenames[diritem] = displayname

    for diritem in os.listdir(bindir):
        if os.path.islink(pathjoin(bindir, diritem)):
            if os.readlink(pathjoin(bindir, diritem)) == pathjoin(cfgdir, 'submit.sh'):
                enabledpackages.append(diritem)

    if packagelist:
        selector.message = 'Seleccione los programas que desea activar/desactivar'
        selector.options = sorted(packagenames.values())
        selector.default = [packagenames[i] for i in enabledpackages]
        selpackages = [packagekeys[i] for i in selector.multiple_choice()]
    else:
        messages.warning('No hay programas configurados para este host')

    for package in enabledpackages:
        os.remove(pathjoin(bindir, package))

    for package in packagelist:
        if package in selpackages:
            symlink(pathjoin(cfgdir, 'submit.sh'), pathjoin(bindir, package))
