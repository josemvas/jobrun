# -*- coding: utf-8 -*-
import sys
from os import path, listdir, environ, getcwd
from argparse import ArgumentParser, SUPPRESS
from . import messages
from .utils import p
from .specparse import readspec
from .bunches import sysinfo, envars, jobspecs, options, argfiles
from .jobutils import printchoices, findparameters
from .fileutils import AbsPath, NotAbsolutePath
from .submit import setup, submit

parser = ArgumentParser(add_help=False)
parser.add_argument('--specdir', metavar='SPECDIR', help='Ruta al directorio de especificaciones del programa.')
parser.add_argument('--program', metavar='PROGNAME', help='Nombre estandarizado del programa.')
parsed, remaining = parser.parse_known_args()
globals().update(vars(parsed))

try:
    envars.TELEGRAM_CHAT_ID = environ['TELEGRAM_CHAT_ID']
except KeyError:
    pass

jobspecs.merge(readspec(path.join(specdir, program, 'hostspec.json')))
jobspecs.merge(readspec(path.join(specdir, program, 'queuespec.json')))
jobspecs.merge(readspec(path.join(specdir, program, 'progspec.json')))
jobspecs.merge(readspec(path.join(specdir, program, 'hostprogspec.json')))

userspecdir = path.join(sysinfo.userhome, '.jobspecs', program + '.json')

if path.isfile(userspecdir):
    jobspecs.merge(readspec(userspecdir))

try: sysinfo.clustername = jobspecs.clustername
except AttributeError:
    messages.error('No se definió el nombre del clúster', spec='clustername')

try: sysinfo.clusterhead = jobspecs.headname.format(**sysinfo)
except AttributeError:
    messages.error('No se definió el nombre del nodo maestro', spec='headname')

parser = ArgumentParser(prog=program, add_help=True, description='Ejecuta trabajos de {} en el sistema de colas del clúster.'.format(jobspecs.progname))
parser.add_argument('-l', '--list', dest='lsopt', action='store_true', help='Mostrar las opciones disponibles y salir.')
parser.add_argument('-H', '--host', dest='remotehost', metavar='HOSTNAME', help='Procesar los archivos de entrada y enviar el trabajo al host remoto HOSTNAME.')
parsed, remaining = parser.parse_known_args(remaining)
globals().update(vars(parsed))

#TODO: Set default=SUPPRESS for all options
parser.add_argument('-v', '--version', metavar='PROGVERSION', help='Versión del ejecutable.')
parser.add_argument('-q', '--queue', metavar='QUEUENAME', help='Nombre de la cola requerida.')
parser.add_argument('-n', '--nproc', type=int, metavar='#PROCS', help='Número de núcleos de procesador requeridos.')
parser.add_argument('-N', '--nhost', type=int, metavar='#HOSTS', help='Número de nodos de ejecución requeridos.')
parser.add_argument('-w', '--wait', type=float, metavar='TIME', help='Tiempo de pausa (en segundos) después de cada ejecución.')
parser.add_argument('-f', '--filter', metavar='REGEX', help='Enviar únicamente los trabajos que coinciden con la expresión regular.')
parser.add_argument('-X', '--xdialog', action='store_true', help='Habilitar el modo gráfico para los mensajes y diálogos.')
parser.add_argument('-I', '--ignore-defaults', dest='ignore-defaults', action='store_true', help='Ignorar todas las opciones por defecto.')
parser.add_argument('-i', '--interpolate', action='store_true', help='Interpolar los archivos de entrada.')
parser.add_argument('-m', '--mol', dest='molfile', metavar='MOLFILE', help='Ruta del archivo de coordenadas para la interpolación.')
parser.add_argument('-b', '--base', action='store_true', help='Interpretar el argumento como el nombre del trabajo (no como un archivo de entrada).')
parser.add_argument('--delete', action='store_true', help='Borrar los archivos de entrada después de enviar el trabajo.')
parser.add_argument('--nodes', metavar='NODENAME', help='Solicitar nodos específicos de ejecución por nombre.')
parser.add_argument('--outdir', metavar='OUTPUTDIR', help='Usar OUTPUTDIR com directorio de salida.')
parser.add_argument('--writedir', metavar='WRITEDIR', help='Usar WRITEDIR como directorio de escritura.')
parser.add_argument('--prefix', metavar='PREFIX', action='append', help='Agregar el prefijo PREFIX al nombre del trabajo.')
parser.add_argument('--suffix', metavar='SUFFIX', action='append', help='Agregar el sufijo SUFFIX al nombre del trabajo.')
parser.add_argument('--dry', action='store_true', help='Procesar los archivos de entrada sin enviar el trabajo.')

sortgroup = parser.add_mutually_exclusive_group()
sortgroup.add_argument('-s', '--sort', action='store_true', help='Ordenar los argumentos numéricamente de menor a mayor.')
sortgroup.add_argument('-S', '--sort-reverse', dest='sort-reverse', action='store_true', help='Ordenar los argumentos numéricamente de mayor a menor.')

yngroup = parser.add_mutually_exclusive_group()
yngroup.add_argument('--yes', '--si', action='store_true', default=False, help='Responder "si" a todas las preguntas.')
yngroup.add_argument('--no', action='store_true', default=False, help='Responder "no" a todas las preguntas.')

options.common, remaining = parser.parse_known_args(remaining)
#print(options.common)

for key in jobspecs.parametersets:
    parser.add_argument('--' + key, dest=key, metavar='PARAMSET', default=SUPPRESS, help='Nombre del conjunto de parámetros.')

options.parametersets, remaining = parser.parse_known_args(remaining)

for key in jobspecs.parametersets:
    parser.add_argument('--' + key + '-path', dest=key+'-path', metavar='PARAMPATH', default=SUPPRESS, help='Ruta del directorio de parámetros.')

options.parameterpaths, remaining = parser.parse_known_args(remaining)

for key, value in jobspecs.fileopts.items():
    parser.add_argument('--' + key, dest=key, metavar='FILEPATH', default=SUPPRESS, help='Ruta del archivo {}.'.format(value))

options.files, remaining = parser.parse_known_args(remaining)

for key in jobspecs.keywords:
    parser.add_argument('--'+key, metavar=key.upper(), default=SUPPRESS, help='Valor de la variable {}.'.format(key.upper()))

options.keywords, remaining = parser.parse_known_args(remaining)
print(options.common)
print(options.files)
print(options.keywords)

parser.add_argument('argfiles', nargs='*', metavar='FILE(S)', help='Rutas de los archivos de entrada.')
#parser.add_argument('-h', '--help', action='help', help='Mostrar este mensaje de ayuda y salir.')
argfiles.extend(parser.parse_args(remaining).argfiles)

if not argfiles:
    messages.error('Debe especificar al menos un archivo de entrada')

if lsopt:
    if jobspecs.versions:
        print('Versiones del programa')
        printchoices(choices=jobspecs.versions, default=jobspecs.defaults.version)
    for key in jobspecs.parametersets:
        if key in jobspecs.defaults.parameterpath:
            if 'parameterset' in jobspecs.defaults and key in jobspecs.defaults.parameterset:
                if isinstance(jobspecs.defaults.parameterset[key], (list, tuple)):
                    defaults = jobspecs.defaults.parameterset[key]
                else:
                    messages.error('La clave', key, 'no es una lista', spec='defaults.parameterset')
            else:
                defaults = []
            print('Conjuntos de parámetros', p(key))
            pathcomponents = AbsPath(jobspecs.defaults.parameterpath[key], cwdir=getcwd()).setkeys(sysinfo).populate()
            findparameters(AbsPath(next(pathcomponents)), pathcomponents, defaults, 1)
    if jobspecs.keywords:
        print('Variables de interpolación')
        printchoices(choices=jobspecs.keywords)

elif remotehost:
    sysinfo.remoteshare = check_output(['ssh', options.remotehost, 'echo $JOBSHARE']).decode(sys.stdout.encoding).strip()
    if not sysinfo.remoteshare:
        messages.error('El servidor remoto no acepta trabajos de otro servidor')
    while argfiles:
        try:
            parentdir, basename = popfile()
        except NonMatchingFile:
            break
        except InputFileError as e:
            messages.failure(e)
            break
        transferlist = []
        relparentdir = path.relpath(parentdir, sysinfo.userhome)
        userhost = sysinfo.username + '@' + sysinfo.hostname
        remotefiles.append(buildpath(sysinfo.remoteshare, userhost, relparentdir, (basename, extension)))
        for key in jobspecs.filekeys:
            if path.isfile(buildpath(parentdir, (basename, key))):
                transferlist.append(buildpath(sysinfo.userhome, '.', relparentdir, (basename, key)))
        call(['rsync', '-qRLtz'] + transferlist + [options.remotehost + ':' + buildpath(sysinfo.remoteshare, userhost)])
    if remotefiles:
        execv('/usr/bin/ssh', [__file__, '-qt', options.remotehost] + ['{}={}'.format(envar, value) for envar, value in envars.items()] + [options.program] + ['--{}'.format(option) if value is True else '--{}={}'.format(option, value) for option, value in vars(options.common).items() if value] + ['--delete'] + remotefiles)

else:
    setup()
    submit()
    while argfiles:
        sleep(options.common.wait)
        submit()

