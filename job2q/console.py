# -*- coding: utf-8 -*-
import re
import sys
from shutil import copyfile
from os import path, listdir, chmod, pathsep
from subprocess import check_output, DEVNULL
from . import dialogs
from . import messages
from .utils import rmdir, makedirs, hardlink, realpath, contractuser, natsort, q
from .readspec import readspec

loader_script = r'''
#!/bin/sh
'exec' 'env' \
"LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{libpath}" \
'SPECPATH={specdir}' \
'{python}' "$0" "$@"

from job2q import *
configure()
if remote:
    while files:
        upload()
    transmit()
else:
    submit()
    while files:
        wait()
        submit()
'''

def setup():

    libpath = []
    configured = []
    pylibpath = []
    pkgnames = {}
    pkgdirs = {}
    
    bindir = dialogs.inputpath('Escriba la ruta donde se instalarán los ejecutables')
    etcdir = dialogs.inputpath('Escriba la ruta donde se escribirán los archivos de configuración')
    
    sourcedir = path.dirname(path.realpath(__file__))
    corespecdir = path.join(sourcedir, 'specdata', 'corespecs')
    hostspecdir = path.join(sourcedir, 'specdata', 'hostspecs')
    specdir = path.join(etcdir, 'jobspecs')
    
    hostname = dialogs.chooseone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(listdir(hostspecdir), key=natsort))
    
    if not path.isfile(path.join(hostspecdir, hostname, 'hostspec.json')):
        messages.cfgerror('El archivo de configuración del host', hostname, 'no existe')
    
    if not path.isfile(path.join(etcdir, 'hostspec.json')) or readspec(hostspecdir, hostname, 'hostspec.json') == readspec(etcdir, 'hostspec.json') or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea reestablecerla?'):
        copyfile(path.join(hostspecdir, hostname, 'hostspec.json'), path.join(etcdir, 'hostspec.json'))
         
    for pkgdir in listdir(path.join(hostspecdir, hostname, 'pathspecs')):
        pkgname = readspec(path.join(corespecdir, pkgdir, 'corespec.json')).packagename
        if not pkgname:
            messages.cfgerror('El archivo', path.join(corespecdir, pkgdir, 'corespec.json'), 'no especifica el nombre del programa')
        pkgnames[pkgdir] = pkgname
        pkgdirs[pkgname] = pkgdir

    if not pkgnames:
        messages.warning('No hay programas configurados para este host')
        return

    if path.isdir(specdir):
        for pkgdir in listdir(specdir):
            configured.append(pkgdir)

    selected = [pkgdirs[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=sorted(pkgnames.values(), key=natsort), default=[pkgnames[i] for i in configured])]

    for pkgdir in selected:
        makedirs(path.join(specdir, pkgdir))
        hardlink(path.join(etcdir, 'hostspec.json'), path.join(specdir, pkgdir, 'hostspec.json'))
        copyfile(path.join(corespecdir, pkgdir, 'corespec.json'), path.join(specdir, pkgdir, 'corespec.json'))
        copypathspec = True
        if pkgdir not in configured or not path.isfile(path.join(specdir, pkgdir, 'pathspec.json')) or readspec(hostspecdir, hostname, 'pathspecs', pkgdir, 'pathspec.json') == readspec(specdir, pkgdir, 'pathspec.json') or dialogs.yesno('La configuración local del programa', q(pkgnames[pkgdir]), 'difiere de la configuración por defecto, ¿desea reestablecerla?', default=False):
            copyfile(path.join(hostspecdir, hostname, 'pathspecs', pkgdir, 'pathspec.json'), path.join(specdir, pkgdir, 'pathspec.json'))

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

    for package in listdir(specdir):
        with open(path.join(bindir, package), 'w') as fh:
            fh.write(loader_script.lstrip().format(
                python=sys.executable,
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
