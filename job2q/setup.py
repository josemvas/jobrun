# -*- coding: utf-8 -*-
import re
import sys
from shutil import copyfile
from os import path, listdir, chmod, pathsep
from subprocess import check_output, DEVNULL
from . import dialogs
from . import messages
from .utils import rmdir, makedirs, hardlink, realpath, contractuser, natural
from .readspec import readspec

loader_script = r'''
#!/bin/sh
'export' 'PATH=/bin:/usr/bin'
'export' 'LD_LIBRARY_PATH={libpath}'
'source' '{scheduler}'
'exec' 'env' 'SPECPATH={specdir}' '{python}' "$0" "$@"

from job2q.client import submit, wait, filelist
submit()
while filelist:
    wait()
    submit()
'''

def setup():

    libpath = []
    configured = []
    pylibpath = []
    available = {}
    
    bindir = dialogs.inputpath('Escriba la ruta donde se instalarán los ejecutables')
    etcdir = dialogs.inputpath('Escriba la ruta donde se instalará la configuración')
    
    sourcedir = path.dirname(path.realpath(__file__))
    corespecdir = path.join(sourcedir, 'specdata', 'corespecs')
    hostspecdir = path.join(sourcedir, 'specdata', 'hostspecs')
    specdir = path.join(etcdir, 'jobspecs')
    
    hostname = dialogs.chooseone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(listdir(hostspecdir), key=natural))
    
    if not path.isfile(path.join(hostspecdir, hostname, 'hostspec.json')):
        messages.cfgerror('El archivo de configuración del host', hostname, 'no existe')
    
    scheduler = readspec(path.join(hostspecdir, hostname,'hostspec.json')).scheduler
    if not scheduler.profile:
        messages.cfgerror('No se especificó el archivo de entorno para inicializar el sistema de colas')

    if path.isfile(path.join(specdir, 'hostspec.json')):
        if dialogs.yesno('El sistema ya está configurado, ¿quiere reestablecer la configuración por defecto?'):
            copyfile(path.join(hostspecdir, hostname, 'hostspec.json'), path.join(specdir, 'hostspec.json'))
    else:
        makedirs(specdir)
        copyfile(path.join(hostspecdir, hostname, 'hostspec.json'), path.join(specdir, 'hostspec.json'))
         
    for package in listdir(path.join(hostspecdir, hostname)):
        if path.isdir(path.join(hostspecdir, hostname, package)):
            packagename = readspec(path.join(corespecdir, package, 'corespec.json')).packagename
            if not packagename:
                messages.cfgerror('El archivo', path.join(corespecdir, package, 'corespec.json'), 'no tiene un nombre')
            available[packagename] = package
            if path.isdir(path.join(specdir, package)):
                configured.append(packagename)

    if not available:
        messages.warning('No hay programas configurados para este host')
        return

    selected = dialogs.choosemany('Seleccione los paquetes que desea configurar o reconfigurar', choices=sorted(available.keys(), key=natural), default=configured)

    if set(selected).isdisjoint(configured) or dialogs.yesno('Algunos de los paquetes seleccionados ya están configurados, ¿está seguro que quiere restablecer sus configuraciones por defecto?'):

        for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
            match = re.search(r'^([^\t]+):$', line)
            if match and match.group(1) not in libpath:
                libpath.append(match.group(1))

        for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
            match = re.search(r'=> (.+) \(0x', line)
            if match:
                libdir = path.dirname(match.group(1))
                if libdir not in libpath and libdir not in pylibpath:
                    pylibpath.append(libdir)

        for package in (available[i] for i in selected):
            makedirs(path.join(specdir, package))
            copyfile(path.join(corespecdir, package, 'corespec.json'), path.join(specdir, package, 'corespec.json'))
            copyfile(path.join(hostspecdir, hostname, package, 'pathspec.json'), path.join(specdir, package, 'pathspec.json'))
            hardlink(path.join(specdir, 'hostspec.json'), path.join(specdir, package, 'hostspec.json'))
            with open(path.join(bindir, package), 'w') as fh:
                fh.write(loader_script.lstrip().format(
                    python=sys.executable,
                    scheduler=scheduler.profile,
                    libpath=pathsep.join(pylibpath),
                    specdir=contractuser(path.join(specdir, package))))
            chmod(path.join(bindir, package), 0o755)

#    import json
#    from .readxmlspec import readxmlspec
#    with open(path.join(hostspecdir, 'Miztli','hostspec.json'), 'w') as fh:
#        json.dump(readxmlspec(path.join(hostspecdir, 'Miztli', 'hostspec.xml')), fh, indent=3)
#    with open(path.join(hostspecdir, 'Helio','hostspec.json'), 'w') as fh:
#        json.dump(readxmlspec(path.join(hostspecdir, 'Helio', 'hostspec.xml')), fh, indent=3)
#    for package in listdir(corespecdir):
#        with open(path.join(corespecdir, package, 'corespec.json'), 'w') as fh:
#            json.dump(readxmlspec(path.join(corespecdir, package, 'corespec.xml')), fh, indent=3)
#    for package in listdir(path.join(hostspecdir, 'Helio')):
#        if path.isdir(path.join(hostspecdir, 'Helio', package)):
#            with open(path.join(hostspecdir, 'Helio', package,'pathspec.json'), 'w') as fh:
#                json.dump(readxmlspec(path.join(hostspecdir, 'Helio', package, 'pathspec.xml')), fh, indent=3)
#    for package in listdir(path.join(hostspecdir, 'Miztli')):
#        if path.isdir(path.join(hostspecdir, 'Miztli', package)):
#            with open(path.join(hostspecdir, 'Miztli', package,'pathspec.json'), 'w') as fh:
#                json.dump(readxmlspec(path.join(hostspecdir, 'Miztli', package, 'pathspec.xml')), fh, indent=3)
