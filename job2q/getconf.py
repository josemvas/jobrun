# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
from errno import ENOENT
from os import path, listdir
from argparse import ArgumentParser
from importlib import import_module
from distutils.util import strtobool

from job2q import dialogs
from job2q import messages
from job2q.utils import realpath, natsort, pathjoin, p
from job2q.readspec import readspec
from job2q.spectags import MPILibs
from job2q.exceptions import * 

alias = path.basename(sys.argv[0])
specdir = path.dirname(sys.argv[0])
homedir = path.expanduser('~')

if specdir is None:
    mesagges.usrerror('No se especificó el directorio de configuración del paquete')

platform = path.join(specdir, 'platform.xml')
corespec = path.join(specdir, 'corespec.xml')
hostspec = path.join(specdir, 'hostspec.xml')
userspec = path.join(homedir, '.j2q', 'jobspec.xml')
#TODO: commonspec =

jobconf = readspec(platform)
jobconf.merge(readspec(corespec))
jobconf.merge(readspec(hostspec))

try: jobconf.merge(readspec(userspec))
except FileNotFoundError as e:
    if e.errno != ENOENT:
        raise

sysconf = import_module('.schedulers.' + jobconf.scheduler, package='job2q')

parser = ArgumentParser(prog=alias, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
parser.add_argument('-l', '--listing', dest='listing', action='store_true', help='Lista las versiones de los programas y parámetros disponibles.')
parser.add_argument('-v', '--version', metavar='PROG VERSION', type=str, dest='version', help='Versión del ejecutable.')
parser.add_argument('-q', '--queue', metavar='QUEUE NAME', type=str, dest='queue', help='Nombre de la cola requerida.')
parser.add_argument('-n', '--ncpu', metavar='CPU CORES', type=int, dest='ncpu', default=1, help='Número de núcleos de procesador requeridos.')
parser.add_argument('-w', '--wait', metavar='TIME', type=float, dest='waitime', help='Tiempo de pausa (en segundos) después de cada ejecución.')
if jobconf.parameters:
    parser.add_argument('-p', metavar='SETNAME', type=str, dest=list(jobconf.parameters)[0], help='Nombre del conjunto de parámetros.')
for key in jobconf.parameters:
    parser.add_argument('--' + key, metavar='SETNAME', type=str, dest=key, help='Nombre del conjunto de parámetros.')
parser.add_argument('-X', '--xdialog', dest='xdialog', action='store_true', help='Usar Xdialog en vez de la terminal para interactuar con el usuario.')
parser.add_argument('-i', '--interactive', dest='interactive', action='store_true', help='Selección interactiva de las versiones de los programas y los parámetros.')
parser.add_argument('-s', '--sort', dest='sort', action='store_true', help='Ordena la lista de argumentos en orden numérico')
parser.add_argument('-S', '--sortreverse', dest='sortreverse', action='store_true', help='Ordena la lista de argumentos en orden numérico inverso')
parser.add_argument('--si', '--yes', dest='defaultanswer', action='store_true', default=None, help='Responder "si" a todas las preguntas.')
parser.add_argument('--no', dest='defaultanswer', action='store_false', default=None, help='Responder "no" a todas las preguntas.')
parser.add_argument('--nodes', metavar='NODE LIST', type=int, dest='nodes', help='Lista de los nodos requeridos.')
parser.add_argument('--hostname', metavar='HOST NAME', type=str, dest='exechost', help='Nombre del host requerido.')
parser.add_argument('--scratch', metavar='SCRATCH DIR', type=str, dest='scratch', help='Directorio temporal de escritura.')
parser.add_argument('inputlist', nargs='*', metavar='INPUT FILE(S)', help='Nombre del archivo de entrada.')

optconf = parser.parse_args()

if optconf.listing:
    messages.lsinfo('Versiones disponibles:', info=jobconf.versions, default=jobconf.defaults.version)
    for key in jobconf.parameters:
        messages.lsinfo('Conjuntos de parámetros disponibles', p(key), info=listdir(jobconf.parameters[key]))
    raise SystemExit()

if not optconf.inputlist:
    messages.opterr('No se definió ningún archivo de entrada')

if optconf.waitime is None:
    try: optconf.waitime = float(jobconf.defaults.waitime)
    except AttributeError:  optconf.waitime = 0

if optconf.sort:
    optconf.inputlist.sort(key=natsort)
elif optconf.sortreverse:
    optconf.inputlist.sort(key=natsort, reverse=True)

if not jobconf.scheduler:
    messages.cfgerr('<scheduler> No se especificó el nombre del sistema de colas')

if not jobconf.storage:
    messages.cfgerr('<storage> No se especificó el tipo de almacenamiento')

if optconf.scratch is None:
    if jobconf.defaults.scratch:
        optconf.scratch = jobconf.defaults.scratch
    else:
        messages.cfgerr('<scratch> No se especificó el directorio temporal de escritura por defecto')

optconf.scratch = realpath(optconf.scratch)

if optconf.queue is None:
    if jobconf.defaults.queue:
        optconf.queue = jobconf.defaults.queue
    else:
        messages.cfgerr('<default><queue> No se especificó la cola por defecto')

if jobconf.makefolder:
    try: jobconf.makefolder = bool(strtobool(jobconf.makefolder))
    except ValueError:
        messages.cfgerr('<outputdir> El texto de este tag debe ser "True" or "False"')
else:
    messages.cfgerr('<outputdir> No se especificó si se requiere crear una carpeta de salida')

if jobconf.mpiwrapper:
    try: jobconf.mpiwrapper = bool(strtobool(jobconf.mpiwrapper))
    except KeyError:
        messages.cfgerr('<mpiwrapper> El texto de este tag debe ser "True" o "False"')

if optconf.interactive is True:
    jobconf.defaults = []

if not jobconf.fileexts:
    messages.cfgerr('<fileexts> La lista de archivos del programa no existe o está vacía')

if jobconf.inputfiles:
    for item in jobconf.inputfiles:
        for key in item.split('|'):
            if not key in jobconf.fileexts:
                messages.cfgerr('<inputfiles><e>{0}</e> El nombre de este archivo de entrada no fue definido'.format(key))
else:
    messages.cfgerr('<inputfiles> La lista de archivos de entrada no existe o está vacía')

if jobconf.outputfiles:
    for item in jobconf.outputfiles:
        for key in item.split('|'):
            if not key in jobconf.fileexts:
                messages.cfgerr('<otputfiles><e>{0}</e> El nombre de este archivo de salida no fue definido'.format(key))
else:
    messages.cfgerr('<outputfiles> La lista de archivos de salida no existe o está vacía')

if jobconf.versions:
    if optconf.version is None:
        if 'version' in jobconf.defaults:
            if jobconf.defaults.version in jobconf.versions:
                optconf.version = jobconf.defaults.version
            else:
                messages.opterr('La versión establecida por default es inválida')
        else:
            optconf.version = dialogs.optone('Seleccione una versión', choices=list(jobconf.versions))
            if not optconf.version in jobconf.versions:
                messages.opterr('La versión seleccionada es inválida')
else:
    messages.cfgerr('<versions> La lista de versiones no existe o está vacía')

if not jobconf.versions[optconf.version].executable:
    messages.cfgerr('No se especificó el ejecutable de la versión', optconf.version)

executable = jobconf.versions[optconf.version].executable
profile = jobconf.versions[optconf.version].profile

optconf.parameters = []
for key in jobconf.parameters:
    pardir = realpath(jobconf.parameters[key])
    parset = getattr(optconf, key)
    try: choices = listdir(pardir)
    except FileNotFoundError as e:
        if e.errno == ENOENT:
            messages.cfgerr('El directorio de parámetros', pardir, 'no existe')
    if not choices:
        messages.cfgerr('El directorio de parámetros', pardir, 'está vacío')
    if parset is None:
        if key in jobconf.defaults.parameters:
            parset = jobconf.defaults.parameters[key]
        else:
            parset = dialogs.optone('Seleccione un conjunto de parámetros', p(key), choices=choices)
    if path.exists(path.join(pardir, parset)):
        optconf.parameters.append(path.join(pardir, parset))
    else:
        messages.opterr('La ruta de parámetros', path.join(pardir, parset), 'no existe')

comments = []
environment = []
command = []

comments.append(sysconf.label.format(jobconf.pkgname))
comments.append(sysconf.queue.format(optconf.queue))

if optconf.exechost is not None: 
    comments.append(sysconf.host.format(optconf.exechost))

if jobconf.storage == 'pooled':
     comments.append(sysconf.stdout.format(pathjoin(optconf.scratch, (sysconf.jobid, 'out'))))
     comments.append(sysconf.stderr.format(pathjoin(optconf.scratch, (sysconf.jobid, 'err'))))
elif jobconf.storage == 'shared':
     comments.append(sysconf.stdout.format(pathjoin(outputdir, (sysconf.jobid, 'out'))))
     comments.append(sysconf.stderr.format(pathjoin(outputdir, (sysconf.jobid, 'err'))))
else:
     messages.cfgerr(jobconf.storage + ' no es un tipo de almacenamiento soportado por este script')

#TODO: MPI support for Slurm
if jobconf.parallelib:
    if jobconf.parallelib.lower() == 'none':
        comments.append(sysconf.ncpu.format(1))
    elif jobconf.parallelib.lower() == 'openmp':
        comments.append(sysconf.ncpu.format(optconf.ncpu))
        comments.append(sysconf.span.format(1))
        environment.append('export OMP_NUM_THREADS=' + str(optconf.ncpu))
    elif jobconf.parallelib.lower() in MPILibs:
        comments.append(sysconf.ncpu.format(optconf.ncpu))
        if optconf.nodes:
            comments.append(sysconf.span.format(optconf.nodes))
        if jobconf.mpiwrapper:
            command.append(sysconf.mpiwrapper[jobconf.parallelib])
        else:
            messages.cfgerr('<mpiwrapper> No se especificó si el programa require un wrapper de mpi para correr')
    else:
        messages.cfgerr('El tipo de paralelización ' + jobconf.parallelib + ' no está soportado')
else:
    messages.cfgerr('<parallelib> No se especificó el tipo de paralelización del programa')

environment.extend(sysconf.environment)
environment.extend(jobconf.environment)

for profile in jobconf.profile + profile:
    environment.append(profile)

for var in jobconf.filevars:
    environment.append(var + '=' + jobconf.fileexts[jobconf.filevars[var]])

environment.append("shopt -s nullglob extglob")
environment.append("workdir=" + pathjoin(optconf.scratch, sysconf.jobidvar))
environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
environment.append("jobram=$(($ncpu*$totalram/$(nproc --all)))")
environment.append("progname=" + jobconf.pkgname)

command.append(realpath(executable) if path.sep in executable else executable)

for key in jobconf.optionargs:
    if not key in jobconf.fileexts:
        messages.cfgerr('<optionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
    command.append(wordjoin('-' + key, jobconf.fileexts[jobconf.optionargs[arg]]))

for item in jobconf.positionargs:
    for key in item.split('|'):
        if not key in jobconf.fileexts:
            messages.cfgerr('<positionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
    command.append('@' + p('|'.join(jobconf.fileexts[i] for i in item.split('|'))))

if 'stdin' in jobconf:
    try: command.append('0<' + ' ' + jobconf.fileexts[jobconf.stdin])
    except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stdin + '" en el tag <stdin> no fue definido.')
if 'stdout' in jobconf:
    try: command.append('1>' + ' ' + jobconf.fileexts[jobconf.stdout])
    except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stdout + '" en el tag <stdout> no fue definido.')
if 'stderr' in jobconf:
    try: command.append('2>' + ' ' + jobconf.fileexts[jobconf.stderr])
    except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stderr + '" en el tag <stderr> no fue definido.')

