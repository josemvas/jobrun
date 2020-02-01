# -*- coding: utf-8 -*-
import sys
from getpass import getuser 
from socket import gethostbyname
from argparse import ArgumentParser
from os import path, listdir, environ
from . import messages
from .utils import normalpath, natsort, p
from .readspec import readspec, Bunch

info = Bunch({})
jobspecs = Bunch({})
options = Bunch({})
jobcomments = []
environment = []
commandline = []
keywords = {}
files = []

def parse():

    info.user = getuser()
    info.homedir = path.expanduser('~')
    info.alias = path.basename(sys.argv[0])
    
    try: info.specdir = normalpath(environ['SPECPATH'])
    except KeyError:
        messages.cfgerror('No se pueden enviar trabajos porque no se definió la variable de entorno $SPECPATH')
    
    hostspec = path.join(info.specdir, 'hostspec.json')
    corespec = path.join(info.specdir, 'corespec.json')
    pathspec = path.join(info.specdir, 'pathspec.json')
    userspec = path.join(info.homedir, '.jobspec.json')
    
    jobspecs.merge(readspec(hostspec))
    jobspecs.merge(readspec(corespec))
    jobspecs.merge(readspec(pathspec))
    
    if path.isfile(userspec):
        jobspecs.merge(readspec(userspec))
    
    try: info.master = path.expandvars(jobspecs.hostname)
    except AttributeError:
        messages.cfgerror('No se definió el valor de "hostname" en la configuración')
    
    if 'REMOTECLIENT' in environ:
        if 'REMOTESHARE' in environ:
            info.clientdir = normalpath(environ['REMOTESHARE'], environ['REMOTECLIENT'])
        else:
            messages.cfgerror('No se pueden aceptar trabajos remotos porque no se definió la variable de entorno $REMOTESHARE')
    
    parser = ArgumentParser(prog=info.alias, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
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
    parser.add_argument('--no', dest='no', action='store_true', default=False, help='Responder "no" a todas las preguntas.')
    parser.add_argument('--move', action='store_true', help='Mover los archivos de entrada a la carpeta de salida en vez de copiarlos.')
    parser.add_argument('--outdir', metavar='OUTDIR', type=str, help='Cambiar el directorio de salida.')
    parser.add_argument('--scrdir', metavar='SCRATCHDIR', type=str, help='Cambiar el directorio de escritura.')
    parser.add_argument('--node', metavar='NODENAME', type=str, help='Solicitar un nodo específico de ejecución.')
    
    if len(jobspecs.parameters) == 1:
        parser.add_argument('-p', metavar='SETNAME', type=str, dest=list(jobspecs.parameters)[0], help='Nombre del conjunto de parámetros.')
    for key in jobspecs.parameters:
        parser.add_argument('--' + key, metavar='SETNAME', type=str, dest=key, help='Nombre del conjunto de parámetros.')
    for key in jobspecs.keywords:
        parser.add_argument('--' + key, metavar='VALUE', type=str, dest=key, help='Valor de la variable de interpolación.')
    
    parsed, remaining = parser.parse_known_args()
    options.update(vars(parsed))
    
    if options.lsopt:
        if jobspecs.versions:
            messages.listing('Versiones del ejecutable disponibles:', items=sorted(jobspecs.versions, key=natsort), default=jobspecs.defaults.version)
        for key in jobspecs.parameters:
            messages.listing('Conjuntos de parámetros disponibles', p(key), items=sorted(listdir(jobspecs.parameters[key]), key=natsort), default=jobspecs.defaults.parameters[key])
        if jobspecs.keywords:
            messages.listing('Variables de interpolación disponibles:', items=sorted(jobspecs.keywords, key=natsort))
        raise SystemExit()
    
    parser.add_argument('-R', '--remote', metavar='HOSTNAME', type=str, help='Ejecutar el trabajo remotamente en HOSTNAME.')
    parsed, remaining = parser.parse_known_args()
    info.remote = parsed.remote

    parser.add_argument('files', nargs='+', metavar='FILE(S)', type=str, help='Rutas de los archivos de entrada.')
    files[:] = parser.parse_args(remaining).files

    for key in jobspecs.keywords:
        if key in options:
            keywords[key] = options[key]


