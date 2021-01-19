# -*- coding: utf-8 -*-
import re
import sys
from time import sleep
from os import path, execv, getcwd, rename
from subprocess import call, check_output
from string import Formatter
from . import dialogs
from . import messages
from .queue import submitjob, checkjob
from .fileutils import AbsPath, NotAbsolutePath, diritems, pathjoin, remove, makedirs, copyfile
from .utils import Bunch, IdentityList, natkey, natsort, p, q, sq, catch_keyboard_interrupt, boolstrs
from .bunches import cluster, envars, jobspecs, options, keywords, files
from .jobutils import NonMatchingFile, InputFileError
from .boolparse import BoolParser
from .details import mpilibs


def nextfile():

    file = files.pop(0)
    filepath = AbsPath(file, cwdir=getcwd())
    srcdir = filepath.parent()
    basename = filepath.name
    if filepath.isfile():
        for key in (k for i in jobspecs.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                extension = key
                inputname = basename[:-len(key)-1]
                if options.object.filter:
                    match = re.match(options.object.filter, inputname)
                    if not match:
                        raise NonMatchingFile()
                break
        else:
            raise InputFileError('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobspecs.progname)
    elif filepath.isdir():
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'es un directorio')
    elif filepath.exists():
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'no es un archivo regular')
    else:
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'no existe')
    if options.jobprefix:
        prefixed = '.'.join([options.jobprefix, inputname])
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(srcdir, [inputname, key])):
                    with open(pathjoin(srcdir, [inputname, key]), 'r') as fr, open(pathjoin(srcdir, [prefixed, key]), 'w') as fw:
                        if options.interpolate:
                            try:
                                fw.write(fr.read().format(**keywords))
                            except KeyError as e:
                                raise InputFileError('No se definió la variable de interpolación', q(e.args[0]), 'del archivo de entrada', pathjoin([inputname, key]))
                        else:
                            fw.write(fr.read())
        inputname = prefixed
    for key in restartfiles:
        restartfiles[key].linkto(srcdir, [inputname, key])
    return srcdir, inputname, extension



@catch_keyboard_interrupt
def wait():

    sleep(options.object.wait)



@catch_keyboard_interrupt
def connect():

    cluster.remoteshare = check_output(['ssh', options.remotehost, 'echo', '-n', '$JOBSHARE']).decode(sys.stdout.encoding)
    if not cluster.remoteshare:
        messages.error('El servidor remoto no acepta trabajos de otro servidor')
        


@catch_keyboard_interrupt
def remoterun():

    if remotefiles:
        execv('/usr/bin/ssh', [__file__, '-qt', options.remotehost] + ['{}={}'.format(envar, value) for envar, value in envars.items()] + [options.program] + ['--{}'.format(option) if value is True else '--{}={}'.format(option, value) for option, value in vars(options.object).items() if value] + ['--temporary'] + remotefiles)



@catch_keyboard_interrupt
def dryrun():

    try:
        srcdir, inputname, extension = nextfile()
    except NonMatchingFile:
        return
    except InputFileError as e:
        messages.failure(e)
        return



@catch_keyboard_interrupt
def upload():

    try:
        srcdir, inputname, extension = nextfile()
    except NonMatchingFile:
        return
    except InputFileError as e:
        messages.failure(e)
        return

    transferlist = []
    relparentdir = path.relpath(srcdir, cluster.home)
    userhost = cluster.user + '@' + cluster.name.lower()
    remotefiles.append(pathjoin(cluster.remoteshare, userhost, relparentdir, (inputname, extension)))
    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(srcdir, (inputname, key))):
            transferlist.append(pathjoin(cluster.home, '.', relparentdir, (inputname, key)))
    call(['rsync', '-qRLtz'] + transferlist + [options.remotehost + ':' + pathjoin(cluster.remoteshare, userhost)])



@catch_keyboard_interrupt
def setup():

    script.environ = []
    script.command = []
    script.qctrl = []

    if not jobspecs.scheduler:
        messages.error('No se especificó el nombre del sistema de colas', spec='scheduler')
    
    if options.object.temporary:
        script.putfile = rename
    else:
        script.putfile = copyfile

    if getattr(options.object, 'ignore-defaults'):
        jobspecs.defaults.pop('version', None)
        jobspecs.defaults.pop('parameterset', None)
    
    if options.object.sort:
        files.sort(key=natkey)
    elif getattr(options.object, 'sort-reverse'):
        files.sort(key=natkey, reverse=True)
    
    if not options.object.wait:
        try: options.object.wait = float(jobspecs.defaults.waitime)
        except AttributeError: options.object.wait = 0
    
    if not options.object.ncore:
        options.object.ncore = 1
    
    if not options.object.nhost:
        options.object.nhost = 1

    if options.object.xdialog:
        try:
            from bulletin import TkDialogs
        except ImportError:
            raise SystemExit()
        else:
            dialogs.yesno = join_arguments(wordseps)(TkDialogs().yesno)
            messages.failure = join_arguments(wordseps)(TkDialogs().message)
            messages.success = join_arguments(wordseps)(TkDialogs().message)

    if not 'outdir' in jobspecs.defaults:
        messages.error('No se especificó el directorio de salida por defecto', spec='defaults.outdir')

    if not 'scratchdir' in jobspecs.defaults:
        messages.error('No se especificó el directorio temporal de escritura por defecto', spec='defaults.scratchdir')

    if options.object.writedir:
        script.workdir = AbsPath(options.object.writedir, jobspecs.qenv.jobid, cwdir=getcwd())
    else:
        try:
            script.workdir = AbsPath(jobspecs.defaults.scratchdir, jobspecs.qenv.jobid).setkeys(cluster).validate()
        except NotAbsolutePath:
            messages.error(jobspecs.defaults.scratchdir, 'no es una ruta absoluta', spec='defaults.scratchdir')

    if not options.object.queue:
        if jobspecs.defaults.queue:
            options.object.queue = jobspecs.defaults.queue
        else:
            messages.error('No se especificó la cola por defecto', spec='defaults.queue')
    
    if not jobspecs.progname:
        messages.error('No se especificó el nombre del programa', spec='progname')
    
    if not jobspecs.progkey:
        messages.error('No se especificó la clave del programa', spec='progkey')
    
    for key in jobspecs.parameters:
        if key in options.object:
            if '/' in getattr(options.object, key):
                messages.error(getattr(options.object, key), 'no puede ser una ruta', option=key)

    if 'mpilaunch' in jobspecs:
        try: jobspecs.mpilaunch = boolstrs[jobspecs.mpilaunch]
        except KeyError:
            messages.error('Este valor requiere ser "True" o "False"', spec='mpilaunch')
    
    if not jobspecs.filekeys:
        messages.error('La lista de archivos del programa no existe o está vacía', spec='filekeys')
    
    if jobspecs.inputfiles:
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if not key in jobspecs.filekeys:
                    messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='inputfiles')
    else:
        messages.error('La lista de archivos de entrada no existe o está vacía', spec='inputfiles')
    
    if jobspecs.outputfiles:
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                if not key in jobspecs.filekeys:
                    messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='outputfiles')
    else:
        messages.error('La lista de archivos de salida no existe o está vacía', spec='outputfiles')
    
    #TODO: MPI support for Slurm
    if jobspecs.parallelib:
        if jobspecs.parallelib.lower() == 'none':
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.object.nhost))
        elif jobspecs.parallelib.lower() == 'openmp':
            script.qctrl.append(jobspecs.qctrl.ncore.format(options.object.ncore))
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.object.nhost))
            script.command.append('OMP_NUM_THREADS=' + str(options.object.ncore))
        elif jobspecs.parallelib.lower() in mpilibs:
            if not 'mpilaunch' in jobspecs:
                messages.error('No se especificó si el programa debe ser ejecutado por mpirun', spec='mpilaunch')
            script.qctrl.append(jobspecs.qctrl.ncore.format(options.object.ncore))
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.object.nhost))
            if jobspecs.mpilaunch:
                script.command.append(jobspecs.mpilauncher[jobspecs.parallelib])
        else:
            messages.error('El tipo de paralelización', jobspecs.parallelib, 'no está soportado', spec='parallelib')
    else:
        messages.error('No se especificó el tipo de paralelización del programa', spec='parallelib')
    
    if jobspecs.versions:
        if not options.object.version:
            if 'version' in jobspecs.defaults:
                if jobspecs.defaults.version in jobspecs.versions:
                    options.object.version = jobspecs.defaults.version
                else:
                    messages.error('La versión establecida por defecto es inválida', spec='defaults.version')
            else:
                options.object.version = dialogs.chooseone('Seleccione una versión', choices=natsort(jobspecs.versions.keys()))
        if not options.object.version in jobspecs.versions:
            messages.error('La versión', options.object.version, 'no es válida', option='version')
    else:
        messages.error('La lista de versiones no existe o está vacía', spec='versions')

    if not jobspecs.versions[options.object.version].executable:
        messages.error('No se especificó el ejecutable', spec='versions[{}].executable'.format(options.object.version))
    
    script.environ.extend(jobspecs.onscript)

    for envar, filepath in jobspecs.export.items() | jobspecs.versions[options.object.version].export.items():
        abspath = AbsPath(filepath, cwdir=script.workdir).setkeys(cluster).validate()
        script.environ.append('export {}={}'.format(envar, abspath))
    
    for filepath in jobspecs.source + jobspecs.versions[options.object.version].source:
        script.environ.append('source {}'.format(AbsPath(filepath).setkeys(cluster).validate()))
    
    for module in jobspecs.load + jobspecs.versions[options.object.version].load:
        script.environ.append('module load {}'.format(module))
    
    try:
        script.command.append(AbsPath(jobspecs.versions[options.object.version].executable).setkeys(cluster).validate())
    except NotAbsolutePath:
        script.command.append(jobspecs.versions[options.object.version].executable)

    script.qctrl.append(jobspecs.qctrl.label.format(jobspecs.progname))
    script.qctrl.append(jobspecs.qctrl.queue.format(options.object.queue))
    script.qctrl.append(jobspecs.qctrl.output.format(AbsPath(jobspecs.logdir).setkeys(cluster).validate()))
    script.qctrl.append(jobspecs.qctrl.error.format(AbsPath(jobspecs.logdir).setkeys(cluster).validate()))
    
    if options.object.nodes:
        script.qctrl.append(jobspecs.qctrl.nodes.format(options.object.nodes))
    
    script.environ.append("shopt -s nullglob extglob")
    script.environ.append("head=" + cluster.head)
    script.environ.extend('='.join(i) for i in jobspecs.qenv.items())
    script.environ.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    script.environ.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    script.environ.append("jobram=$(($ncore*$totalram/$(nproc --all)))")
    
    for var in jobspecs.filevars:
        script.environ.append(var + '=' + sq(jobspecs.filekeys[jobspecs.filevars[var]]))
    
    for key in jobspecs.optionargs:
        if not jobspecs.optionargs[key] in jobspecs.filekeys:
            messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='optionargs')
        script.command.append('-{key} {val}'.format(key=key, val=jobspecs.filekeys[jobspecs.optionargs[key]]))
    
    for item in jobspecs.positionargs:
        for key in item.split('|'):
            if not key in jobspecs.filekeys:
                messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='positionargs')
        script.command.append('@' + p('|'.join(jobspecs.filekeys[i] for i in item.split('|'))))
    
    if 'stdinput' in jobspecs:
        try:
            script.command.append('0<' + ' ' + jobspecs.filekeys[jobspecs.stdinput])
        except KeyError:
            messages.error('La clave', q(jobspecs.stdinput) ,'no tiene asociado ningún archivo', spec='stdinput')
    if 'stdoutput' in jobspecs:
        try:
            script.command.append('1>' + ' ' + jobspecs.filekeys[jobspecs.stdoutput])
        except KeyError:
            messages.error('La clave', q(jobspecs.stdoutput) ,'no tiene asociado ningún archivo', spec='stdoutput')
    if 'stderror' in jobspecs:
        try:
            script.command.append('2>' + ' ' + jobspecs.filekeys[jobspecs.stderror])
        except KeyError:
            messages.error('La clave', q(jobspecs.stderror) ,'no tiene asociado ningún archivo', spec='stderror')
    
    script.chdir = 'cd "{}"'.format
    script.runathead = 'ssh $head "{}"'.format
    if jobspecs.hostcopy == 'local':
        script.rmdir = 'rm -rf "{}"'.format
        script.mkdir = 'mkdir -p -m 700 "{}"'.format
        script.fetch = 'mv "{}" "{}"'.format
        script.fetchdir = 'cp -r "{}/." "{}"'.format
        script.remit = 'cp "{}" "{}"'.format
    elif jobspecs.hostcopy == 'remote':
        script.rmdir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'{}\'"; done'.format
        script.mkdir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.fetch = 'for host in ${{hosts[*]}}; do scp $head:"\'{0}\'" $host:"\'{1}\'"; ssh $head rm "\'{0}\'"; done'.format
        script.fetchdir = 'for host in ${{hosts[*]}}; do ssh $head tar -cf- -C "\'{0}\'" . | ssh $host tar -xf- -C "\'{1}\'"; done'.format
        script.remit = 'scp "{}" $head:"\'{}\'"'.format
    else:
        messages.error('El método de copia', q(jobspecs.hostcopy), 'no es válido', spec='hostcopy')

    for item in jobspecs.restartfiles:
        for key in item.split('|'):
            if key in options.object:
                restartfiles[key] = AbsPath(getattr(options.object, key), cwdir=getcwd())
                if not restartfiles[key].isfile():
                    messages.error('El archivo de entrada', restartfiles[key], 'no existe', option=key)

#TODO: Check if variables in parameter sets match filter groups
#    if options.object.filter:
#        pattern = re.compile(options.object.filter)
#        for item in jobspecs.parameters + [i + '-path' for i in jobspecs.parameters]:
#            if item in options.object:
#                for key in Formatter().parse(getattr(options.object, item)):
#                    if key[1] is not None:
#                        try:
#                            if int(key[1]) not in range(pattern.groups()):
#                                messages.error('El nombre o ruta', getattr(options.object, key), 'contiene referencias no numéricas', option=key)
#                        except ValueError:
#                            messages.error('El nombre o ruta', getattr(options.object, key), 'contiene referencias fuera de rango', option=key)



@catch_keyboard_interrupt
def localrun():

    try:
        srcdir, inputname, extension = nextfile()
    except NonMatchingFile:
        return
    except InputFileError as e:
        messages.failure(e)
        return

    filebools = {}

    for key in jobspecs.filekeys:
        filebools[key] = path.isfile(pathjoin(srcdir, (inputname, key)))

    if 'filecheck' in jobspecs:
        if not BoolParser(jobspecs.filecheck).ev(filebools):
            messages.failure('No se encontraron todos los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobspecs:
        if BoolParser(jobspecs.fileclash).ev(filebools):
            messages.failure('Hay un conflicto entre los archivos de entrada')
            return
    
    if inputname.endswith('.' + jobspecs.progkey):
        jobname = inputname[:-len(jobspecs.progkey)-1]
    else:
        jobname = inputname

#TODO: Use filter matchings groups to build the parameter list
#    for key in jobspecs.parameters:
#        if key in options.object:
#            for var in getattr(options.object, key).split(','): 
#                if var.startswith('%'):
#                    parameterlist.append(match.groups(var[1:]))
#                else:
#                    parameterlist.append(var[1:])

    for key in jobspecs.parameters:
        if key + '-path' in options.object:
            rootpath = AbsPath(getattr(options.object, key + '-path'), cwdir=getcwd())
#       if key in jobspecs.defaults.parameterpath: (key and key-path options should not be exclusive)
        elif key in jobspecs.defaults.parameterpath:
            if key in options.object:
                parameterlist = getattr(options.object, key).split(',')
            elif 'parameterset' in jobspecs.defaults and key in jobspecs.defaults.parameterset:
                if isinstance(jobspecs.defaults.parameterset[key], (list, tuple)):
                    parameterlist = jobspecs.defaults.parameterset[key]
                else:
                    messages.error('La clave', key, 'no es una lista', spec='defaults.parameterset')
            else:
                parameterlist = []
            pathcomponents = AbsPath(jobspecs.defaults.parameterpath[key], cwdir=getcwd()).setkeys(cluster).populate()
            rootpath = AbsPath(next(pathcomponents))
            for component in pathcomponents:
                try:
                    rootpath = rootpath.joinpath(component.format(*parameterlist))
                except IndexError:
                    choices = diritems(rootpath, component)
                    choice = dialogs.chooseone('Seleccione un conjunto de parámetros para el trabajo', jobname, p(key), choices=choices)
                    rootpath = rootpath.joinpath(choice)
        else:
            messages.error('Debe indicar la ruta al directorio de parámetros', option='{}-path'.format(key), spec='defaults.parameterpath[{}]'.format(key))
        if rootpath.exists():
            parameters.append(rootpath)
        else:
            messages.error('La ruta', rootpath, 'no existe', option='{}-path'.format(key), spec='defaults.parameterpath[{}]'.format(key))
    
    if options.object.outdir:
        outdir = AbsPath(options.object.outdir, cwdir=srcdir)
    else:
        jobinfo = dict(
            jobname = jobname,
            progkey = jobspecs.progkey,
            version = options.object.version.replace(' ', '.'))
        outdir = AbsPath(jobspecs.defaults.outdir, cwdir=srcdir).setkeys(jobinfo).validate()

    hiddendir = AbsPath(outdir, '.job')

    inputfiles = []
    inputdirs = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            if path.isfile(pathjoin(srcdir, (inputname, key))):
                inputfiles.append(((pathjoin(hiddendir, jobspecs.filekeys[key])), pathjoin(script.workdir, jobspecs.filekeys[key])))
    
    for parameter in parameters:
        if parameter.isfile():
            inputfiles.append((parameter, pathjoin(script.workdir, path.basename(parameter))))
        elif parameter.isdir():
            inputdirs.append((pathjoin(parameter), script.workdir))

    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append((pathjoin(script.workdir, jobspecs.filekeys[key]), pathjoin(outdir, (jobname, key))))
    
    if outdir.isdir():
        if hiddendir.isdir():
            try:
                with open(pathjoin(hiddendir, 'jobid'), 'r') as f:
                    jobid = f.read()
                jobstate = checkjob(jobid)
                if jobstate is not None:
                    messages.failure(jobstate.format(id=jobid, name=jobname))
                    return
            except FileNotFoundError:
                pass
        elif hiddendir.exists():
            messages.failure('No se puede crear la carpeta', hiddendir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(hiddendir)
        if not set(outdir.listdir()).isdisjoint(pathjoin((jobname, k)) for i in jobspecs.outputfiles for k in i.split('|')):
            if options.object.no is True or (options.object.yes is False and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                messages.failure('Cancelado por el usuario')
                return
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                remove(pathjoin(outdir, (jobname, key)))
        if srcdir != outdir:
            for item in jobspecs.inputfiles:
                for key in item.split('|'):
                    remove(pathjoin(outdir, (jobname, key)))
    elif outdir.exists():
        messages.failure('No se puede crear la carpeta', outdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outdir)
        makedirs(hiddendir)
    
#    if srcdir != outdir:
    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            if path.isfile(pathjoin(srcdir, (inputname, key))):
                script.putfile(pathjoin(srcdir, (inputname, key)), pathjoin(hiddendir, jobspecs.filekeys[key]))
    
    script.qctrl.append(jobspecs.qctrl.name.format(jobname))

    offscript = []

    for line in jobspecs.offscript:
        try:
           offscript.append(line.format(jobname=jobname, clustername=cluster.name, **envars))
        except KeyError:
           pass

    jobscript = pathjoin(hiddendir, 'jobscript')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash' + '\n')
        f.write(''.join(i + '\n' for i in script.qctrl))
        f.write(''.join(i + '\n' for i in script.environ))
        f.write('for host in ${hosts[*]}; do echo "<$host>"; done' + '\n')
        f.write(script.mkdir(script.workdir) + '\n')
        f.write(''.join(script.fetch(i, j) + '\n' for i, j in inputfiles))
        f.write(''.join(script.fetchdir(i, j) + '\n' for i, j in inputdirs))
        f.write(script.chdir(script.workdir) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.prescript))
        f.write(' '.join(script.command) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.postscript))
        f.write(''.join(script.remit(i, j) + '\n' for i, j in outputfiles))
        f.write(script.rmdir(script.workdir) + '\n')
        f.write(''.join(script.runathead(i) + '\n' for i in offscript))
    
    try:
        jobid = submitjob(jobscript)
    except RuntimeError as error:
        messages.failure('El sistema de colas no envió el trabajo porque ocurrió un error', p(error))
        return
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(options.object.ncore), 'núcleo(s) en', cluster.name, 'con número de trabajo', jobid)
        with open(pathjoin(hiddendir, 'jobid'), 'w') as f:
            f.write(jobid)
    
parameters = []
remotefiles = []
restartfiles = {}
script = Bunch()

