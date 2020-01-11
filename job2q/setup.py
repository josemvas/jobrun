# -*- coding: utf-8 -*-
import sys
from re import search
from subprocess import check_output
from os import path, listdir, chmod, pathsep
from shutil import copyfile
import json5 as json

from . import dialogs
from . import messages
from .utils import rmdir, makedirs, hardlink, realpath, contractuser
from .readspec import readspec

loader_script = r'''
#!/bin/sh
'exec' 'env' \
"LD_LIBRARY_PATH={pylibs}:$LD_LIBRARY_PATH" \
'{python}' "$0" "$@" '--specdir={specdir}'

from job2q import main
main.submit()
while main.filelist:
    main.wait()
    main.submit()
'''

def setup():

    bindir = dialogs.inputpath('Escriba la ruta donde se instalarán los ejecutables')
    etcdir = dialogs.inputpath('Escriba la ruta donde se instalará la configuración')
    
    sourcedir = path.dirname(path.realpath(__file__))
    corespecdir = path.join(sourcedir, 'specdata', 'corespecs')
    hostspecdir = path.join(sourcedir, 'specdata', 'hostspecs')
    specdir = path.join(etcdir, 'specs')
    
    hostname = dialogs.optone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(listdir(hostspecdir), key=str.casefold))
    
    if not path.isfile(path.join(hostspecdir, hostname, 'hostspec.xml')):
        messages.cfgerr('El archivo de configuración del host', hostname, 'no existe')
    
    available = {}
    configured = []
    libraries = set()
    
    if path.isfile(path.join(specdir, 'hostspec.xml')):
        if dialogs.yesno('El sistema ya está configurado, ¿quiere reestablecer la configuración por defecto?'):
            copyfile(path.join(hostspecdir, hostname, 'hostspec.xml'), path.join(specdir, 'hostspec.xml'))
    else:
        makedirs(specdir)
        copyfile(path.join(hostspecdir, hostname, 'hostspec.xml'), path.join(specdir, 'hostspec.xml'))
         
    for package in listdir(path.join(hostspecdir, hostname)):
        if path.isdir(path.join(hostspecdir, hostname, package)):
            packagename = readspec(path.join(corespecdir, package, 'corespec.xml'), 'packagename')
            if packagename is None:
                messages.cfgerr('El archivo', path.join(corespecdir, package, 'corespec.xml'), 'no tiene un título')
            available[packagename] = package
            if path.isdir(path.join(specdir, package)):
                configured.append(packagename)

    if not available:
        messages.warning('No hay programas configurados para este host')
        return

    selected = dialogs.optany('Seleccione los paquetes que desea configurar o reconfigurar', choices=sorted(available.keys(), key=str.casefold), default=configured)

    if set(selected).isdisjoint(configured) or dialogs.yesno('Algunos de los paquetes seleccionados ya están configurados, ¿está seguro que quiere restablecer sus configuraciones por defecto?'):

        for line in check_output(('ldd', sys.executable)).decode('utf-8').splitlines():
            matching = search(r'=> (.+) \(0x', line)
            if matching:
                libraries.add(path.dirname(matching.group(1)))

        for package in (available[i] for i in selected):
            makedirs(path.join(specdir, package))
            copyfile(path.join(corespecdir, package, 'corespec.xml'), path.join(specdir, package, 'corespec.xml'))
            copyfile(path.join(hostspecdir, hostname, package, 'pathspec.xml'), path.join(specdir, package, 'pathspec.xml'))
            hardlink(path.join(specdir, 'hostspec.xml'), path.join(specdir, package, 'hostspec.xml'))
            with open(path.join(bindir, package), 'w') as fh:
                fh.write(loader_script.lstrip().format(
                    python=sys.executable,
                    pylibs=pathsep.join(libraries),
                    specdir=contractuser(path.join(specdir, package))))
            chmod(path.join(bindir, package), 0o755)

#    with open(path.join(hostspecdir, 'Miztli','hostspec.json'), 'w') as fh:
#        json.dump(readspec(path.join(hostspecdir, 'Miztli', 'hostspec.xml')), fh, indent=4)
#    with open(path.join(hostspecdir, 'Helio','hostspec.json'), 'w') as fh:
#        json.dump(readspec(path.join(hostspecdir, 'Helio', 'hostspec.xml')), fh, indent=4)
#    for package in listdir(corespecdir):
#        with open(path.join(corespecdir, package, 'corespec.json'), 'w') as fh:
#            json.dump(readspec(path.join(corespecdir, package, 'corespec.xml')), fh, indent=4)
#    for package in listdir(path.join(hostspecdir, 'Helio')):
#        if path.isdir(path.join(hostspecdir, 'Helio', package)):
#            with open(path.join(hostspecdir, 'Helio', package,'pathspec.json'), 'w') as fh:
#                json.dump(readspec(path.join(hostspecdir, 'Helio', package, 'pathspec.xml')), fh, indent=4)
#    for package in listdir(path.join(hostspecdir, 'Miztli')):
#        if path.isdir(path.join(hostspecdir, 'Miztli', package)):
#            with open(path.join(hostspecdir, 'Miztli', package,'pathspec.json'), 'w') as fh:
#                json.dump(readspec(path.join(hostspecdir, 'Miztli', package, 'pathspec.xml')), fh, indent=4)


