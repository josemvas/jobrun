# -*- coding: utf-8 -*-
import sys
import json
from getpass import getuser 
from socket import gethostname, gethostbyname
from os import path, listdir, environ, getcwd
from argparse import ArgumentParser
from . import messages
from .classes import Bunch, AbsPath
from .exceptions import NotAbsolutePath
from .utils import natsort, p, join_positional_args, pathseps
from .details import dictags, listags

class SpecList(list):
    def __init__(self, parentlist):
        for item in parentlist:
            if isinstance(item, dict):
                self.append(SpecBunch(item))
            elif isinstance(item, list):
                self.append(SpecList(item))
            else:
                self.append(item)
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge') and type(other[i]) is type(self[i]):
                    self[i].merge(other[i])
                elif other[i] == self[i]:
                    pass # same leaf value
                else:
                    raise Exception('Conflicto en {} entre {} y {}'.format(i, self[i], other[i]))
            else:
                self.append(other[i])

class SpecBunch(Bunch):
    def __init__(self, parentdict):
        for key, value in parentdict.items():
            if isinstance(value, dict):
                self[key] = SpecBunch(value)
            elif isinstance(value, list):
                self[key] = SpecList(value)
            else:
                self[key] = value
    def __missing__(self, item):
        if item in dictags:
            return SpecBunch({})
        elif item in listags:
            return SpecList([])
        else:
            return None
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge') and type(other[i]) is type(self[i]):
                    self[i].merge(other[i])
                elif other[i] == self[i]:
                    pass # same leaf value
                else:
                    raise Exception('Conflicto en {} entre {} y {}'.format(i, self[i], other[i]))
            else:
                self[i] = other[i]

def ordered(obj):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj

@join_positional_args(pathseps)
def readspec(jsonfile):
    with open(jsonfile, 'r') as fh:
        try: return SpecBunch(ordered(json.load(fh)))
        except ValueError as e:
            messages.cfgerror('El archivo {} contiene JSON inválido: {}'.format(fh.name, str(e)))

def parse():

    cluster.homedir = path.expanduser('~')
    cluster.program = path.basename(sys.argv[0])
    cluster.user = getuser()
    
    try:
        cluster.specdir = AbsPath(environ['SPECPATH'])
    except KeyError:
        messages.cfgerror('No se pueden enviar trabajos porque no se definió la variable de entorno $SPECPATH')
    except NotAbsolutePath:
        cluster.specdir = AbsPath(getcwd(), environ['SPECPATH'])
    
    try:
        cluster.telegram = environ['TELEGRAM_BOT_URL']
        cluster.chatid = environ['TELEGRAM_CHAT_ID']
    except KeyError:
        pass

    hostspec = path.join(cluster.specdir, 'hostspec.json')
    corespec = path.join(cluster.specdir, 'corespec.json')
    pathspec = path.join(cluster.specdir, 'pathspec.json')
    userspec = path.join(cluster.homedir, '.jobspec.json')
    
    jobspecs.merge(readspec(hostspec))
    jobspecs.merge(readspec(corespec))
    jobspecs.merge(readspec(pathspec))
    
    if path.isfile(userspec):
        jobspecs.merge(readspec(userspec))
    
    try: cluster.name = jobspecs.clustername
    except AttributeError:
        messages.cfgerror('No se definió la propiedad "clustername" en la configuración')

    try: cluster.head = jobspecs.headname.format(hostname=gethostname())
    except AttributeError:
        messages.cfgerror('No se definió la propiedad "headname" en la configuración')

    parser = ArgumentParser(prog=cluster.program, add_help=False, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
    parser.add_argument('-l', '--list', action='store_true', help='Mostrar las versiones de los programas y parámetros disponibles.')
    parser.add_argument('-v', '--version', metavar='PROGVERSION', type=str, help='Versión del ejecutable.')
    parser.add_argument('-q', '--queue', metavar='QUEUENAME', type=str, help='Nombre de la cola requerida.')
    parser.add_argument('-n', '--ncore', metavar='#CORES', type=int, default=1, help='Número de núcleos de cpu requeridos.')
    parser.add_argument('-N', '--nhost', metavar='#HOSTS', type=int, default=1, help='Número de nodos de ejecución requeridos.')
    parser.add_argument('-w', '--wait', metavar='TIME', type=float, help='Tiempo de pausa (en segundos) después de cada ejecución.')
    parser.add_argument('-t', '--template', action='store_true', help='Interpolar los archivos de entrada.')
    parser.add_argument('-m', '--molfile', metavar='MOLFILE', type=str, help='Ruta del archivo de coordenadas para la interpolación.')
    parser.add_argument('-j', '--jobname', metavar='MOLNAME', type=str, help='Nombre del trabajo de interpolación.')
    parser.add_argument('-s', '--sort', action='store_true', help='Ordenar la lista de argumentos en orden numérico')
    parser.add_argument('-S', '--sortrev', action='store_true', help='Ordenar la lista de argumentos en orden numérico inverso')
    parser.add_argument('-i', '--interactive', action='store_true', help='Seleccionar interactivamente las versiones y parámetros.')
    parser.add_argument('-X', '--xdialog', action='store_true', help='Habilitar el modo gráfico para los mensajes y diálogos.')
    parser.add_argument('--si', '--yes', dest='yes', action='store_true', default=False, help='Responder "si" a todas las preguntas.')
    parser.add_argument('--no', dest='no', action='store_true', default=False, help='Responder "no" a todas las preguntas.')
    parser.add_argument('--outdir', metavar='OUTPUTDIR', type=str, help='Usar OUTPUTDIR com directorio de salida.')
    parser.add_argument('--scrdir', metavar='SCRATCHDIR', type=str, help='Usar SCRATCHDIR como directorio de escritura.')
    parser.add_argument('--node', metavar='NODENAME', type=str, help='Solicitar un nodo específico de ejecución.')
    parser.add_argument('--move', action='store_true', help='Mover los archivos de entrada a la carpeta de salida en vez de copiarlos.')
    
    if len(jobspecs.parameters) == 1:
        key = jobspecs.parameters.keys()[0]
        parser.add_argument('-p', '--' + key, metavar='SETNAME', type=str, dest=key, help='Nombre del conjunto de parámetros.')
    elif len(jobspecs.parameters) > 1:
        for key in jobspecs.parameters:
            parser.add_argument('--' + key, metavar='SETNAME', type=str, dest=key, help='Nombre del conjunto de parámetros.')

    for key in jobspecs.keywords:
        parser.add_argument('--' + key, metavar=key.upper(), type=str, dest=key, help='Valor de la variable {}'.format(key.upper()))
    
    parsed, remaining = parser.parse_known_args()
    options.update(vars(parsed))
    
    if options.list:
        if jobspecs.versions:
            messages.listing('Versiones del ejecutable disponibles:', items=sorted(jobspecs.versions, key=natsort), default=jobspecs.defaults.version)
        for key in jobspecs.parameters:
            messages.listing('Conjuntos de parámetros disponibles', p(key), items=sorted(listdir(jobspecs.parameters[key]), key=natsort), default=jobspecs.defaults.parameters[key])
        if jobspecs.keywords:
            messages.listing('Variables de interpolación disponibles:', items=sorted(jobspecs.keywords, key=natsort))
        raise SystemExit()

    parser.add_argument('-r', '--remote-to', metavar='HOSTNAME', type=str, help='Ejecutar el trabajo en el host remoto HOSTNAME.')
    parser.add_argument('-R', '--remote-from', metavar='HOSTNAME', type=str, help='Ejecutar el trabajo del host remoto HOSTNAME.')
    parsed, remaining = parser.parse_known_args()

    parser.add_argument('files', nargs='*', metavar='FILE(S)', type=str, help='Rutas de los archivos de entrada.')
    parsed, remaining = parser.parse_known_args()

    files[:] = parsed.files

    parser.add_argument('-h', '--help', action='help', help='Mostrar este mensaje de ayuda y salir')
    parser.parse_args(remaining)

    if not files:
        messages.opterror('Debe especificar al menos un archivo de entrada')

    if parsed.remote_from:
        if 'JOBSHARE' in environ:
            remote.fromhost = parsed.remote_from
        else:
            messages.cfgerror('No se pueden aceptar trabajos remotos porque no se definió la variable de entorno $JOBSHARE')

    if parsed.remote_to:
        remote.tohost = parsed.remote_to
        remote.share = '$JOBSHARE'
        remote.user = '{user}@{host}'.format(user=cluster.user, host=cluster.head)
        return False
    else:
        return True

cluster = Bunch({})
options = Bunch({})
jobspecs = SpecBunch({})
remote = Bunch({})
files = []

