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
from job2q.utils import pathexpand
from job2q.readspec import readspec
from job2q.exceptions import * 

alias = path.basename(sys.argv[0])
specdir = path.dirname(sys.argv[0])
homedir = path.expanduser('~')

if specdir is None:
    mesagges.usrerror('No se indicó el directorio de especificaciones del paquete')

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
if not 'versionprefix' in jobconf:
    jobconf.versionprefix = 'v'

parser = ArgumentParser(prog=alias, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
parser.add_argument('-l', '--listing', dest='listing', action='store_true', help='Lista las versiones de los programas y parámetros disponibles.')
parser.add_argument('-v', '--version', metavar='PROGVERSION', type=str, dest='version', help='Versión del ejecutable.')
parser.add_argument('-q', '--queue', metavar='QUEUENAME', type=str, dest='queue', help='Nombre de la cola requerida.')
parser.add_argument('-n', '--ncpu', metavar='CPUCORES', type=int, dest='ncpu', default=1, help='Número de núcleos de procesador requeridos.')
parser.add_argument('-N', '--nodes', metavar='NODELIST', type=int, dest='nodes', help='Lista de los nodos requeridos.')
parser.add_argument('-H', '--hostname', metavar='HOSTNAME', type=str, dest='exechost', help='Nombre del host requerido.')
parser.add_argument('-s', '--scratch', metavar='SCRATCHDIR', type=str, dest='scratch', help='Directorio temporal de escritura.')
parser.add_argument('-i', '--interactive', dest='interactive', action='store_true', help='Selección interactiva de las versiones de los programas y los parámetros.')
parser.add_argument('-X', '--xdialog', dest='xdialog', action='store_true', help='Usar Xdialog en vez de la terminal para interactuar con el usuario.')
parser.add_argument('-w', '--wait', metavar='WAITTIME', type=float, dest='waitime', help='Tiempo de pausa (en segundos) después de cada ejecución.')
parser.add_argument('--sort', dest='sort', type=str, default='', help='Ordena la lista de argumentos en el orden especificado')
parser.add_argument('--si', '--yes', dest='defaultanswer', action='store_true', default=None, help='Responder "si" a todas las preguntas.')
parser.add_argument('--no', dest='defaultanswer', action='store_false', default=None, help='Responder "no" a todas las preguntas.')
parser.add_argument('inputlist', nargs='*', metavar='INPUTFILE', help='Nombre del archivo de entrada.')
for key in jobconf.parameters:
    parser.add_argument('-p' + key, '--' + key + 'set', metavar='SETNAME', type=str, dest=key+'set', help='Nombre del conjunto de parámetros.')

optconf = parser.parse_args()

if optconf.listing:
    messages.lsinfo('Versiones disponibles:', info=jobconf.versions, default=jobconf.defaults.version)
    for key in jobconf.parameters:
        messages.lsinfo('Conjuntos de parámetros disponibles:', info=listdir(jobconf.parameters[key]))
        raise SystemExit()

if not optconf.inputlist:
    messages.opterr('No se definió ningún archivo de entrada')

if optconf.waitime is None:
    try: optconf.waitime = float(jobconf.defaults.waitime)
    except AttributeError:  optconf.waitime = 0

#TODO: Sort in alphabetical or numerical order
if 'r' in optconf.sort:
    optconf.inputlist.sort(reverse=True)

try: jobconf.scheduler
except AttributeError: messages.cfgerr('No se indicó el nombre del sistema de colas (scheduler)')

try: jobconf.storage
except AttributeError: messages.cfgerr('No se indicó el tipo de almacenamiento (storage)')

if optconf.scratch is None:
    try: optconf.scratch = jobconf.defaults.scratch
    except AttributeError: messages.cfgerr('No se indicó el directorio temporal de escritura por defecto (scratch)')
optconf.scratch = pathexpand(optconf.scratch)

if optconf.queue is None:
    try: optconf.queue = jobconf.defaults.queue
    except AttributeError: messages.cfgerr('No se indicó la cola por defecto (queue)')

try: jobconf.outputdir = bool(strtobool(jobconf.outputdir))
except AttributeError: messages.cfgerr('No se indicó si se debe crear una carpeta de salida (outputdir)')
except ValueError: messages.cfgerr('El valor debe ser True or False (outputdir)')

if optconf.interactive is True:
    jobconf.defaults = []

try: jobconf.runtype
except AttributeError: messages.cfgerr('No se indicó el tipo de paralelización del programa')

if jobconf.runtype in ('intelmpi', 'openmpi', 'mpich'):
    try: jobconf.mpiwrapper = bool(strtobool(jobconf.mpiwrapper))
    except AttributeError: messages.cfgerr('No se indicó ningún wrapper MPI (mpiwrapper)')
    except ValueError: messages.cfgerr('El valor de debe ser True or False (mpiwrapper)')

for ext in jobconf.inputfiles:
    try: jobconf.fileexts[ext]
    except KeyError:
        messages.cfgerr('El nombre del archivo de entrada con llave', ext, 'no está definido')

for ext in jobconf.outputfiles:
    try: jobconf.fileexts[ext]
    except KeyError:
        messages.cfgerr('El nombre del archivo de salida con llave', ext, 'no está definido')

