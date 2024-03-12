import os
import sys
import re
from string import Template
from argparse import ArgumentParser
#from tkdialogs import messages, prompts
from clinterface import messages, prompts, _
from subprocess import check_output, DEVNULL
from .utils import shq
from .readspec import readspec
from .fileutils import AbsPath

selector = prompts.Selector()
completer = prompts.Completer()


def clusterq():

    parser = ArgumentParser(description='Herramienta de configuración de ClusterQ.')
    parser.add_argument('command', metavar='command')
    parser.add_argument('--in-place', action='store_true')
    args = parser.parse_args()

    if args.command == 'setup':
        clusterq_setup(args.in_place)
    else:
        messages.error(_('$command no es un comando válido', command=args.command))


def clusterq_setup(in_place):

    packages = []
    enabledpackages = []
    packagenames = {}
    systemlibs = set()
    pythonlibs = set()

    mdldir = AbsPath(__file__).parent

    if in_place:
        bindir = AbsPath('.', parent=os.getcwd())
        cfgdir = AbsPath('clusterq', parent=os.getcwd())
    else:
        completer.set_message(_('Escriba la ruta del directorio de configuración:'))
        cfgdir = AbsPath(completer.directory_path(), parent=os.getcwd())
        completer.set_message(_('Escriba la ruta en la que se instalarán los ejecutables:'))
        bindir = AbsPath(completer.directory_path(), parent=os.getcwd())
        bindir.mkdir()
        cfgdir.mkdir()
        (cfgdir/'pspecs').mkdir()
        (cfgdir/'qspecs').mkdir()
        for pspec in (mdldir/'pspecs').listdir():
            if (cfgdir/'pspecs'/pspec).isfile():
                if readspec(mdldir/'pspecs'/pspec) != readspec(cfgdir/'pspecs'/pspec):
                    completer.set_message(_('¿Desea restaurar la configuración por defecto de $progname?', progname=pspec))
                    completer.set_truthy_options(['si', 'yes'])
                    completer.set_falsy_options(['no'])
                    if completer.binary_choice():
                        (mdldir/'pspecs'/pspec).copyto(cfgdir/'pspecs')
            else:
                (mdldir/'pspecs'/pspec).copyto(cfgdir/'pspecs')
        for qspec in (mdldir/'qspecs').listdir():
            if (cfgdir/'qspecs'/qspec).isfile():
                if readspec(mdldir/'qspecs'/qspec) != readspec(cfgdir/'qspecs'/qspec):
                    completer.set_message(_('¿Desea restaurar la configuración por defecto de $quename?', quename=qspec))
                    completer.set_truthy_options(['si', 'yes'])
                    completer.set_falsy_options(['no'])
                    if completer.binary_choice():
                        (mdldir/'qspecs'/qspec).copyto(cfgdir/'qspecs')
            else:
                (mdldir/'qspecs'/qspec).copyto(cfgdir/'qspecs')

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match:
            systemlibs.add(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            lib = AbsPath(match.group(1)).parent
            if lib not in systemlibs:
                pythonlibs.add(lib)

    if (cfgdir/'environ').isdir():
        for spec in (cfgdir/'environ').listdir():
            specdict = readspec(cfgdir/'environ'/spec)
            if 'displayname' in specdict:
                name = os.path.splitext(spec)[0]
                packages.append(name)
                packagenames[name] = specdict.displayname

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
    command.extend([f'PYTHONPATH={shq(mdldir)}', f'CLUSTERQCFG={shq(cfgdir)}', shq(sys.executable), '-m', 'clusterq.main', '"$0"', '"$@"'])

    for package in packages:
        if package in selpackages:
            with open(bindir/package, 'w') as file:
                file.write('#!/bin/sh\n')
                file.write(' '.join(command) + '\n')
            (bindir/package).chmod(0o755)
