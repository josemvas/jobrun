# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
from os import path, listdir
from argparse import ArgumentParser
from importlib import import_module
from distutils.util import strtobool
from os.path import dirname, basename, realpath

from job2q import dialogs
from job2q import messages
from job2q.parsing import BunchDict, parsexml
from job2q.utils import pathjoin, pathexpand
from job2q.config import specdir

alias = basename(sys.argv[0])
homedir = path.expanduser('~')

platform = pathjoin(specdir, 'platform.xml')
corespec = pathjoin(specdir, 'corespec.xml')
hostspec = pathjoin(specdir, 'hostspec.xml')
userspec = pathjoin(homedir, '.j2q', 'jobspec.xml')
#TODO: commonspec =

jobconf = parsexml(platform)
jobconf.merge(parsexml(corespec))
jobconf.merge(parsexml(hostspec))

try: jobconf.merge(parsexml(userspec))
except IOError: pass

queueconf = import_module('.schedulers.' + jobconf.scheduler, package='job2q')

parser = ArgumentParser(prog=alias, add_help=False)
parser.add_argument('-l', '--listing', dest='listing', action='store_true', help='Lista las versiones de los programas y parámetros disponibles.')
parsed, parsing = parser.parse_known_args()

if parsed.listing:
    messages.lsinfo('Versiones del binario disponibles', info=jobconf.versions, default=jobconf.defaults.version)
    messages.lsinfo('Conjuntos de parámetros disponibles', info=jobconf.parameters)
    raise SystemExit()

parser = ArgumentParser(prog=alias, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
parser.add_argument('-l', '--list', dest='listonly', action='store_true', help='Lista las versiones de los programas y conjuntos de parámetros disponibles.')
parser.add_argument('-v', '--version', metavar = 'PROGVERSION', type=str, dest='version', help='Versión del ejecutable.')
parser.add_argument('-p', '--parameter', metavar = 'PARAMETERSET', type=str, dest='parameter', help='Versión del conjunto de parámetros.')
parser.add_argument('-q', '--queue', metavar = 'QUEUENAME', type=str, dest='queue', help='Nombre de la cola requerida.')
parser.add_argument('-n', '--ncpu', metavar ='CPUCORES', type=int, dest='ncpu', default=1, help='Número de núcleos de procesador requeridos.')
parser.add_argument('-N', '--nodes', metavar ='NODELIST', type=int, dest='nodes', help='Lista de los nodos requeridos.')
parser.add_argument('-H', '--hostname', metavar = 'HOSTNAME', type=str, dest='exechost', help='Nombre del host requerido.')
parser.add_argument('-s', '--scratch', metavar = 'SCRATCHDIR', type=str, dest='scratch', help='Directorio temporal de escritura.')
parser.add_argument('-i', '--interactive', dest='interactive', action='store_true', help='Selección interactiva de las versiones de los programas y los parámetros.')
parser.add_argument('-X', '--xdialog', dest='xdialog', action='store_true', help='Usar Xdialog en vez de la terminal para interactuar con el usuario.')
parser.add_argument('-w', '--wait', metavar='WAITTIME', type=float, dest='waitime', help='Tiempo de pausa (en segundos) después de cada ejecución.')
parser.add_argument('--sort', dest='sort', type=str, default='', help='Ordena la lista de argumentos en el orden especificado')
parser.add_argument('--si', '--yes', dest='defaultanswer', action='store_true', default=None, help='Responder "si" a todas las preguntas.')
parser.add_argument('--no', dest='defaultanswer', action='store_false', default=None, help='Responder "no" a todas las preguntas.')
parser.add_argument('inputlist', nargs='+', metavar='INPUTFILE', help='Nombre del archivo de entrada.')

userconf = parser.parse_args(parsing)

if not userconf.inputlist:
    messages.opterr('Debe especificar al menos un archivo de entrada')
else:
    inputlist = userconf.inputlist

if userconf.waitime is None:
    try: waitime = float(jobconf.defaults.waitime)
    except AttributeError:  waitime = 0
else:
    waitime = userconf.waitime

#TODO: Sort in alphabetical or numerical order
if 'r' in userconf.sort:
    userconf.inputlist.sort(reverse=True)

try: jobconf.scheduler
except AttributeError: messages.cfgerr('No se especificó el nombre del sistema de colas (scheduler)')

try: jobconf.storage
except AttributeError: messages.cfgerr('No se especificó el tipo de almacenamiento (storage)')

if userconf.scratch is None:
    try: userconf.scratch = pathexpand(jobconf.defaults.scratch)
    except AttributeError: messages.cfgerr('No se especificó el directorio temporal de escritura por defecto (scratch)')

if userconf.queue is None:
    try: userconf.queue = jobconf.defaults.queue
    except AttributeError: messages.cfgerr('No se especificó la cola por defecto (queue)')

try: jobconf.outputdir = bool(strtobool(jobconf.outputdir))
except AttributeError: messages.cfgerr('No se especificó si se debe crear una carpeta de salida (outputdir)')
except ValueError: messages.cfgerr('El valor debe ser True or False (outputdir)')

if userconf.interactive is True:
    jobconf.defaults = []

try: jobconf.runtype
except AttributeError: messages.cfgerr('No se especificó el tipo de paralelización del programa')

if jobconf.runtype in ('intelmpi', 'openmpi', 'mpich'):
    try: jobconf.mpiwrapper = bool(strtobool(jobconf.mpiwrapper))
    except AttributeError: messages.cfgerr('No se especificó ningún wrapper MPI (mpiwrapper)')
    except ValueError: messages.cfgerr('El valor de debe ser True or False (mpiwrapper)')

if jobconf.versions:
    if userconf.version is None:
        if 'version' in jobconf.defaults:
            userconf.version = jobconf.defaults.version
        else:
            choices = sorted(list(jobconf.versions))
            userconf.version = dialogs.optone('Seleccione una versión', choices=choices)
    try: jobconf.program = jobconf.versions[userconf.version]
    except KeyError as e: messages.opterr('La versión seleccionada', str(e.args[0]), 'es inválida')
    except TypeError: messages.cfgerr('La lista de versiones está mal definida')
    try: jobconf.program.executable = pathexpand(jobconf.program.executable)
    except AttributeError: messages.cfgerr('No se especificó el ejecutable para la versión', userconf.version)
else: messages.cfgerr('La lista de versiones está vacía (versions)')

#TODO: Implement default parameter sets
jobconf.parsets = []
for item in jobconf.parameters:
    itempath = realpath(pathexpand(item))
    try:
        choices = sorted(listdir(itempath))
    except IOError:
        messages.cfgerr('El directorio padre de parámetros', item, 'no existe o no es un directorio')
    if not choices:
        messages.cfgerr('El directorio padre de parámetros', item, 'está vacío')
    if userconf.parameter is None:
        userconf.parameter = choices[0] if len(choices) == 1 else dialogs.optone('Seleccione un conjunto de parámetros', choices=choices)
    jobconf.parsets.append(pathjoin(itempath, userconf.parameter))

for ext in jobconf.inputfiles:
    try: jobconf.fileexts[ext]
    except KeyError:
        messages.cfgerr('El nombre del archivo de entrada con llave', ext, 'no está definido')

for ext in jobconf.outputfiles:
    try: jobconf.fileexts[ext]
    except KeyError:
        messages.cfgerr('El nombre del archivo de salida con llave', ext, 'no está definido')

