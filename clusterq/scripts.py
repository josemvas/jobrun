import os
import sys
import re
from string import Template
from subprocess import check_output, DEVNULL
from clinterface import messages, prompts, _
#from tkdialogs import messages, prompts
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
        completer.set_message(_('Escriba la ruta del directorio de configuración:'))
        cfgdir = AbsPath(completer.directory_path(), parent=os.getcwd())
        completer.set_message(_('Escriba la ruta en la que se instalarán los ejecutables:'))
        bindir = AbsPath(completer.directory_path(), parent=os.getcwd())
        bindir.mkdir()
        cfgdir.mkdir()
        (cfgdir/'pspecs').mkdir()
        (cfgdir/'qspecs').mkdir()
        for spec in (moduledir/'pspecs').listdir():
            if (cfgdir/'pspecs'/spec).isfile():
                if readspec(moduledir/'pspecs'/spec) != readspec(cfgdir/'pspecs'/spec):
                    completer.set_message(_('¿Desea reestablecer la configuración de los programas?'))
                    completer.set_truthy_options(['si', 'yes'])
                    completer.set_falsy_options(['no'])
                    if completer.binary_choice():
                        (moduledir/'pspecs'/spec).copyto(cfgdir/'pspecs')
            else:
                (moduledir/'pspecs'/spec).copyto(cfgdir/'pspecs')
        for spec in (moduledir/'qspecs').listdir():
            if (cfgdir/'qspecs'/spec).isfile():
                if readspec(moduledir/'qspecs'/spec) != readspec(cfgdir/'qspecs'/spec):
                    completer.set_message(_('¿Desea reestablecer la configuración de las colas?'))
                    completer.set_truthy_options(['si', 'yes'])
                    completer.set_falsy_options(['no'])
                    if completer.binary_choice():
                        (moduledir/'qspecs'/spec).copyto(cfgdir/'qspecs')
            else:
                (moduledir/'qspecs'/spec).copyto(cfgdir/'qspecs')
    else:
        bindir = AbsPath('.', parent=os.getcwd())
        cfgdir = AbsPath('clusterq', parent=os.getcwd())

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match and match.group(1) not in systemlibs:
            systemlibs.add(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            library = AbsPath(match.group(1)).parent
            if library not in systemlibs:
                pythonlibs.add(library)

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

    for package in packages:
        if package in selpackages:
            with open(bindir/package, 'w') as file:
                file.write('#!/bin/sh\n')
                if pythonlibs:
                    file.write('LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH\n'.format(os.pathsep.join(pythonlibs)))
                file.write('exec env PYTHONPATH="{}" "{}" -m clusterq.main "{}" "$0" "$@"\n'.format(moduledir, sys.executable, cfgdir))
            (bindir/package).chmod(0o755)
