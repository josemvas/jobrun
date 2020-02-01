# -*- coding: utf-8 -*-
import re
import sys
from shutil import copyfile
from os import path, listdir, chmod, pathsep
from subprocess import check_output, DEVNULL
from . import dialogs
from . import messages
from .utils import rmdir, makedirs, hardlink, realpath, normalpath, natsort, q
from .readspec import readspec

loader_script = r'''
#!/bin/sh
'exec' 'env' \
"LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{pylibpath}" \
"PYTHONPATH={modulepath}" \
"SPECPATH={specpath}" \
'{python}' "$0" "$@"

from job2q import *
if remote:
    decode()
    while files:
        upload()
    transmit()
else:
    decode()
    inspect()
    submit()
    while files:
        wait()
        submit()
'''

def setup(*, relpath=False):

    libpath = []
    pylibpath = []
    hostnames = {}
    hostdirnames = {}
    prognames = {}
    progdirnames = {}
    configured = []
    
    bindir = dialogs.inputpath('Escriba la ruta donde se instalarán los programas', absolute=True)
    etcdir = path.join(bindir, 'job2q')
    makedirs(etcdir)
    
    sourcedir = path.dirname(path.realpath(__file__))
    corespecdir = path.join(sourcedir, 'specdata', 'corespecs')
    hostspecdir = path.join(sourcedir, 'specdata', 'hostspecs')
    specdir = path.join(etcdir, 'jobspecs')
    
    for dirname in listdir(hostspecdir):
        hostnames[dirname] = readspec(path.join(hostspecdir, dirname, 'hostspec.json')).hostname
        hostdirnames[hostnames[dirname]] = dirname

    if not hostnames:
        messages.warning('No hay hosts configurados')
        return

    if path.isfile(path.join(etcdir, 'hostspec.json')):
        defaulthost = readspec(path.join(etcdir, 'hostspec.json')).hostname
    else:
        defaulthost = None

    hostname = hostdirnames[dialogs.chooseone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(hostnames.values(), key=natsort), default=defaulthost)]
    
    if not path.isfile(path.join(hostspecdir, hostname, 'hostspec.json')):
        messages.cfgerror('El archivo de configuración del host', hostname, 'no existe')
    
    if not path.isfile(path.join(etcdir, 'hostspec.json')) or readspec(hostspecdir, hostname, 'hostspec.json') == readspec(etcdir, 'hostspec.json') or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea reestablecerla?'):
        copyfile(path.join(hostspecdir, hostname, 'hostspec.json'), path.join(etcdir, 'hostspec.json'))
         
    for dirname in listdir(path.join(hostspecdir, hostname, 'pathspecs')):
        prognames[dirname] = readspec(path.join(corespecdir, dirname, 'corespec.json')).progname
        progdirnames[prognames[dirname]] = dirname

    if not prognames:
        messages.warning('No hay programas configurados para este host')
        return

    if path.isdir(specdir):
        for dirname in listdir(specdir):
            configured.append(dirname)

    selected = [progdirnames[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=sorted(prognames.values(), key=natsort), default=[prognames[i] for i in configured])]

    for dirname in selected:
        makedirs(path.join(specdir, dirname))
        hardlink(path.join(etcdir, 'hostspec.json'), path.join(specdir, dirname, 'hostspec.json'))
        copyfile(path.join(corespecdir, dirname, 'corespec.json'), path.join(specdir, dirname, 'corespec.json'))
        copypathspec = True
        if dirname not in configured or not path.isfile(path.join(specdir, dirname, 'pathspec.json')) or readspec(hostspecdir, hostname, 'pathspecs', dirname, 'pathspec.json') == readspec(specdir, dirname, 'pathspec.json') or dialogs.yesno('La configuración local del programa', q(prognames[dirname]), 'difiere de la configuración por defecto, ¿desea reestablecerla?', default=False):
            copyfile(path.join(hostspecdir, hostname, 'pathspecs', dirname, 'pathspec.json'), path.join(specdir, dirname, 'pathspec.json'))

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

    for dirname in listdir(specdir):
        if relpath:
            modulepath = path.join('${0%/*}', path.relpath(path.dirname(sourcedir), bindir))
            specpath = path.join('${0%/*}', path.relpath(path.join(specdir, dirname), bindir))
        else:
            modulepath = path.dirname(sourcedir)
            specpath = normalpath(specdir, dirname)
        with open(path.join(bindir, dirname), 'w') as fh:
            fh.write(loader_script.lstrip().format(
                python=sys.executable,
                pylibpath=pathsep.join(pylibpath),
                modulepath=modulepath,
                specpath=specpath,
            ))
        chmod(path.join(bindir, dirname), 0o755)

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
