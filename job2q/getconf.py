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
from job2q.utils import realpath, natsort, p
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

if optconf.queue is None:
    if jobconf.defaults.queue:
        optconf.queue = jobconf.defaults.queue
    else:
        messages.cfgerr('<default><queue> No se especificó la cola por defecto')

if jobconf.outputdir:
    try: jobconf.outputdir = bool(strtobool(jobconf.outputdir))
    except ValueError:
        messages.cfgerr('<outputdir> El texto de este tag debe ser "True" or "False"')
else:
    messages.cfgerr('<outputdir> No se especificó si se requiere crear una carpeta de salida')

if optconf.interactive is True:
    jobconf.defaults = []

if jobconf.parallelization:
    if jobconf.parallelization in MPILibs:
        if jobconf.mpiwrapper:
            try: jobconf.mpiwrapper = bool(strtobool(jobconf.mpiwrapper))
            except ValueError:
                messages.cfgerr('<mpiwrapper> El valor de debe ser True or False')
        else:
            messages.cfgerr('<mpiwrapper> No se especificó ningún wrapper MPI')
else:
    messages.cfgerr('<mpiwrapper> No se especificó el tipo de paralelización del programa')

if not jobconf.fileexts:
    messages.cfgerr('<fileexts> Falta la lista de extensiones de archivo de o la lista está vacía')

if jobconf.inputfiles:
    for key in jobconf.inputfiles:
        if not key in jobconf.fileexts:
            messages.cfgerr('<inputfiles><e key="{0}"> El nombre de este archivo de entrada no fue definido'.format(ext))
else:
    messages.cfgerr('<inputfiles> Falta la lista de archivos de entrada o la lista está vacía')

if jobconf.outputfiles:
    for key in jobconf.outputfiles:
        if not key in jobconf.fileexts:
            messages.cfgerr('<otputfiles><e key="{0}"> El nombre de este archivo de salida no fue definido'.format(ext))
else:
    messages.cfgerr('<outputfiles> Falta la lista de archivos de salida o la lista está vacía')

if optconf.version is None:
    if 'version' in jobconf.defaults:
        optconf.version = jobconf.defaults.version
    else:
        optconf.version = dialogs.optone('Seleccione una versión', choices=list(jobconf.versions))

if jobconf.versions:
    if optconf.version in jobconf.versions:
        program = jobconf.versions[optconf.version]
    else:
        messages.opterr('La versión seleccionada', str(e.args[0]), 'es inválida')
else:
    messages.cfgerr('<versions> Falta la lista de versiones o la lista está vacía')

if not program.executable:
    messages.cfgerr('No se indicó el ejecutable para la versión', optconf.version)

optconf.scratch = realpath(optconf.scratch)

