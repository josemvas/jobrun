import os
import sys
import re
from string import Template
from subprocess import check_output, DEVNULL
from clinterface import messages, prompts
from .readspec import readspec
from .fileutils import AbsPath

selector = prompts.Selector()
completer = prompts.Completer()

def setup(install=True):

    pythonlibs = set()
    systemlibs = set()
    packages = []
    enabledpackages = []
    packagenames = {}

    moduledir = AbsPath(__file__).parent

    if install:

        completer.set_message('Escriba la ruta del directorio de configuración:')
        cfgdir = AbsPath(completer.directory_path(), cwd=os.getcwd())
        completer.set_message('Escriba la ruta en la que se instalarán los ejecutables:')
        bindir = AbsPath(completer.directory_path(), cwd=os.getcwd())

        bindir.mkdir()
        cfgdir.mkdir()
        (cfgdir/'qspecs').mkdir()
        (cfgdir/'pspecs').mkdir()

        for specdir in (moduledir/'qspecs').listdir():
            (cfgdir/'qspecs'/specdir).mkdir()
            (moduledir/'qspecs'/specdir/'config.json').copyto(cfgdir/'qspecs'/specdir)

        for specdir in (moduledir/'pspecs').listdir():
            (cfgdir/'pspecs'/specdir).mkdir()
            (moduledir/'pspecs'/specdir/'config.json').copyto(cfgdir/'pspecs'/specdir)

    else:

        bindir = AbsPath('.', cwd=os.getcwd())
        cfgdir = AbsPath('clusterq', cwd=os.getcwd())


    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match and match.group(1) not in systemlibs:
            systemlibs.add(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            library = os.path.dirname(match.group(1))
            if library not in systemlibs:
                pythonlibs.add(library)

    if (cfgdir/'environments').isdir():
        for specdir in (cfgdir/'environments').listdir():
            specs = readspec(cfgdir/'environments'/specdir/'config.json')
            if 'displayname' in specs:
                packages.append(specdir)
                packagenames[specdir] = specs.displayname

    if bindir.isdir():
        for runfile in bindir.listdir():
            if (bindir/runfile).isfile():
                if runfile in packages:
                    enabledpackages.append(runfile)
                    (bindir/runfile).remove()

    if packages:
        selector.set_message('Seleccione los programas que desea activar/desactivar:')
        selector.set_options(packagenames)
        selector.set_multiple_defaults(enabledpackages)
        selpackages = selector.multiple_choices()
    else:
        messages.warning('No hay ningún programa configurado todavía')

    for package in packages:
        if package in selpackages:
            with open(bindir/package, 'w') as file:
                file.write('#!/bin/sh\n')
                if pythonlibs:
                    file.write('LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH\n'.format(os.pathsep.join(pythonlibs)))
                file.write('exec env PYTHONPATH="{}" "{}" -m clusterq.main "{}" "$0" "$@"\n'.format(moduledir, sys.executable, cfgdir))
            (bindir/package).chmod(0o755)

#def configure_cluster():
#
#    clusterkeys = {}
#    clusternames = {}
#    defaultschedulers = {}
#    schedulerkeys = {}
#    schedulernames = {}
#
#    for diritem in os.listdir(pathjoin(moduledir, 'templates', 'hosts')):
#        if not os.path.isfile(pathjoin(moduledir, 'templates', 'hosts', diritem, 'cluster', 'config.json')):
#            messages.warning('El directorio', diritem, 'no contiene ningún archivo de configuración')
#        clusterconf = readspec(pathjoin(moduledir, 'templates', 'hosts', diritem, 'cluster', 'config.json'))
#        clusternames[diritem] = clusterconf.clustername
#        clusterkeys[clusterconf.clustername] = diritem
#        defaultschedulers[diritem] = clusterconf.scheduler
#
#    for diritem in os.listdir(pathjoin(moduledir, 'qspecs')):
#        scheduler = readspec(pathjoin(moduledir, 'qspecs', diritem, 'config.json')).scheduler
#        schedulernames[diritem] = scheduler
#        schedulerkeys[scheduler] = diritem
#
#    if os.path.isfile(pathjoin(cfgdir, 'cluster', 'config.json')):
#        selector.set_message('¿Qué clúster desea configurar?')
#        selector.set_options(clusternames)
#        clusterconf = readspec(pathjoin(cfgdir, 'cluster', 'config.json'))
#        if clusterconf.clustername in clusternames.values():
#            selector.set_single_default(clusterkeys[clusterconf.clustername])
#        selcluster = selector.single_choice()
#        if selcluster != clusterkeys[clusterconf.clustername]:
#            if readspec(pathjoin(moduledir, 'templates', 'hosts', selcluster, 'cluster', 'config.json')) != readspec(pathjoin(cfgdir, 'cluster', 'config.json')):
#                completer.set_message('Desea sobreescribir la configuración local del sistema?')
#                completer.set_truthy_options(['si', 'yes'])
#                completer.set_falsy_options(['no'])
#                if completer.binary_choice():
#                    copyfile(pathjoin(moduledir, 'templates', 'hosts', selcluster, 'cluster', 'config.json'), pathjoin(cfgdir, 'cluster', 'config.json'))
#        selector.set_message('Seleccione el gestor de trabajos adecuado')
#        selector.set_options(schedulernames)
#        selector.set_single_default(schedulerkeys[clusterconf.scheduler])
#        selscheduler = selector.single_choice()
#        copyfile(pathjoin(moduledir, 'qspecs', selscheduler, 'config.json'), pathjoin(cfgdir, 'config.json'))
#    else:
#        selector.set_message('¿Qué clúster desea configurar?')
#        selector.set_options(clusternames)
#        selcluster = selector.single_choice()
#        copyfile(pathjoin(moduledir, 'templates', 'hosts', selcluster, 'cluster', 'config.json'), pathjoin(cfgdir, 'cluster', 'config.json'))
#        selector.set_message('Seleccione el gestor de trabajos adecuado')
#        selector.set_options(schedulernames)
#        selector.set_single_default(selcluster)
#        selscheduler = selector.single_choice()
#        copyfile(pathjoin(moduledir, 'qspecs', selscheduler, 'config.json'), pathjoin(cfgdir, 'config.json'))
