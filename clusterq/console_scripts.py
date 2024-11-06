import os
import sys
import re
from string import Template
from argparse import ArgumentParser
#from tkdialogs import messages, prompts
from clinterface import messages, prompts, _
from subprocess import check_output, DEVNULL
from .utils import readspec, shq
from .fileutils import AbsPath

selector = prompts.Selector()
completer = prompts.Completer()
completer.set_truthy_options(['si', 'yes'])
completer.set_falsy_options(['no'])

def clusterq():

    parser = ArgumentParser(description='Herramienta de configuración de ClusterQ.')
    parser.add_argument('command', metavar='command')
    args = parser.parse_args()

    if args.command == 'setup':
        clusterq_setup()
    else:
        messages.error(_('$command no es un comando válido', command=args.command))


def clusterq_setup():

    packages = []
    enabledpackages = []
    packagenames = {}
    systemlibs = set()
    pythonlibs = set()

    packagedir = AbsPath(__file__).parent()

    completer.set_message(_('Escriba la ruta del directorio de configuración:'))
    cfgdir = AbsPath(completer.directory_path(), parent=os.getcwd())
    completer.set_message(_('Escriba la ruta en la que se instalarán los ejecutables:'))
    bindir = AbsPath(completer.directory_path(), parent=os.getcwd())
    bindir.mkdir()
    cfgdir.mkdir()
    (cfgdir/'progspecs').mkdir()
    (cfgdir/'queuespecs').mkdir()
    for specfile in (packagedir/'progspecs').listdir():
        if (cfgdir/'progspecs'/specfile).isfile():
            if readspec(packagedir/'progspecs'/specfile) != readspec(cfgdir/'progspecs'/specfile):
                completer.set_message(_('¿Desea sobrescribir la configuración local del programa $progname?', progname=specfile))
                if completer.binary_choice():
                    (packagedir/'progspecs'/specfile).copyto(cfgdir/'progspecs')
        else:
            (packagedir/'progspecs'/specfile).copyto(cfgdir/'progspecs')
    for specfile in (packagedir/'queuespecs').listdir():
        if (cfgdir/'queuespecs'/specfile).isfile():
            if readspec(packagedir/'queuespecs'/specfile) != readspec(cfgdir/'queuespecs'/specfile):
                completer.set_message(_('¿Desea sobrescribir la configuración local del gestor de trabajos $queuename?', queuename=specfile))
                if completer.binary_choice():
                    (packagedir/'queuespecs'/specfile).copyto(cfgdir/'queuespecs')
        else:
            (packagedir/'queuespecs'/specfile).copyto(cfgdir/'queuespecs')

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match:
            systemlibs.add(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            lib = AbsPath(match.group(1)).parent()
            if lib not in systemlibs:
                pythonlibs.add(lib)

    if (cfgdir/'profiles').isdir():
        for spec in (cfgdir/'profiles').listdir():
            specdict = readspec(cfgdir/'profiles'/spec)
            if 'displayname' in specdict:
                name = os.path.splitext(spec)[0]
                packages.append(name)
                packagenames[name] = specdict['displayname']

    if bindir.isdir():
        for runfile in bindir.listdir():
            if (bindir/runfile).isfile():
                if runfile in packages:
                    enabledpackages.append(runfile)
                    (bindir/runfile).remove()

    if packages:
        selector.set_message(_('Seleccione los programas que desea activar/desactivar:'))
        selector.set_options(packagenames)
        selector.set_multiple_defaults(enabledpackages)
        selpackages = selector.multiple_choices()
    else:
        messages.warning(_('No hay ningún programa configurado todavía'))

    command = ['exec', 'env']
    if pythonlibs:
        command.append(f"LD_LIBRARY_PATH={':'.join(shq(lib) for lib in pythonlibs)}:$LD_LIBRARY_PATH")
    command.extend([f'PYTHONPATH={shq(packagedir)}', f'CLUSTERQCFG={shq(cfgdir)}', shq(sys.executable), '-m', 'clusterq.main', '"$0"', '"$@"'])

    for package in packages:
        if package in selpackages:
            with open(bindir/package, 'w') as file:
                file.write('#!/bin/sh\n')
                file.write(' '.join(command) + '\n')
            (bindir/package).chmod(0o755)
