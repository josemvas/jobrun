# -*- coding: utf-8 -*-
import sys
from os import path, listdir, environ, getcwd, execv
from argparse import ArgumentParser, Action, SUPPRESS
from subprocess import call, Popen, PIPE, check_output, CalledProcessError
from . import messages
from .utils import o, p, q, Bunch
from .specparse import readspec
from .bunches import sysinfo, envars, jobspecs, options
from .jobutils import printchoices, findparameters
from .fileutils import AbsPath, NotAbsolutePath, buildpath
from .submit import setup, submit, popfile

class LsOptions(Action):
    def __init__(self, nargs=0, **kwargs):
        super().__init__(nargs=nargs, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        if jobspecs.versions:
            print('Versiones del programa')
            printchoices(choices=jobspecs.versions, default=jobspecs.defaults.version)
        for key in jobspecs.parameters:
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
        raise SystemExit()

try:

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
    
    userspecdir = path.join(sysinfo.home, '.jobspecs', program + '.json')
    
    if path.isfile(userspecdir):
        jobspecs.merge(readspec(userspecdir))
    
    try: sysinfo.clustername = jobspecs.clustername
    except AttributeError:
        messages.error('No se definió el nombre del clúster', spec='clustername')

    try: sysinfo.headname = jobspecs.headname.format(**sysinfo)
    except AttributeError:
        messages.error('No se definió el nombre del nodo maestro', spec='headname')

    parser = ArgumentParser(prog=program, add_help=False, description='Envía trabajos de {} a la cola de ejecución.'.format(jobspecs.progname))

    group1 = parser.add_argument_group('common')
    group1.add_argument('-h', '--help', action='help', help='Mostrar este mensaje de ayuda y salir.')
    group1.add_argument('-l', '--list', action=LsOptions, default=SUPPRESS, help='Mostrar las opciones disponibles y salir.')
    group1.add_argument('-H', '--host', metavar='HOSTNAME', default=SUPPRESS, help='Procesar el trabajo en el host HOSTNAME.')
    group1.add_argument('-v', '--version', metavar='PROGVERSION', default=SUPPRESS, help='Versión del ejecutable.')
    group1.add_argument('-q', '--queue', metavar='QUEUENAME', default=SUPPRESS, help='Nombre de la cola requerida.')
    group1.add_argument('-n', '--nproc', type=int, metavar='#PROCS', default=SUPPRESS, help='Número de núcleos de procesador requeridos.')
    group1.add_argument('-N', '--nhost', type=int, metavar='#HOSTS', default=SUPPRESS, help='Número de nodos de ejecución requeridos.')
    group1.add_argument('-w', '--wait', type=float, metavar='TIME', default=SUPPRESS, help='Tiempo de pausa (en segundos) después de cada ejecución.')
    group1.add_argument('-f', '--filter', metavar='REGEX', default=SUPPRESS, help='Enviar únicamente los trabajos que coinciden con la expresión regular.')
    group1.add_argument('-m', '--mol', dest='molfile', metavar='MOLFILE', default=SUPPRESS, help='Ruta del archivo de coordenadas para la interpolación.')
    group1.add_argument('--nodes', metavar='NODENAME', default=SUPPRESS, help='Solicitar nodos específicos de ejecución por nombre.')
    group1.add_argument('--outdir', metavar='OUTPUTDIR', default=SUPPRESS, help='Usar OUTPUTDIR com directorio de salida.')
    group1.add_argument('--writedir', metavar='WRITEDIR', default=SUPPRESS, help='Usar WRITEDIR como directorio de escritura.')
    group1.add_argument('--suffix', metavar='SUFFIX', default=SUPPRESS, help='Agregar el sufijo SUFFIX al nombre del trabajo.')
    group1.add_argument('-d', '--ignore-defaults', action='store_true', help='Ignorar las opciones por defecto.')
    group1.add_argument('-i', '--interpolate', action='store_true', help='Interpolar los archivos de entrada.')
    group1.add_argument('-X', '--xdialog', action='store_true', help='Habilitar el modo gráfico para los mensajes y diálogos.')
    group1.add_argument('-b', '--bare', action='store_true', help='Interpretar los argumentos como nombres de trabajos.')
    group1.add_argument('--delete', action='store_true', help='Borrar los archivos de entrada después de enviar el trabajo.')
    group1.add_argument('--dry', action='store_true', help='Procesar los archivos de entrada sin enviar el trabajo.')
    
    sortgroup = group1.add_mutually_exclusive_group()
    sortgroup.add_argument('-s', '--sort', action='store_true', help='Ordenar los argumentos de menor a mayor.')
    sortgroup.add_argument('-S', '--sort-reverse', action='store_true', help='Ordenar los argumentos de mayor a menor.')
    
    yngroup = group1.add_mutually_exclusive_group()
    yngroup.add_argument('--yes', '--si', action='store_true', help='Responder "si" a todas las preguntas.')
    yngroup.add_argument('--no', action='store_true', help='Responder "no" a todas las preguntas.')
    
    group2 = parser.add_argument_group('parameters')
    for key in jobspecs.parameters:
        group2.add_argument('--' + key, metavar='PARAMETERSET', default=SUPPRESS, help='Nombre del conjunto de parámetros.')
    
    group3 = parser.add_argument_group('fileopts')
    for key, value in jobspecs.fileopts.items():
        group3.add_argument('--' + key, metavar='FILEPATH', default=SUPPRESS, help='Ruta del archivo {}.'.format(value))
    
    group4 = parser.add_argument_group('keywords')
    for key in jobspecs.keywords:
        group4.add_argument('--' + key, metavar=key.upper(), default=SUPPRESS, help='Valor de la variable {}.'.format(key.upper()))
    
    parser.add_argument('fileargs', nargs='*', metavar='FILE', help='Ruta del archivo de entrada.')

    parsed = parser.parse_args(remaining)
    print(parsed)

    if parsed.fileargs:
        options.fileargs = parsed.fileargs
    else:
        messages.error('Debe especificar al menos un archivo de entrada')

    for group in parser._action_groups:
        group_dict = {a.dest:getattr(parsed, a.dest) for a in group._group_actions if a.dest in parsed}
        setattr(options, group.title, Bunch(**group_dict))
    
    for key in options.fileopts:
        options.fileopts[key] = AbsPath(options.fileopts[key], cwdir=getcwd())
        if not options.fileopts[key].isfile():
            messages.error('El archivo de entrada', options.fileopts[key], 'no existe', option=o(key))

    if options.common.host:

        filelist = []
        remotejobs = []
        remotehost = options.common.host
        remoteshare = '/test'
#        #remoteshare = check_output(['ssh', remotehost, 'echo $JOBSHARE']).decode(sys.stdout.encoding).strip()
#        process = Popen(['ssh', remotehost, 'echo $JOBSHARE'], stdout=PIPE, stderr=PIPE, close_fds=True)
#        output, error = process.communicate()
#        remoteshare = output.decode(sys.stdout.encoding).strip()
#        error = error.decode(sys.stdout.encoding).strip()
#        if process.returncode != 0:
#            messages.error(error)
#        if not remoteshare:
#            messages.error('El servidor remoto no acepta trabajos de otro servidor')
#        options.appendto(filelist, 'molfile')
#        options.appendto(filelist, 'fileopts')
#        filelist.append(options.common.molfile)
#        filelist.extend(options.fileopts)
        print(options.fileargs)
        while options.fileargs:
            try:
                parentdir, basename = popfile()
            except InputFileException as e:
                if e: messages.failure(e)
                break
            relparentdir = path.relpath(parentdir, sysinfo.home)
            userhost = sysinfo.user + '@' + sysinfo.hostname
            remotejobs.append(buildpath(remoteshare, userhost, relparentdir, basename))
            for key in jobspecs.filekeys:
                if path.isfile(buildpath(parentdir, (basename, key))):
                    filelist.append(buildpath(sysinfo.home, '.', relparentdir, (basename, key)))
        if remotejobs:
#            call(['rsync', '-qRLtz'] + filelist + [remotehost + ':' + buildpath(remoteshare, userhost)])
#            execv('/usr/bin/ssh', [__file__, '-qt', remotehost] + [envar + '=' + value for envar, value in envars.items()] + [program] + ['--bare'] + ['--delete'] + [o(option) if value is True else o(option, value) for option, value in options.collection.items()] + remotejobs)
            options.boolean.add('bare')
            options.boolean.add('delete')
            call(['echo', '-qRLtz'] + filelist + [remotehost + ':' + buildpath(remoteshare, userhost)])
            execv('/bin/echo', [__file__, '-qt', remotehost] + [envar + '=' + value for envar, value in envars.items()] + [program] + [o(option) for option in options.boolean] + [o(option, value) for option, value in options.constant.items()] + remotejobs)
        raise SystemExit()

    else:

        setup()
        submit()
        while options.fileargs:
            sleep(options.common.wait)
            submit()
    
except KeyboardInterrupt:
    raise SystemExit(colors.red + 'Interrumpido por el usuario' + colors.default)

