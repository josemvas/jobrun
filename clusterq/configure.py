import os
import sys
import re
from string import Template
from subprocess import check_output, DEVNULL
from clinterface import messages, prompts
from .readspec import readspec
from .fileutils import AbsPath, pathjoin, mkdir, copyfile, symlink

selector = prompts.Selector()
completer = prompts.Completer()

def manage_packages():

    pythonlibs = []
    systemlibs = []
    packagelist = []
    packagenames = {}
    enabledpackages = []

    moduledir = AbsPath(__file__).parent

    completer.set_message('Escriba la ruta de los archivos de configuración')
    confdir = AbsPath(completer.directory_path(), cwd=os.getcwd())

    completer.set_message('Escriba la ruta donde se instalarán los ejecutables')
    bindir = AbsPath(completer.directory_path(), cwd=os.getcwd())

    mainscript = 'clusterq-submit'
    mainscriptpath = pathjoin(bindir, mainscript)

    mkdir(bindir)
    mkdir(confdir)
    mkdir(pathjoin(confdir, 'packages'))

    if not os.path.isfile(pathjoin(confdir, 'config.json')):
        messages.warning('Aún no se ha configurado el clúster')

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match and match.group(1) not in systemlibs:
            systemlibs.append(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            library = os.path.dirname(match.group(1))
            if library not in systemlibs:
                pythonlibs.append(library)

    with open(mainscriptpath, 'w') as file:
        file.write('#!/bin/sh -a\n')
        if pythonlibs:
            file.write('LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH\n'.format(os.pathsep.join(pythonlibs)))
        file.write('exec env PYTHONPATH="{}" "{}" -m clusterq.main "{}" "$0" "$@"\n'.format(moduledir, sys.executable, confdir))

    os.chmod(mainscriptpath, 0o755)

    for diritem in os.listdir(pathjoin(confdir, 'packages')):
        displayname = readspec(pathjoin(confdir, 'packages', diritem, 'config.json')).displayname
        packagelist.append(diritem)
        packagenames[diritem] = displayname

    for diritem in os.listdir(bindir):
        if os.path.islink(pathjoin(bindir, diritem)):
            if os.readlink(pathjoin(bindir, diritem)) == mainscript:
                enabledpackages.append(diritem)

    if packagelist:
        selector.set_message('Seleccione los programas que desea activar/desactivar')
        selector.set_options(packagenames)
        selector.set_multiple_defaults(enabledpackages)
        selpackages = selector.multiple_choices()
    else:
        messages.warning('No hay ningún programa configurado todavía')

    for package in enabledpackages:
        os.remove(pathjoin(bindir, package))

    for package in packagelist:
        if package in selpackages:
            symlink(mainscript, pathjoin(bindir, package))


def configure_cluster():

    clusterkeys = {}
    clusternames = {}
    defaultschedulers = {}
    schedulerkeys = {}
    schedulernames = {}

    for diritem in os.listdir(pathjoin(moduledir, 'templates', 'hosts')):
        if not os.path.isfile(pathjoin(moduledir, 'templates', 'hosts', diritem, 'cluster', 'config.json')):
            messages.warning('El directorio', diritem, 'no contiene ningún archivo de configuración')
        clusterconf = readspec(pathjoin(moduledir, 'templates', 'hosts', diritem, 'cluster', 'config.json'))
        clusternames[diritem] = clusterconf.clustername
        clusterkeys[clusterconf.clustername] = diritem
        defaultschedulers[diritem] = clusterconf.scheduler

    for diritem in os.listdir(pathjoin(moduledir, 'schedulers')):
        scheduler = readspec(pathjoin(moduledir, 'schedulers', diritem, 'config.json')).scheduler
        schedulernames[diritem] = scheduler
        schedulerkeys[scheduler] = diritem

    if os.path.isfile(pathjoin(confdir, 'cluster', 'config.json')):
        selector.set_message('¿Qué clúster desea configurar?')
        selector.set_options(clusternames)
        clusterconf = readspec(pathjoin(confdir, 'cluster', 'config.json'))
        if clusterconf.clustername in clusternames.values():
            selector.set_single_default(clusterkeys[clusterconf.clustername])
        selcluster = selector.single_choice()
        if selcluster != clusterkeys[clusterconf.clustername]:
            if readspec(pathjoin(moduledir, 'templates', 'hosts', selcluster, 'cluster', 'config.json')) != readspec(pathjoin(confdir, 'cluster', 'config.json')):
                completer.set_message('Desea sobreescribir la configuración local del sistema?')
                completer.set_truthy_options(['si', 'yes'])
                completer.set_falsy_options(['no'])
                if completer.binary_choice():
                    copyfile(pathjoin(moduledir, 'templates', 'hosts', selcluster, 'cluster', 'config.json'), pathjoin(confdir, 'cluster', 'config.json'))
        selector.set_message('Seleccione el gestor de trabajos adecuado')
        selector.set_options(schedulernames)
        selector.set_single_default(schedulerkeys[clusterconf.scheduler])
        selscheduler = selector.single_choice()
        copyfile(pathjoin(moduledir, 'schedulers', selscheduler, 'config.json'), pathjoin(confdir, 'config.json'))
    else:
        selector.set_message('¿Qué clúster desea configurar?')
        selector.set_options(clusternames)
        selcluster = selector.single_choice()
        copyfile(pathjoin(moduledir, 'templates', 'hosts', selcluster, 'cluster', 'config.json'), pathjoin(confdir, 'cluster', 'config.json'))
        selector.set_message('Seleccione el gestor de trabajos adecuado')
        selector.set_options(schedulernames)
        selector.set_single_default(selcluster)
        selscheduler = selector.single_choice()
        copyfile(pathjoin(moduledir, 'schedulers', selscheduler, 'config.json'), pathjoin(confdir, 'config.json'))
