# -*- coding: utf-8 -*-
import os
import sys
from time import sleep
from socket import gethostname
from argparse import ArgumentParser, Action, SUPPRESS
from . import messages
from .readspec import readspec
from .utils import Bunch, templatekeys, printoptions, o, p, q, _
from .fileutils import AbsPath, pathjoin, dirbranches
from .shared import ArgList, names, paths, environ, clusterconf, packageconf, progspecs, options, remoteargs
from .submit import initialize, submit 

class ListOptions(Action):
    def __init__(self, **kwargs):
        super().__init__(nargs=0, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        if packageconf.versions:
            print(_('Versiones del programa:'))
            default = packageconf.defaults.version if 'version' in packageconf.defaults else None
            printoptions(tuple(packageconf.versions.keys()), [default], level=1)
        for path in packageconf.defaults.parameterpaths:
            dirtree = {}
            parts = AbsPath(pathjoin(path, keys=names)).parts
            dirbranches(AbsPath(parts.pop(0)), parts, dirtree)
            defaults = [packageconf.defaults.parameters.get(i, None) for i in templatekeys(path)]
            if dirtree:
                print(_('Conjuntos de parámetros:'))
                printoptions(dirtree, defaults, level=1)
        sys.exit()

class StorePath(Action):
    def __init__(self, **kwargs):
        super().__init__(nargs=1, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, AbsPath(values[0], cwd=os.getcwd()))

#TODO How to append value to list?
class AppendPath(Action):
    def __init__(self, **kwargs):
        super().__init__(nargs=1, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, AbsPath(values[0], cwd=os.getcwd()))

try:

    try:
        paths.specdir = os.environ['SPECDIR']
    except KeyError:
        messages.error('No se definió la variable de entorno SPECDIR')
    
    parser = ArgumentParser(add_help=False)
    parser.add_argument('program', metavar='PROGNAME', help='Nombre estandarizado del programa.')
    parsedargs, remainingargs = parser.parse_known_args()
    names.program = parsedargs.program
    
    clusterconf.merge(readspec(pathjoin(paths.specdir, 'clusterconf.json')))
    clusterconf.merge(readspec(pathjoin(paths.specdir, 'queuespec.json')))

    packageconf.merge(readspec(pathjoin(paths.specdir, names.program, 'packageconf.json')))
    progspecs.merge(readspec(pathjoin(paths.specdir, names.program, 'progspec.json')))
    
    userconfdir = pathjoin(paths.home, '.jobspecs')
    userclusterconf = pathjoin(userconfdir, 'clusterconf.json')
    userpackageconf = pathjoin(userconfdir, names.program, 'packageconf.json')
    
    if os.path.isfile(userclusterconf):
        clusterconf.merge(readspec(usersclusterconf))

    if os.path.isfile(userpackageconf):
        progspecs.merge(readspec(userpackageconf))
    
    try:
        names.cluster = clusterconf.name
    except AttributeError:
        messages.error('No se definió el nombre del clúster', spec='name')

    try:
        names.head = clusterconf.head
    except AttributeError:
        names.head = names.host

    parser = ArgumentParser(prog=names.program, add_help=False, description='Envía trabajos de {} a la cola de ejecución.'.format(progspecs.longname))

    group1 = parser.add_argument_group('Argumentos')
    group1.add_argument('files', nargs='*', metavar='FILE', help='Rutas de los archivos de entrada.')
    group1.name = 'arguments'
    group1.remote = False

#    group1 = parser.add_argument_group('Ejecución remota')

    group2 = parser.add_argument_group('Opciones comunes')
    group2.name = 'common'
    group2.remote = True
    group2.add_argument('-d', '--defaults', action='store_true', help='Ignorar las opciones predeterminadas y preguntar.')
    group2.add_argument('-f', '--filter', metavar='REGEX', default=SUPPRESS, help='Enviar únicamente los trabajos que coinciden con la expresión regular.')
    group2.add_argument('-j', '--jobargs', action='store_true', help='Interpretar los argumentos como nombres de trabajos en vez de rutas de archivo.')
    group2.add_argument('-l', '--list', action=ListOptions, default=SUPPRESS, help='Mostrar las opciones disponibles y salir.')
    group2.add_argument('-n', '--nproc', type=int, metavar='#PROCS', default=1, help='Número de núcleos de procesador requeridos.')
    group2.add_argument('-q', '--queue', metavar='QUEUENAME', default=SUPPRESS, help='Nombre de la cola requerida.')
    group2.add_argument('-s', '--sort', metavar='ORDER', default=SUPPRESS, help='Ordenar los argumentos de acuerdo al orden ORDER.')
    group2.add_argument('-v', '--version', metavar='PROGVERSION', default=SUPPRESS, help='Versión del ejecutable.')
    group2.add_argument('-w', '--wait', type=float, metavar='TIME', default=SUPPRESS, help='Tiempo de pausa (en segundos) después de cada ejecución.')
#    group2.add_argument('-p', '--path', action=AppendPath, metavar='PATH', default=[], help='Agregar la ruta PATH para buscar los conjunto de parámetros.')
    group2.add_argument('--cwd', action=StorePath, metavar='PATH', default=os.getcwd(), help='Establecer PATH como el directorio actual para rutas relativas.')
    group2.add_argument('--out', action=StorePath, metavar='PATH', default=SUPPRESS, help='Escribir los archivos de salida en el directorio PATH.')
    group2.add_argument('--raw', action='store_true', help='No interpolar ni crear copias de los archivos de entrada.')
    group2.add_argument('--dispose', action='store_true', help='Borrar los archivos de entrada del directorio intermedio tras enviar el trabajo.')
    group2.add_argument('--scratch', action=StorePath, metavar='PATH', default=SUPPRESS, help='Escribir los archivos temporales en el directorio PATH.')
    hostgroup = group2.add_mutually_exclusive_group()
    hostgroup.add_argument('-N', '--nodes', type=int, metavar='#NODES', default=SUPPRESS, help='Número de nodos de ejecución requeridos.')
    hostgroup.add_argument('--nodelist', metavar='NODE', default=SUPPRESS, help='Solicitar nodos específicos de ejecución.')
    yngroup = group2.add_mutually_exclusive_group()
    yngroup.add_argument('--yes', '--si', action='store_true', help='Responder "si" a todas las preguntas.')
    yngroup.add_argument('--no', action='store_true', help='Responder "no" a todas las preguntas.')
#    group2.add_argument('-X', '--xdialog', action='store_true', help='Habilitar el modo gráfico para los mensajes y diálogos.')
#    group2.add_argument('--delete', action='store_true', help='Borrar los archivos de entrada después de enviar el trabajo.')

    group3 = parser.add_argument_group('Opciones remotas')
    group3.name = 'remote'
    group3.remote = False 
    group3.add_argument('-H', '--host', metavar='HOSTNAME', help='Procesar el trabajo en el host HOSTNAME.')

    group4 = parser.add_argument_group('Conjuntos de parámetros')
    group4.name = 'parameters'
    group4.remote = True
    for key in progspecs.parameters:
        group4.add_argument(o(key), metavar='PARAMETERSET', default=SUPPRESS, help='Nombre del conjunto de parámetros.')

    group5 = parser.add_argument_group('Opciones de interpolación')
    group5.name = 'interpolation'
    group5.remote = False
#    group5.add_argument('-i', '--interpolate', action='store_true', help='Interpolar los archivos de entrada.')
    group5.add_argument('-x', '--var', dest='vars', metavar='VALUE', action='append', default=[], help='Variables posicionales de interpolación.')
    molgroup = group5.add_mutually_exclusive_group()
    molgroup.add_argument('-m', '--mol', metavar='MOLFILE', action='append', default=[], help='Incluir el último paso del archivo MOLFILE en las variables de interpolación.')
    molgroup.add_argument('-M', '--trjmol', metavar='MOLFILE', default=SUPPRESS, help='Incluir todos los pasos del archivo MOLFILE en las variables de interpolación.')
    group5.add_argument('--prefix', metavar='PREFIX', default=SUPPRESS, help='Agregar el prefijo PREFIX al nombre del trabajo.')
    group5.add_argument('--suffix', metavar='SUFFIX', default=SUPPRESS, help='Agregar el sufijo SUFFIX al nombre del trabajo.')

    group6 = parser.add_argument_group('Archivos reutilizables')
    group6.name = 'targetfiles'
    group6.remote = False
    for key, value in progspecs.fileoptions.items():
        group6.add_argument(o(key), action=StorePath, metavar='FILEPATH', default=SUPPRESS, help='Ruta al archivo {}.'.format(value))

    group7 = parser.add_argument_group('Opciones de depuración')
    group7.name = 'debug'
    group7.remote = False
    group7.add_argument('--dryrun', action='store_true', help='Procesar los archivos de entrada sin enviar el trabajo.')

    parsedargs = parser.parse_args(remainingargs)
#    print(parsedargs)

    for group in parser._action_groups:
        group_dict = {a.dest:getattr(parsedargs, a.dest) for a in group._group_actions if a.dest in parsedargs}
        if hasattr(group, 'name'):
            options[group.name] = Bunch(**group_dict)
        if hasattr(group, 'remote') and group.remote:
            remoteargs.gather(Bunch(**group_dict))

#    print(options)
#    print(remoteargs)

    if parsedargs.files:
        arguments = ArgList(parsedargs.files)
    else:
        messages.error('Debe especificar al menos un archivo de entrada')

    try:
        environ.TELEGRAM_BOT_URL = os.environ['TELEGRAM_BOT_URL']
        environ.TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    except KeyError:
        pass

    initialize()

    try:
        parentdir, inputname = next(arguments)
    except StopIteration:
        sys.exit()

    submit(parentdir, inputname)
    for parentdir, inputname in arguments:
        sleep(options.common.wait)
        submit(parentdir, inputname)
    
except KeyboardInterrupt:

    messages.error('Interrumpido por el usuario')

