# -*- coding: utf-8 -*-
import sys
from pwd import getpwnam
from grp import getgrgid
from getpass import getuser 
from socket import gethostname, gethostbyname
from os import path, listdir, environ, getcwd
from argparse import ArgumentParser, SUPPRESS
from . import messages
from .utils import Bunch, p
from .specparse import SpecBunch, readspec
from .jobutils import printchoices, findparameters, readcoords
from .fileutils import AbsPath, NotAbsolutePath

envars = Bunch()
cluster = Bunch()
jobspecs = SpecBunch()
keywords = {}

try:
    specdir = AbsPath(environ['SPECPATH'], cwdir=getcwd())
except KeyError:
    messages.cfgerror('No se pueden enviar trabajos porque no se definió la variable de entorno $SPECPATH')

cluster.user = getuser()
cluster.home = path.expanduser('~')
cluster.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
program = path.basename(sys.argv[0])

try:
    envars.TELEGRAM_CHAT_ID = environ['TELEGRAM_CHAT_ID']
except KeyError:
    pass

jobspecs.merge(readspec(path.join(specdir, 'hostspec.json')))
jobspecs.merge(readspec(path.join(specdir, 'queuespec.json')))
jobspecs.merge(readspec(path.join(specdir, 'progspec.json')))
jobspecs.merge(readspec(path.join(specdir, 'hostprogspec.json')))

userspecdir = path.join(cluster.home, '.jobspecs', program + '.json')

if path.isfile(userspecdir):
    jobspecs.merge(readspec(userspecdir))

try: cluster.name = jobspecs.clustername
except AttributeError:
    messages.cfgerror('No se definió la propiedad "clustername" en la configuración')

try: cluster.head = jobspecs.headname.format(hostname=gethostname())
except AttributeError:
    messages.cfgerror('No se definió la propiedad "headname" en la configuración')

parser = ArgumentParser(prog=program, add_help=False, description='Ejecuta trabajos de {} en el sistema de colas del clúster.'.format(jobspecs.progname))

parser.add_argument('-l', '--list', action='store_true', help='Mostrar las opciones disponibles y salir.')
parsed, remaining = parser.parse_known_args()

if parsed.list:
    if jobspecs.versions:
        print('Versiones del programa')
        printchoices(choices=jobspecs.versions, default=jobspecs.defaults.version)
    for parkey in jobspecs.parameters:
        if parkey in jobspecs.defaults.parampaths:
            if 'paramsets' in jobspecs.defaults and parkey in jobspecs.defaults.paramsets:
                if isinstance(jobspecs.defaults.paramsets[parkey], (list, tuple)):
                    defaults = jobspecs.defaults.paramsets[parkey]
                else:
                    messages.opterror('Los conjuntos de parámetros por defecto deben definirse en una lista', p(parkey))
            else:
                defaults = []
            print('Conjuntos de parámetros', p(parkey))
            pathcomponents = AbsPath(jobspecs.defaults.parampaths[parkey], cwdir=getcwd()).setkeys(cluster).populate()
            findparameters(AbsPath(next(pathcomponents)), pathcomponents, defaults, 1)
    if jobspecs.keywords:
        print('Variables de interpolación')
        printchoices(choices=jobspecs.keywords)
    raise SystemExit()

#TODO: Set default=SUPPRESS for all options
parser.add_argument('-v', '--version', metavar='PROGVERSION', help='Versión del ejecutable.')
parser.add_argument('-q', '--queue', metavar='QUEUENAME', help='Nombre de la cola requerida.')
parser.add_argument('-n', '--ncore', type=int, metavar='#CORES', help='Número de núcleos de cpu requeridos.')
parser.add_argument('-N', '--nhost', type=int, metavar='#HOSTS', help='Número de nodos de ejecución requeridos.')
#parser.add_argument('-c', '--collect', action='store_true', help='Recolectar todos los archivos de entrada en la carpeta de salida.')
parser.add_argument('-w', '--wait', type=float, metavar='TIME', help='Tiempo de pausa (en segundos) después de cada ejecución.')
parser.add_argument('-M', '--match', metavar='REGEX', help='Enviar únicamente los trabajos que coinciden con la expresión regular.')
parser.add_argument('-X', '--xdialog', action='store_true', help='Habilitar el modo gráfico para los mensajes y diálogos.')
parser.add_argument('-I', '--ignore-defaults', dest='ignore-defaults', action='store_true', help='Ignorar todas las opciones por defecto.')
parser.add_argument('--temporary', action='store_true', help='Borrar los archivos de entrada y vrear una carpeta temporal de salida.')
parser.add_argument('--nodes', metavar='NODENAME', help='Solicitar nodos específicos de ejecución por nombre.')
parser.add_argument('--outdir', metavar='OUTPUTDIR', help='Usar OUTPUTDIR com directorio de salida.')
parser.add_argument('--scrdir', metavar='SCRATCHDIR', help='Usar SCRATCHDIR como directorio de escritura.')

sortgroup = parser.add_mutually_exclusive_group()
sortgroup.add_argument('-s', '--sort', action='store_true', help='Ordenar los argumentos numéricamente de menor a mayor.')
sortgroup.add_argument('-S', '--sort-reverse', dest='sort-reverse', action='store_true', help='Ordenar los argumentos numéricamente de mayor a menor.')

yngroup = parser.add_mutually_exclusive_group()
yngroup.add_argument('--si', '--yes', dest='yes', action='store_true', default=False, help='Responder "si" a todas las preguntas.')
yngroup.add_argument('--no', dest='no', action='store_true', default=False, help='Responder "no" a todas las preguntas.')

for key in jobspecs.parameters:
    parser.add_argument('--' + key, dest=key, metavar='PARAMSET', default=SUPPRESS, help='Nombre del conjunto de parámetros.')
    parser.add_argument('--' + key + '-path', dest=key+'-path', metavar='PARAMPATH', default=SUPPRESS, help='Ruta del directorio de parámetros.')

for item in jobspecs.resumefiles:
    key = item.split('|')[0]
    parser.add_argument('--' + key + 'file', dest=key+'file' , metavar='FILEPATH', default=SUPPRESS, help='Ruta del archivo ' + key + '.')

options, remaining = parser.parse_known_args(remaining)
#print(options)

for key in jobspecs.keywords:
    parser.add_argument('--'+key, metavar=key.upper(), help='Valor de la variable {}.'.format(key.upper()))

parsed, remaining = parser.parse_known_args(remaining)

for key, value in vars(parsed).items():
    if value: keywords[key] = value

rungroup = parser.add_mutually_exclusive_group()
rungroup.add_argument('-H', '--host', dest='remotehost', metavar='HOSTNAME', help='Procesar los archivos de entrada y enviar el trabajo al host remoto HOSTNAME.')
rungroup.add_argument('--dry', dest='drytest', action='store_true', help='Procesar los archivos de entrada sin enviar el trabajo.')

parser.add_argument('-m', '--mol', dest='coordfile', metavar='MOLFILE', help='Ruta del archivo de coordenadas para la interpolación.')
parser.add_argument('--prefix', dest='jobprefix', metavar='PREFIX', help='Anteponer el prefijo PREFIX al nombre del trabajo.')

parser.add_argument('-i', '--interpolate', action='store_true', help='Interpolar los archivos de entrada.')

parser.add_argument('files', nargs='*', metavar='FILE(S)', help='Rutas de los archivos de entrada.')
parser.add_argument('-h', '--help', action='help', help='Mostrar este mensaje de ayuda y salir.')

parsed = parser.parse_args(remaining)
globals().update(vars(parsed))

if not files:
    messages.opterror('Debe especificar al menos un archivo de entrada')

if interpolate:
    if jobprefix:
        if coordfile:
            jobprefix = readcoords(coordfile, keywords) + '.' + jobprefix
    else:
        if coordfile:
            jobprefix = readcoords(coordfile, keywords)
        else:
            messages.opterror('Para interpolar debe especificar un archivo de coordenadas o/y un prefijo de trabajo')
elif coordfile or keywords:
    messages.opterror('Se especificaron coordenadas o variables de interpolación pero no se va a interpolar nada')

