# -*- coding: utf-8 -*-
import sys
from time import sleep
from os import path, listdir, environ, getcwd, execv
from argparse import ArgumentParser, Action, SUPPRESS
from subprocess import check_output, CalledProcessError, STDOUT
from . import messages
from .utils import o, p, q, Bunch
from .readspec import readspec
from .jobutils import printchoices, findparameters
from .shared import ArgList, InputFileError, sysinfo, envars, jobspecs, options
from .fileutils import AbsPath, NotAbsolutePath, buildpath
from .submit import setup, submit 

class LsOptions(Action):
    def __init__(self, **kwargs):
        super().__init__(nargs=0, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        if jobspecs.versions:
            print('Versiones del programa:')
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
                print('Conjuntos de parámetros:', p(key))
                pathcomponents = AbsPath(jobspecs.defaults.parameterpath[key]).setkeys(sysinfo).populate()
                findparameters(AbsPath(next(pathcomponents)), pathcomponents, defaults, 1)
        if jobspecs.keywords:
            print('Variables de interpolación:')
            printchoices(choices=jobspecs.keywords)
        raise SystemExit()

class SetCwd(Action):
    def __init__(self, **kwargs):
        super().__init__(nargs=1, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, AbsPath(values[0], cwd=getcwd()))

try:

    parser = ArgumentParser(add_help=False)
    parser.add_argument('--specdir', metavar='SPECDIR', help='Ruta al directorio de especificaciones del programa.')
    parser.add_argument('--program', metavar='PROGNAME', help='Nombre estandarizado del programa.')
    parsedargs, remainingargs = parser.parse_known_args()
    globals().update(vars(parsedargs))
    
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

    group0 = parser.add_argument_group('Argumentos')
    group0.add_argument('fileargs', nargs='*', metavar='FILE', help='Ruta al acrhivo de entrada.')

    group1 = parser.add_argument_group('Ejecución remota')
    group1.add_argument('-H', '--host', metavar='HOSTNAME', help='Procesar el trabajo en el host HOSTNAME.')

    group2 = parser.add_argument_group('Opciones comunes')
    group2.key = 'common'
    group2.add_argument('-h', '--help', action='help', help='Mostrar este mensaje de ayuda y salir.')
    group2.add_argument('-l', '--list', action=LsOptions, default=SUPPRESS, help='Mostrar las opciones disponibles y salir.')
    group2.add_argument('-v', '--version', metavar='PROGVERSION', default=SUPPRESS, help='Versión del ejecutable.')
    group2.add_argument('-q', '--queue', metavar='QUEUENAME', default=SUPPRESS, help='Nombre de la cola requerida.')
    group2.add_argument('-n', '--nproc', type=int, metavar='#PROCS', default=SUPPRESS, help='Número de núcleos de procesador requeridos.')
    group2.add_argument('-N', '--nhost', type=int, metavar='#HOSTS', default=SUPPRESS, help='Número de nodos de ejecución requeridos.')
    group2.add_argument('--nodes', metavar='NODENAME', default=SUPPRESS, help='Solicitar nodos específicos de ejecución por nombre.')
    group2.add_argument('-w', '--wait', type=float, metavar='TIME', default=SUPPRESS, help='Tiempo de pausa (en segundos) después de cada ejecución.')
    group2.add_argument('-f', '--filter', metavar='REGEX', default=SUPPRESS, help='Enviar únicamente los trabajos que coinciden con la expresión regular.')
    group2.add_argument('-D', '--no-defaults', action='store_true', help='Ignorar todos los valores por defecto.')
    group2.add_argument('-i', '--interpolate', action='store_true', help='Interpolar los archivos de entrada.')
    group2.add_argument('-X', '--xdialog', action='store_true', help='Habilitar el modo gráfico para los mensajes y diálogos.')
    group2.add_argument('-b', '--base', action='store_true', help='Interpretar los argumentos como nombres de trabajos.')
    group2.add_argument('--cwd', action=SetCwd, metavar='WORKDIR', default=getcwd(), help='Buscar los archivos de entrada en el drectorio WORKDIR.')
    group2.add_argument('--outdir', metavar='OUTDIR', default=SUPPRESS, help='Guardar los archivos de salida en el directorio OUTDIR.')
    group2.add_argument('--scratch', metavar='SCRDIR', default=SUPPRESS, help='Escribir los acrchivos temporales en el directorio SCRDIR.')
    group2.add_argument('--suffix', metavar='SUFFIX', default=SUPPRESS, help='Agregar el sufijo SUFFIX al nombre del trabajo.')
    group2.add_argument('--delete', action='store_true', help='Borrar los archivos de entrada después de enviar el trabajo.')
    group2.add_argument('--dry', action='store_true', help='Procesar los archivos de entrada sin enviar el trabajo.')

    molgroup = group2.add_mutually_exclusive_group()
    molgroup.add_argument('-m', '--mol', metavar='FILE', default=SUPPRESS, help='Ruta al archivo de coordenadas de interpolación.')
    molgroup.add_argument('-M', '--molfix', metavar='PREFIX', default=SUPPRESS, help='Prefijo del archivo interpolado.')

    sortgroup = group2.add_mutually_exclusive_group()
    sortgroup.add_argument('-s', '--sort', action='store_true', help='Ordenar los argumentos de menor a mayor.')
    sortgroup.add_argument('-S', '--sort-reverse', action='store_true', help='Ordenar los argumentos de mayor a menor.')

    yngroup = group2.add_mutually_exclusive_group()
    yngroup.add_argument('--yes', '--si', action='store_true', help='Responder "si" a todas las preguntas.')
    yngroup.add_argument('--no', action='store_true', help='Responder "no" a todas las preguntas.')

    group3 = parser.add_argument_group('Conjuntos de parámetros')
    group3.key = 'parameters'
    for key in jobspecs.parameters:
        group3.add_argument(o(key), metavar='PARAMETERSET', default=SUPPRESS, help='Nombre del conjunto de parámetros.')

    group4 = parser.add_argument_group('Archivos opcionales')
    group4.key = 'fileopts'
    for key, value in jobspecs.fileopts.items():
        group4.add_argument(o(key), metavar='FILEPATH', default=SUPPRESS, help='Ruta al archivo {}.'.format(value))

    group5 = parser.add_argument_group('Variables de interpolación')
    group5.key = 'keywords'
    for key in jobspecs.keywords:
        group5.add_argument(o(key), metavar=key.upper(), default=SUPPRESS, help='Valor de la variable {}.'.format(key.upper()))

    parsedargs = parser.parse_args(remainingargs)

    for group in parser._action_groups:
        if hasattr(group, 'key'):
            group_dict = {a.dest:getattr(parsedargs, a.dest) for a in group._group_actions if a.dest in parsedargs}
            setattr(options, group.key, Bunch(**group_dict))

    if parsedargs.fileargs:
        arglist = ArgList(parsedargs.fileargs)
    else:
        messages.error('Debe especificar al menos un archivo de entrada')

    for key in options.fileopts:
        options.fileopts[key] = AbsPath(options.fileopts[key], cwd=options.common.cwd)
        if not options.fileopts[key].isfile():
            messages.error('El archivo de entrada', options.fileopts[key], 'no existe', option=o(key))

    if parsedargs.host:

        filelist = []
        remotejobs = []
        remotehost = parsedargs.host
        userhost = sysinfo.user + '@' + sysinfo.hostname
        try:
            output = check_output(['ssh', remotehost, 'echo $JOBSHARE'], stderr=STDOUT)
        except CalledProcessError as exc:
            messages.error(exc.output.decode(sys.stdout.encoding).strip())
        remoteshare = output.decode(sys.stdout.encoding).strip()
        if not remoteshare:
            messages.error('El servidor remoto no acepta trabajos de otro servidor')
        #TODO: Consider include common.mol path in fileopts
        if 'mol' in options.common:
            filelist.append(buildpath(sysinfo.home, '.', path.relpath(options.common.mol, sysinfo.home)))
        #TODO: Make default empty dict for fileopts so no test is needed
        if hasattr(options, 'fileopts'):
            for item in options.fileopts.values():
                filelist.append(buildpath(sysinfo.home, '.', path.relpath(item, sysinfo.home)))
        for item in arglist:
            if isinstance(item, tuple):
                parentdir, basename = item
                relparent = path.relpath(parentdir, sysinfo.home)
                remotecwd = buildpath(remoteshare, userhost, relparent)
                remotejobs.append(basename)
                for key in jobspecs.filekeys:
                    if path.isfile(buildpath(parentdir, (basename, key))):
                        filelist.append(buildpath(sysinfo.home, '.', relparent, (basename, key)))
            elif isinstance(item, InputFileError):
                messages.failure(str(item))
        if remotejobs:
            options.boolean.add('base')
            options.boolean.add('delete')
            options.constant.update({'cwd': remotecwd})
            try:
                check_output(['rsync', '-qRLtz'] + filelist + [remotehost + ':' + buildpath(remoteshare, userhost)])
            except CalledProcessError as exc:
                messages.error(exc.output.decode(sys.stdout.encoding).strip())
            execv('/usr/bin/ssh', [__file__, '-qt', remotehost] + [envar + '=' + value for envar, value in envars.items()] + [program] + [o(option) for option in options.boolean] + [o(option, value) for option, value in options.constant.items()] + remotejobs)
        raise SystemExit()

    else:

        setup()
        options.interpolate()

        item = next(arglist)
        if isinstance(item, tuple):
            submit(*item)
        elif isinstance(item, InputFileError):
            messages.failure(str(item))
        for item in arglist:
            if isinstance(item, tuple):
                sleep(options.common.wait)
                submit(*item)
            elif isinstance(item, InputFileError):
                messages.failure(str(item))
    
except KeyboardInterrupt:
    raise SystemExit(colors.red + 'Interrumpido por el usuario' + colors.default)

