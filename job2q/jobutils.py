# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from argparse import ArgumentParser
from os import path, listdir, getcwd, environ
from importlib import import_module
from socket import gethostbyname
from . import details
from . import dialogs
from . import messages
from . import tkboxes
from .readspec import readspec, Bunch
from .utils import homedir, wordjoin, pathjoin, realpath, normalpath, isabspath, natsort, p, q, sq
from .strings import mpiLibs, boolStrDict
from .chemistry import readxyz

jobconf = Bunch({})
options = Bunch({})
files = []

jobcomments = []
environment = []
commandline = []
keywords = {}

def nextfile():
    
    filepath = path.abspath(files.pop(0))
    basename = path.basename(filepath)

    if isabspath(filepath):
        parentdir = path.dirname(normalpath(filepath))
    else:
        if details.clientdir:
            parentdir = path.dirname(normalpath(details.clientdir, filepath))
        else:
            parentdir = path.dirname(normalpath(path.getcwd(), filepath))
        filepath = normalpath(parentdir, filepath)
    
    if path.isfile(filepath):
        for key in (k for i in jobconf.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                filename = basename[:-len(key)-1]
                extension = key
                break
        else:
            messages.failure('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobconf.progname)
            raise(AssertionError)
    elif path.isdir(filepath):
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'es un directorio')
        raise(AssertionError)
    elif path.exists(filepath):
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no es un archivo regular')
        raise(AssertionError)
    else:
        messages.failure('Este trabajo no se envió porque el archivo de entrada', filepath, 'no existe')
        raise(AssertionError)

    return parentdir, filename, extension


def decode():

    details.alias = path.basename(sys.argv[0])
    specdir = path.expanduser(environ['SPECPATH'])

    if 'JOBCLIENT' in environ:
        if 'REMOTEJOBS' in environ:
            details.clientdir = normalpath(environ['REMOTEJOBS'], environ['JOBCLIENT'])
        else:
            messages.cfgerror('No se pueden aceptar trabajos remotos porque la variable de entorno $REMOTEJOBS aún no existe')
    
    hostspec = path.join(specdir, 'hostspec.json')
    corespec = path.join(specdir, 'corespec.json')
    pathspec = path.join(specdir, 'pathspec.json')
    userspec = path.join(homedir, '.jobspec.json')
    
    jobconf.merge(readspec(hostspec))
    jobconf.merge(readspec(corespec))
    jobconf.merge(readspec(pathspec))
    
    if path.isfile(userspec):
        jobconf.merge(readspec(userspec))
    
    parser = ArgumentParser(prog=details.alias, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
    parser.add_argument('-l', '--lsopt', action='store_true', help='Imprimir las versiones de los programas y parámetros disponibles.')
    parser.add_argument('-v', '--version', metavar='PROGVERSION', type=str, help='Versión del ejecutable.')
    parser.add_argument('-q', '--queue', metavar='QUEUENAME', type=str, help='Nombre de la cola requerida.')
    parser.add_argument('-n', '--ncore', metavar='#CORES', type=int, default=1, help='Número de núcleos de cpu requeridos.')
    parser.add_argument('-N', '--nhost', metavar='#HOSTS', type=int, default=1, help='Número de nodos de ejecución requeridos.')
    parser.add_argument('-w', '--wait', metavar='TIME', type=float, help='Tiempo de pausa (en segundos) después de cada ejecución.')
    parser.add_argument('-t', '--template', action='store_true', help='Interpolar los archivos de entrada.')
    parser.add_argument('-m', '--molfile', metavar='MOLFILE', type=str, help='Ruta del archivo de coordenadas para la interpolación.')
    parser.add_argument('-j', '--jobname', metavar='MOLNAME', type=str, help='Nombre del trabajo de interpolación.')
    parser.add_argument('-s', '--sort', action='store_true', help='Ordenar la lista de argumentos en orden numérico')
    parser.add_argument('-S', '--sortreverse', action='store_true', help='Ordenar la lista de argumentos en orden numérico inverso')
    parser.add_argument('-i', '--interactive', action='store_true', help='Seleccionar interactivamente las versiones y parámetros.')
    parser.add_argument('-X', '--xdialog', action='store_true', help='Usar Xdialog en vez de la terminal para interactuar con el usuario.')
    parser.add_argument('--si', '--yes', dest='yes', action='store_true', default=False, help='Responder "si" a todas las preguntas.')
    parser.add_argument('--no', dest='no', action='store_false', default=False, help='Responder "no" a todas las preguntas.')
    parser.add_argument('--move', action='store_true', help='Mover los archivos de entrada a la carpeta de salida en vez de copiarlos.')
    parser.add_argument('--outdir', metavar='OUTDIR', type=str, help='Cambiar el directorio de salida.')
    parser.add_argument('--scrdir', metavar='SCRATCHDIR', type=str, help='Cambiar el directorio de escritura.')
    parser.add_argument('--node', metavar='NODENAME', type=str, help='Solicitar un nodo específico de ejecución.')
    
    if len(jobconf.parameters) == 1:
        parser.add_argument('-p', metavar='SETNAME', type=str, dest=list(jobconf.parameters)[0], help='Nombre del conjunto de parámetros.')
    for key in jobconf.parameters:
        parser.add_argument('--' + key, metavar='SETNAME', type=str, dest=key, help='Nombre del conjunto de parámetros.')
    for key in jobconf.formatkeys:
        parser.add_argument('--' + key, metavar='VALUE', type=str, dest=key, help='Valor de la variable de interpolación.')
    
    parsed, remaining = parser.parse_known_args()
    options.update(vars(parsed))
    
    if options.lsopt:
        if jobconf.versions:
            messages.listing('Versiones del ejecutable disponibles:', items=sorted(jobconf.versions, key=natsort), default=jobconf.defaults.version)
        for key in jobconf.parameters:
            messages.listing('Conjuntos de parámetros disponibles', p(key), items=sorted(listdir(jobconf.parameters[key]), key=natsort), default=jobconf.defaults.parameters[key])
        if jobconf.formatkeys:
            messages.listing('Variables de interpolación disponibles:', items=sorted(jobconf.formatkeys, key=natsort))
        raise SystemExit()
    
    parser.add_argument('-R', '--remote', metavar='HOSTNAME', type=str, help='Ejecutar el trabajo remotamente en HOSTNAME.')
    parsed, remaining = parser.parse_known_args()

    parser.add_argument('files', nargs='+', metavar='FILE(S)', type=str, help='Rutas de los archivos de entrada.')

    files[:] = parser.parse_args(remaining).files
    details.clienthost = gethostbyname(jobconf.headname)
    details.remotehost = parsed.remote

def configure():

    if not jobconf.scheduler:
        messages.cfgerror('<scheduler> No se especificó el nombre del sistema de colas')
    
    scheduler = import_module('.schedulers.' + jobconf.scheduler, package='job2q')
    jobformat = Bunch(scheduler.jobformat)
    jobenvars = Bunch(scheduler.jobenvars)
    mpilauncher = scheduler.mpilauncher
    
    for key in jobconf.formatkeys:
        if key in options:
            keywords[key] = options[key]

    if options.sort:
        files.sort(key=natsort)
    elif options.sortreverse:
        files.sort(key=natsort, reverse=True)
    
    if details.clientdir:
        if isabspath(details.clientdir):
            details.clientdir = normalpath(details.clientdir)
        else: 
            details.clientdir = normalpath(jobconf.rootdir, details.clientdir)
    
    if options.wait is None:
        try: options.wait = float(jobconf.defaults.waitime)
        except AttributeError: options.wait = 0
    
    if options.xdialog:
        dialogs.yesno = tkboxes.ynbox
        messages.failure = tkboxes.msgbox
        messages.success = tkboxes.msgbox
    
    if not options.scrdir:
        if jobconf.defaults.scrdir:
            options.scrdir = jobconf.defaults.scrdir
        else:
            messages.cfgerror('<scrdir> No se especificó el directorio temporal de escritura por defecto')
    
    options.scrdir = realpath(options.scrdir)
    
    if not options.queue:
        if jobconf.defaults.queue:
            options.queue = jobconf.defaults.queue
        else:
            messages.cfgerror('<default><queue> No se especificó la cola por defecto')
    
    if not jobconf.progname:
        messages.cfgerror('<title> No se especificó el nombre del programa')
    
    if not jobconf.progkey:
        messages.cfgerror('<title> No se especificó la clave del programa')
    
    if jobconf.makejobdir:
        try: jobconf.makejobdir = boolStrDict[jobconf.makejobdir]
        except KeyError:
            messages.cfgerror('<outputdir> El texto de este tag debe ser "True" or "False"')
    else:
        messages.cfgerror('<outputdir> No se especificó si se requiere crear una carpeta de salida')
    
    if 'usempilauncher' in jobconf:
        try: jobconf.usempilauncher = boolStrDict[jobconf.usempilauncher]
        except KeyError:
            messages.cfgerror('<usempilauncher> El texto de este tag debe ser "True" o "False"')
    
    if options.interactive:
        jobconf.defaults = []
    
    if not jobconf.filekeys:
        messages.cfgerror('<filekeys> La lista de archivos del programa no existe o está vacía')
    
    if jobconf.inputfiles:
        for item in jobconf.inputfiles:
            for key in item.split('|'):
                if not key in jobconf.filekeys:
                    messages.cfgerror('<inputfiles><e>{0}</e> El nombre de este archivo de entrada no fue definido'.format(key))
    else:
        messages.cfgerror('<inputfiles> La lista de archivos de entrada no existe o está vacía')
    
    if jobconf.outputfiles:
        for item in jobconf.outputfiles:
            for key in item.split('|'):
                if not key in jobconf.filekeys:
                    messages.cfgerror('<otputfiles><e>{0}</e> El nombre de este archivo de salida no fue definido'.format(key))
    else:
        messages.cfgerror('<outputfiles> La lista de archivos de salida no existe o está vacía')
    
    if jobconf.versions:
        if not options.version:
            if 'version' in jobconf.defaults:
                if jobconf.defaults.version in jobconf.versions:
                    options.version = jobconf.defaults.version
                else:
                    messages.opterror('La versión establecida por default es inválida')
            else:
                options.version = dialogs.chooseone('Seleccione una versión', choices=sorted(list(jobconf.versions), key=natsort))
                if not options.version in jobconf.versions:
                    messages.opterror('La versión seleccionada es inválida')
    else:
        messages.cfgerror('<versions> La lista de versiones no existe o está vacía')
    
    if not jobconf.versions[options.version].executable:
        messages.cfgerror('No se especificó el ejecutable de la versión', options.version)
    
    executable = jobconf.versions[options.version].executable
    profile = jobconf.versions[options.version].profile
    
    options.parameters = []
    for key in jobconf.parameters:
        parameterdir = realpath(jobconf.parameters[key])
        parameterset = options[key]
        try: items = listdir(parameterdir)
        except FileNotFoundError as e:
            messages.cfgerror('El directorio de parámetros', parameterdir, 'no existe')
        if not items:
            messages.cfgerror('El directorio de parámetros', parameterdir, 'está vacío')
        if parameterset is None:
            if key in jobconf.defaults.parameters:
                parameterset = jobconf.defaults.parameters[key]
            else:
                parameterset = dialogs.chooseone('Seleccione un conjunto de parámetros', p(key), choices=sorted(items, key=natsort))
        if path.exists(path.join(parameterdir, parameterset)):
            options.parameters.append(path.join(parameterdir, parameterset))
        else:
            messages.opterror('La ruta de parámetros', path.join(parameterdir, parameterset), 'no existe')
    
    jobcomments.append(jobformat.label(jobconf.progname))
    jobcomments.append(jobformat.queue(options.queue))
    jobcomments.append(jobformat.stdout(options.scrdir))
    jobcomments.append(jobformat.stderr(options.scrdir))
    
    if options.node:
        jobcomments.append(jobformat.hosts(options.node))
    
    #TODO: MPI support for Slurm
    if jobconf.concurrency:
        if jobconf.concurrency.lower() == 'none':
            jobcomments.append(jobformat.nhost(options.nhost))
        elif jobconf.concurrency.lower() == 'openmp':
            jobcomments.append(jobformat.ncore(options.ncore))
            jobcomments.append(jobformat.nhost(options.nhost))
            environment.append('export OMP_NUM_THREADS=' + str(options.ncore))
        elif jobconf.concurrency.lower() in mpiLibs:
            if not 'usempilauncher' in jobconf:
                messages.cfgerror('<usempilauncher> No se especificó si el programa es lanzado por mpirun')
            jobcomments.append(jobformat.ncore(options.ncore))
            jobcomments.append(jobformat.nhost(options.nhost))
            if jobconf.usempilauncher:
                commandline.append(mpilauncher[jobconf.concurrency])
        else:
            messages.cfgerror('El tipo de paralelización ' + jobconf.concurrency + ' no está soportado')
    else:
        messages.cfgerror('<concurrency> No se especificó el tipo de paralelización del programa')
    
    environment.extend('='.join(i) for i in jobenvars.items())
    environment.extend(jobconf.onscript)
    environment.append("head=" + gethostbyname(jobconf.headname))
    
    for profile in jobconf.profile + profile:
        environment.append(profile)
    
    for var in jobconf.filevars:
        environment.append(var + '=' + sq(jobconf.filekeys[jobconf.filevars[var]]))
    
    environment.append("shopt -s nullglob extglob")
    environment.append("workdir=" + q(pathjoin(options.scrdir, jobenvars.jobid)))
    environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    environment.append("jobram=$(($ncore*$totalram/$(nproc --all)))")
    environment.append("progname=" + sq(jobconf.progname))
    
    commandline.append(realpath(executable) if path.sep in executable else executable)
    
    for key in jobconf.optionargs:
        if not jobconf.optionargs[key] in jobconf.filekeys:
            messages.cfgerror('<optionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
        commandline.append(wordjoin('-' + key, jobconf.filekeys[jobconf.optionargs[key]]))
    
    for item in jobconf.positionargs:
        for key in item.split('|'):
            if not key in jobconf.filekeys:
                messages.cfgerror('<positionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
        commandline.append('@' + p('|'.join(jobconf.filekeys[i] for i in item.split('|'))))
    
    if 'stdin' in jobconf:
        try: commandline.append('0<' + ' ' + jobconf.filekeys[jobconf.stdin])
        except KeyError: messages.cfgerror('El nombre de archivo "' + jobconf.stdin + '" en el tag <stdin> no fue definido.')
    if 'stdout' in jobconf:
        try: commandline.append('1>' + ' ' + jobconf.filekeys[jobconf.stdout])
        except KeyError: messages.cfgerror('El nombre de archivo "' + jobconf.stdout + '" en el tag <stdout> no fue definido.')
    if 'stderr' in jobconf:
        try: commandline.append('2>' + ' ' + jobconf.filekeys[jobconf.stderr])
        except KeyError: messages.cfgerror('El nombre de archivo "' + jobconf.stderr + '" en el tag <stderr> no fue definido.')
    
    if options.template:
        if options.molfile:
            molpath = Path(options.molfile)
            if molpath.is_file():
                keywords['mol0'] = molpath.resolve()
                if molpath.suffix == '.xyz':
                    for i, step in enumerate(readxyz(molpath), 1):
                        keywords['mol' + str(i)] = '\n'.join('{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format(*atom) for atom in step['coords'])
                    if not options.jobname:
                        options.jobname = molpath.stem
                else:
                    messages.opterror('Solamente están soportados archivos de coordenadas en formato xyz')
            elif molpath.is_dir():
                messages.opterror('El archivo de coordenadas', molpath, 'es un directorio')
            elif molpath.exists():
                messages.opterror('El archivo de coordenadas', molpath, 'no es un archivo regular')
            else:
                messages.opterror('El archivo de coordenadas', molpath, 'no existe')
        elif not options.jobname:
            messages.opterror('Se debe especificar el archivo de coordenadas y/o el nombre del trabajo para poder interpolar')
        
