# -*- coding: utf-8 -*-
import sys
from pwd import getpwnam
from grp import getgrgid
from getpass import getuser 
from socket import gethostname, gethostbyname
from os import path, listdir, environ, getcwd
from argparse import ArgumentParser, SUPPRESS
from . import messages
from .specparse import SpecBunch, readspec
from .fileutils import AbsPath, NotAbsolutePath
from .utils import Bunch, natsort, p
from .chemistry import readxyz

def readmol():

    if run.molfile:
        try:
            molfile = AbsPath(run.molfile)
        except NotAbsolutePath:
            molfile = AbsPath(getcwd(), run.molfile)
        if molfile.isfile():
            if molfile.hasext('.xyz'):
                for i, step in enumerate(readxyz(molfile), 1):
                    keywords['mol' + str(i)] = '\n'.join('{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format(*atom) for atom in step['coords'])
            else:
                messages.opterror('Solamente están soportados archivos de coordenadas en formato xyz')
        elif molfile.isdir():
            messages.opterror('El archivo de coordenadas', molfile, 'es un directorio')
        elif molfile.exists():
            messages.opterror('El archivo de coordenadas', molfile, 'no es un archivo regular')
        else:
            messages.opterror('El archivo de coordenadas', molfile, 'no existe')
        keywords['molfile'] = molfile
        run.molname = molfile.stem
    elif run.molname:
        keywords['molname'] = run.molname
    else:
        messages.opterror('Debe especificar el archivo de coordenadas o un nombre para interpolar el archivo de entrada')

def listchoices():
    if jobspecs.versions:
        messages.listing('Versiones disponibles del ejecutable:', items=sorted(jobspecs.versions, key=natsort), default=jobspecs.defaults.version)
    for parkey in jobspecs.parameters:
        if parkey in jobspecs.defaults.parameters:
            print('Conjuntos disponibles de parámetros', p(parkey) + ':')
            try:
                abspath = AbsPath(jobspecs.defaults.parameters[parkey])
            except NotAbsolutePath:
                abspath = AbsPath(getcwd(), jobspecs.defaults.parameters[parkey])
            choices = list(abspath.setkeys(user).splitkeys())
            listdir(AbsPath('/'), choices, len(choices))
    if jobspecs.keywords:
        messages.listing('Variables disponibles de interpolación:', items=sorted(jobspecs.keywords, key=natsort))

def listdir(rootpath, choices, depth):
    part, key, default = choices[0]
    if key is None:
        rootpath = rootpath.joinpath(part)
    else:
        rootpath = rootpath.joinpath(part)
        try:
            diritems = rootpath.listdir()
        except FileNotFoundError:
            messages.cfgerror('El directorio', self, 'no existe')
        except NotADirectoryError:
            messages.cfgerror('La ruta', self, 'no es un directorio')
        if not diritems:
            messages.cfgerror('El directorio', self, 'está vacío')
        diritems.sort(key=natsort)
        for item in diritems:
            if default and item == default:
                print(' '*2*(depth - len(choices) + 1) + item + ' (default)')
            else:
                print(' '*2*(depth - len(choices) + 1) + item)
            rootpath = rootpath.joinpath(item)
            if choices[1:]: listdir(rootpath, choices[1:], depth)

def jobparse():

    try:
        specdir = AbsPath(environ['SPECPATH'])
    except KeyError:
        messages.cfgerror('No se pueden enviar trabajos porque no se definió la variable de entorno $SPECPATH')
    except NotAbsolutePath:
        specdir = AbsPath(getcwd(), environ['SPECPATH'])
    
    user.user = getuser()
    user.home = path.expanduser('~')
    user.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
    run.program = path.basename(sys.argv[0])
    
    try:
        envars.TELEGRAM_BOT_URL = environ['TELEGRAM_BOT_URL']
        envars.TELEGRAM_CHAT_ID = environ['TELEGRAM_CHAT_ID']
    except KeyError:
        pass

    hostspec = path.join(specdir, 'hostspec.json')
    corespec = path.join(specdir, 'corespec.json')
    pathspec = path.join(specdir, 'pathspec.json')
    userspec = path.join(user.home, '.jobspec.json')
    
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

    parser = ArgumentParser(prog=run.program, add_help=False, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')

    parser.add_argument('-l', '--list', action='store_true', help='Mostrar las opciones disponibles y salir.')
    parsed, remaining = parser.parse_known_args()

    if parsed.list:
        listchoices()
        raise SystemExit()

    parser.add_argument('-v', '--version', metavar='PROGVERSION', help='Versión del ejecutable.')
    parser.add_argument('-q', '--queue', metavar='QUEUENAME', help='Nombre de la cola requerida.')
    parser.add_argument('-n', '--ncore', type=int, default=1, metavar='#CORES', help='Número de núcleos de cpu requeridos.')
    parser.add_argument('-N', '--nhost', type=int, default=1, metavar='#HOSTS', help='Número de nodos de ejecución requeridos.')
    parser.add_argument('-j', '--jobname', metavar='JOBNAME', help='Cambiar el nombre del trabajo por JOBNAME.')
    parser.add_argument('-w', '--wait', type=float, metavar='TIME', help='Tiempo de pausa (en segundos) después de cada ejecución.')
    parser.add_argument('-X', '--xdialog', action='store_true', help='Habilitar el modo gráfico para los mensajes y diálogos.')
    parser.add_argument('-I', '--ignore-defaults', action='store_true', help='Ignorar todas las opciones por defecto.')
    parser.add_argument('--node', metavar='NODENAME', help='Solicitar un nodo específico de ejecución.')
    parser.add_argument('--move', action='store_true', help='Mover los archivos de entrada a la carpeta de salida en vez de copiarlos.')
    parser.add_argument('--outdir', metavar='OUTPUTDIR', help='Usar OUTPUTDIR com directorio de salida.')
    parser.add_argument('--scrdir', metavar='SCRATCHDIR', help='Usar SCRATCHDIR como directorio de escritura.')

    sgroup = parser.add_mutually_exclusive_group()
    sgroup.add_argument('-s', '--sort', action='store_true', help='Ordenar los argumentos numéricamente de menor a mayor')
    sgroup.add_argument('-S', '--sort-reverse', action='store_true', help='Ordenar los argumentos numéricamente de mayor a menor')

    yngroup = parser.add_mutually_exclusive_group()
    yngroup.add_argument('--si', '--yes', dest='yes', action='store_true', default=False, help='Responder "si" a todas las preguntas.')
    yngroup.add_argument('--no', dest='no', action='store_true', default=False, help='Responder "no" a todas las preguntas.')

    if len(jobspecs.parameters) == 1:
        key = jobspecs.parameters[0]
        parser.add_argument('-p', '--' + key + '-set', metavar='PARAMSET', help='Nombre del conjunto de parámetros.')
        parser.add_argument('-P', '--' + key + '-path', metavar='PARAMPATH', help='Ruta del directorio de parámetros.')
    else:
        for key in jobspecs.parameters:
            parser.add_argument('--' + key + '-set', metavar='PARAMSET', help='Nombre del conjunto de parámetros.')
            parser.add_argument('--' + key + '-path', metavar='PARAMPATH', help='Ruta del directorio de parámetros.')

    # Convert to dict and remove options with None value
    parsed, remaining = parser.parse_known_args(remaining)
    options.update(vars(parsed))

    rgroup = parser.add_mutually_exclusive_group()
    rgroup.add_argument('-d', '--dry-run', dest='dry', action='store_true', help='Procesar los archivos de entrada sin enviar el trabajo.')
    rgroup.add_argument('-r', '--remote-run', dest='remote', metavar='HOSTNAME', help='Ejecutar el trabajo en el host remoto HOSTNAME.')

    mgroup = parser.add_mutually_exclusive_group()
    mgroup.add_argument('-m', '--molfile', metavar='MOLFILE', help='Ruta del archivo de coordenadas para la interpolación.')
    mgroup.add_argument('-M', '--molname', metavar='MOLNAME', help='Nombre de los archivos de interpolación.')

    parser.add_argument('-i', '--interpolate', action='store_true', help='Interpolar los archivos de entrada.')

    for key in jobspecs.keywords:
        parser.add_argument('--' + key, metavar=key.upper(), dest=key, help='Valor de la variable {}'.format(key.upper()))
    
    parser.add_argument('files', nargs='*', metavar='FILE(S)', help='Rutas de los archivos de entrada.')
    parser.add_argument('-h', '--help', action='help', help='Mostrar este mensaje de ayuda y salir')

    # Convert to dict and remove options with None value
    parsed = parser.parse_args(remaining)
    run.update(vars(parsed))

    if not run.files:
        messages.opterror('Debe especificar al menos un archivo de entrada')

    if run.remote:
        run.userathost = '{user}@{host}'.format(user=user.user, host=cluster.name.lower())
        run.jobshare = '$JOBSHARE'

    for key in jobspecs.keywords:
        if run[key]:
            keywords[key] = run[key]

    if run.interpolate:
        readmol()
    elif run.molfile or run.molname:
        messages.opterror('Se especificó un nombre o archivo de coordenadas sin interpolar los archivos de entrada')
        

run = Bunch()
user = Bunch()
cluster = Bunch()
options = Bunch()
envars = Bunch()
jobspecs = SpecBunch()
keywords = {}

