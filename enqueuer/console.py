# -*- coding: utf-8 -*-
import re
import sys
from subprocess import check_output, DEVNULL
from os import path, listdir, chmod, pathsep
from argparse import ArgumentParser
from os.path import isfile, isdir
from . import dialogs
from . import messages
from .utils import natsort, q
from .specparse import readspec
from .fileutils import AbsPath, NotAbsolutePath, rmdir, makedirs, copyfile, hardlink

loader_script = r'''
#!/bin/sh
'exec' 'env' \
"LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{pyldpath}" \
"PYTHONPATH={modulepath}" \
"SPECPATH={specpath}" \
'{python}' "$0" "$@"

from enqueuer.jobinit import dry_run, remote_run, files
from enqueuer.jobexec import wait, setup, transfer, dryrun, remoterun, localrun

if dry_run:
    while files:
        dryrun()
elif remote_run:
    while files:
        transfer()
    remoterun()
else:
    setup()
    localrun()
    while files:
        wait()
        localrun()
'''

def main():

    commands = {
        'firstsetup' : firstsetup,
    }
    
    parser = ArgumentParser()
    parser.add_argument('cmd', choices=commands.keys())
    commands[parser.parse_args().cmd]()

def firstsetup(relpath=False):

    libpath = []
    pyldpath = []
    clusternames = {}
    hostdirnames = {}
    prognames = {}
    progdirnames = {}
    configured = []
    
    bindir = dialogs.inputpath('Escriba la ruta donde se instalarán los programas', check=isdir)
    datadir = path.join(bindir, 'enqueuer.d')
    makedirs(datadir)
    
    sourcedir = AbsPath(__file__).parent()
    corespecdir = path.join(sourcedir, 'specdata', 'corespecs')
    hostspecdir = path.join(sourcedir, 'specdata', 'hostspecs')
    specdir = path.join(datadir, 'jobspecs')
    
    for dirname in listdir(hostspecdir):
        if not path.isfile(path.join(hostspecdir, dirname, 'hostspec.json')):
            messages.warning('El directorio', dirname, 'no contiene ningún archivo de configuración')
        clusternames[dirname] = readspec(path.join(hostspecdir, dirname, 'hostspec.json')).clustername
        hostdirnames[clusternames[dirname]] = dirname

    if not clusternames:
        messages.warning('No hay hosts configurados')
        return

    if path.isfile(path.join(datadir, 'hostspec.json')):
        defaulthost = readspec(path.join(datadir, 'hostspec.json')).clustername
    else:
        defaulthost = None

    selhostdir = hostdirnames[dialogs.chooseone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(clusternames.values(), key=natsort), default=defaulthost)]
    
    if not path.isfile(path.join(datadir, 'hostspec.json')) or readspec(hostspecdir, selhostdir, 'hostspec.json') == readspec(datadir, 'hostspec.json') or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea reestablecerla?'):
        copyfile(path.join(hostspecdir, selhostdir, 'hostspec.json'), path.join(datadir, 'hostspec.json'))
         
    for dirname in listdir(path.join(hostspecdir, selhostdir, 'pathspecs')):
        prognames[dirname] = readspec(path.join(corespecdir, dirname, 'corespec.json')).progname
        progdirnames[prognames[dirname]] = dirname

    if not prognames:
        messages.warning('No hay programas configurados para este host')
        return

    if path.isdir(specdir):
        for dirname in listdir(specdir):
            configured.append(dirname)
    elif path.exists(specdir):
        messages.cfgerror('No se puede crear el directorio de configuración', specdir, 'porque ya existe un archivo con ese nombre')
    else:
        makedirs(specdir)

    selprogdirs = [progdirnames[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=sorted(prognames.values(), key=natsort), default=[prognames[i] for i in configured])]

    for progdir in selprogdirs:
        makedirs(path.join(specdir, progdir))
        hardlink(path.join(datadir, 'hostspec.json'), path.join(specdir, progdir, 'hostspec.json'))
        copyfile(path.join(corespecdir, progdir, 'corespec.json'), path.join(specdir, progdir, 'corespec.json'))
        copypathspec = True
        if progdir not in configured or not path.isfile(path.join(specdir, progdir, 'pathspec.json')) or readspec(hostspecdir, selhostdir, 'pathspecs', progdir, 'pathspec.json') == readspec(specdir, progdir, 'pathspec.json') or dialogs.yesno('La configuración local del programa', q(prognames[progdir]), 'difiere de la configuración por defecto, ¿desea reestablecerla?', default=False):
            copyfile(path.join(hostspecdir, selhostdir, 'pathspecs', progdir, 'pathspec.json'), path.join(specdir, progdir, 'pathspec.json'))

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.search(r'^([^\t]+):$', line)
        if match and match.group(1) not in libpath:
            libpath.append(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.search(r'=> (.+) \(0x', line)
        if match:
            libdir = path.dirname(match.group(1))
            if libdir not in libpath and libdir not in pyldpath:
                pyldpath.append(libdir)

    for dirname in listdir(specdir):
        if relpath:
            modulepath = path.join('${0%/*}', path.relpath(path.dirname(sourcedir), bindir))
            specpath = path.join('${0%/*}', path.relpath(path.join(specdir, dirname), bindir))
        else:
            modulepath = path.dirname(sourcedir)
            specpath = AbsPath(specdir, dirname)
        with open(path.join(bindir, dirname), 'w') as fh:
            fh.write(loader_script.lstrip().format(
                python=sys.executable,
                pyldpath=pathsep.join(pyldpath),
                modulepath=modulepath,
                specpath=specpath,
            ))
        chmod(path.join(bindir, dirname), 0o755)

