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

from enqueuer.jobinit import drytest, remotehost, files
from enqueuer.jobexec import wait, setup, connect, upload, dryrun, localrun, remoterun

if drytest:
    while files:
        dryrun()
elif remotehost:
    connect()
    while files:
        upload()
    remoterun()
else:
    setup()
    localrun()
    while files:
        wait()
        localrun()
'''

def setup(relpath=False):

    libpath = []
    pyldpath = []
    configured = []
    clusternames = {}
    hostdirnames = {}
    progdirnames = {}
    schedulers = {}
    prognames = {}
    defaults = {}
    
    bindir = dialogs.inputpath('Escriba la ruta donde se instalarán los programas', check=isdir)
    cfgdir = path.join(bindir, 'enqueuer')
    makedirs(cfgdir)
    
    sourcedir = AbsPath(__file__).parent()
    corespecdir = path.join(sourcedir, 'specdata', 'corespecs')
    hostspecdir = path.join(sourcedir, 'specdata', 'hostspecs')
    queuespecdir = path.join(sourcedir, 'specdata', 'queuespecs')
    specdir = path.join(cfgdir, 'jobspecs')
    
    for dirname in listdir(hostspecdir):
        if not path.isfile(path.join(hostspecdir, dirname, 'hostspec.json')):
            messages.warning('El directorio', dirname, 'no contiene ningún archivo de configuración')
        hostspec = readspec(path.join(hostspecdir, dirname, 'hostspec.json'))
        clusternames[dirname] = hostspec.clustername
        hostdirnames[hostspec.clustername] = dirname
        if hostspec.scheduler:
            if hostspec.scheduler in listdir(queuespecdir):
                schedulers[dirname] = hostspec.scheduler
            else:
                messages.error('El gestor de trabajos', hostspec.scheduler, 'no está soportado')

    if not clusternames:
        messages.warning('No hay hosts configurados')
        raise SystemExit()

    if path.isfile(path.join(cfgdir, 'hostspec.json')):
        clustername = readspec(path.join(cfgdir, 'hostspec.json')).clustername
        if clustername in clusternames.values():
            defaults['cluster'] = clustername

    selhostdir = hostdirnames[dialogs.chooseone('Seleccione la opción con la arquitectura más adecuada', choices=natsort(clusternames.values()), default=defaults.get('cluster', 'Generic'))]
    
    if not path.isfile(path.join(cfgdir, 'hostspec.json')) or readspec(hostspecdir, selhostdir, 'hostspec.json') == readspec(cfgdir, 'hostspec.json') or dialogs.yesno('La configuración local del sistema difiere de la configuración por defecto, ¿desea sobreescribirla?'):
        copyfile(path.join(hostspecdir, selhostdir, 'hostspec.json'), path.join(cfgdir, 'hostspec.json'))

    if selhostdir in schedulers:
        copyfile(path.join(queuespecdir, schedulers[selhostdir], 'queuespec.json'), path.join(cfgdir, 'queuespec.json'))
    else:
        messages.warning('Especifique el gestor de trabajos en el archivo hostspec.json y ejecute otra vez este comando')
        return
         
    for dirname in listdir(path.join(hostspecdir, selhostdir, 'pathspecs')):
        prognames[dirname] = readspec(path.join(corespecdir, dirname, 'corespec.json')).progname
        progdirnames[prognames[dirname]] = dirname

    if not prognames:
        messages.warning('No hay programas configurados para este host')
        raise SystemExit()

    if path.isdir(specdir):
        for dirname in listdir(specdir):
            configured.append(dirname)
    elif path.exists(specdir):
        messages.cfgerror('No se puede crear el directorio de configuración', specdir, 'porque ya existe un archivo con ese nombre')
    else:
        makedirs(specdir)

    selprogdirs = [progdirnames[i] for i in dialogs.choosemany('Seleccione los programas que desea configurar o reconfigurar', choices=natsort(prognames.values()), default=[prognames[i] for i in configured])]

    for progdir in selprogdirs:
        makedirs(path.join(specdir, progdir))
        hardlink(path.join(cfgdir, 'hostspec.json'), path.join(specdir, progdir, 'hostspec.json'))
        hardlink(path.join(cfgdir, 'queuespec.json'), path.join(specdir, progdir, 'queuespec.json'))
        copyfile(path.join(corespecdir, progdir, 'corespec.json'), path.join(specdir, progdir, 'corespec.json'))
        copypathspec = True
        if progdir not in configured or not path.isfile(path.join(specdir, progdir, 'pathspec.json')) or readspec(hostspecdir, selhostdir, 'pathspecs', progdir, 'pathspec.json') == readspec(specdir, progdir, 'pathspec.json') or dialogs.yesno('La configuración local del programa', q(prognames[progdir]), 'difiere de la configuración por defecto, ¿desea sobreescribirla?', default=False):
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

