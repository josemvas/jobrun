# -*- coding: utf-8 -*-
import sys
from re import match
from time import sleep
from os import path, execv, getcwd, rename
from subprocess import call, check_output
from . import dialogs
from . import messages
from .queue import submitjob, checkjob
from .utils import Bunch, IdentityList, alnum, natkey, natsort, p, q, sq, catch_keyboard_interrupt, boolstrs
from .jobinit import cluster, program, envars, jobspecs, options, files, keywords, interpolate, jobprefix, remotehost
from .fileutils import AbsPath, NotAbsolutePath, diritems, pathjoin, remove, makedirs, copyfile
from .jobutils import NonMatchingFile, InputFileError
from .boolparse import BoolParser
from .details import mpilibs

def nextfile():

    file = files.pop(0)
    filepath = AbsPath(file, cwdir=getcwd())
    inputdir = filepath.parent()
    basename = filepath.name
    if filepath.isfile():
        for key in (k for i in jobspecs.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                inputext = key
                inputname = basename[:-len(key)-1]
                if options.match:
                    matched = match(options.match, inputname)
                    if matched:
                        for parkey in jobspecs.parameters:
                            try:
                                if parkey in options:
                                    setattr(options, parkey, getattr(options, parkey).format(*matched.groups()))
                                elif parkey + '-path' in options:
                                    setattr(options, parkey + '-path', getattr(options, parkey + '-path').format(*matched.groups()))
                            except IndexError:
                                messages.opterror('El conjunto de parámetros', parkey, 'contiene variables indefinidas')
                    else:
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
    if jobprefix:
        prefixed = '.'.join([jobprefix, inputname])
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, [inputname, key])):
                    with open(pathjoin(inputdir, [inputname, key]), 'r') as fr, open(pathjoin(inputdir, [prefixed, key]), 'w') as fw:
                        if interpolate:
                            try:
                                fw.write(fr.read().format(**keywords))
                            except KeyError as e:
                                raise InputFileError('No se definió la variable de interpolación', q(e.args[0]), 'del archivo de entrada', pathjoin([inputname, key]))
                        else:
                            fw.write(fr.read())
        inputname = prefixed
    for item in jobspecs.resumefiles:
        key = item.split('|')[0]
        if key + 'file' in options:
            sourcepath = AbsPath(getattr(options, key + 'file'), cwdir=getcwd())
            if sourcepath.isfile():
                sourcepath.symlinkto(inputdir, [inputname, key])
            else:
                messages.opterror('El archivo', sourcepath, 'no existe (', key + 'file)')
    return inputdir, inputname, inputext

@catch_keyboard_interrupt
def wait():

    sleep(options.wait)

@catch_keyboard_interrupt
def connect():

    cluster.remoteshare = check_output(['ssh', remotehost, 'echo', '-n', '$JOBSHARE']).decode(sys.stdout.encoding)
    if not cluster.remoteshare:
        messages.runerror('El servidor remoto no acepta trabajos de otro servidor')
        
@catch_keyboard_interrupt
def remoterun():

    if remotefiles:
        execv('/usr/bin/ssh', [__file__, '-qt', remotehost] + ['{}={}'.format(envar, value) for envar, value in envars.items()] + [program] + ['--{}'.format(option) if value is True else '--{}={}'.format(option, value) for option, value in vars(options).items() if value] + ['--temporary'] + remotefiles)

@catch_keyboard_interrupt
def dryrun():

    try:
        inputdir, inputname, inputext = nextfile()
    except NonMatchingFile:
        return
    except InputFileError as e:
        messages.failure(e)
        return

@catch_keyboard_interrupt
def upload():

    try:
        inputdir, inputname, inputext = nextfile()
    except NonMatchingFile:
        return
    except InputFileError as e:
        messages.failure(e)
        return
    transferlist = []
    relparentdir = path.relpath(inputdir, cluster.home)
    userhost = cluster.user + '@' + cluster.name.lower()
    remotefiles.append(pathjoin(cluster.remoteshare, userhost, relparentdir, (inputname, inputext)))
    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(inputdir, (inputname, key))):
            transferlist.append(pathjoin(cluster.home, '.', relparentdir, (inputname, key)))
    call(['rsync', '-qRLtz'] + transferlist + [remotehost + ':' + pathjoin(cluster.remoteshare, userhost)])

@catch_keyboard_interrupt
def setup():

    script.environ = []
    script.command = []
    script.qctrl = []

    if not jobspecs.scheduler:
        messages.cfgerror('No se especificó el nombre del sistema de colas (scheduler)')
    
    if options.temporary:
        script.putfile = rename
    else:
        script.putfile = copyfile

    if getattr(options, 'ignore-defaults'):
        jobspecs.defaults.pop('version', None)
        jobspecs.defaults.pop('paramsets', None)
    
    if options.sort:
        files.sort(key=natkey)
    elif getattr(options, 'sort-reverse'):
        files.sort(key=natkey, reverse=True)
    
    if not options.wait:
        try: options.wait = float(jobspecs.defaults.waitime)
        except AttributeError: options.wait = 0
    
    if not options.ncore:
        options.ncore = 1
    
    if not options.nhost:
        options.nhost = 1

    if options.xdialog:
        try:
            from bulletin import TkDialogs
        except ImportError:
            raise SystemExit()
        else:
            dialogs.yesno = join_arguments(wordseps)(TkDialogs().yesno)
            messages.failure = join_arguments(wordseps)(TkDialogs().message)
            messages.success = join_arguments(wordseps)(TkDialogs().message)

    if not 'outputdir' in jobspecs.defaults:
        messages.cfgerror('No se especificó el directorio de salida por defecto (outputdir)')

    if not 'scratchdir' in jobspecs.defaults:
        messages.cfgerror('No se especificó el directorio temporal de escritura por defecto (scratchdir)')

    if options.scrdir:
        script.workdir = AbsPath(options.scrdir, jobspecs.qenv.jobid, cwdir=getcwd())
    else:
        try:
            script.workdir = AbsPath(jobspecs.defaults.scratchdir, jobspecs.qenv.jobid)
        except NotAbsolutePath:
            messages.cfgerror(jobspecs.defaults.scratchdir, 'no es una ruta absoluta (scratchdir)')

    if not options.queue:
        if jobspecs.defaults.queue:
            options.queue = jobspecs.defaults.queue
        else:
            messages.cfgerror('No se especificó la cola por defecto (default:queue)')
    
    if not jobspecs.progname:
        messages.cfgerror('No se especificó el nombre del programa (progname)')
    
    if not jobspecs.progkey:
        messages.cfgerror('No se especificó la clave del programa (progkey)')
    
    for parkey in jobspecs.parameters:
        if parkey in options:
            if getattr(options, parkey).startswith('/') or getattr(options, parkey).endswith('/'):
                messages.opterror('El nombre del conjunto de parámetros no puede empezar ni terminar con una diagonal')

    if 'mpilaunch' in jobspecs:
        try: jobspecs.mpilaunch = boolstrs[jobspecs.mpilaunch]
        except KeyError:
            messages.cfgerror('Este valor requiere ser "True" o "False" (mpilaunch)')
    
    if not jobspecs.filekeys:
        messages.cfgerror('La lista de archivos del programa no existe o está vacía (filekeys)')
    
    if jobspecs.inputfiles:
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if not key in jobspecs.filekeys:
                    messages.cfgerror('El nombre del archivo de entrada "{0}" no fue definido'.format(key), '(inputfiles)')
    else:
        messages.cfgerror('La lista de archivos de entrada no existe o está vacía (inputfiles)')
    
    if jobspecs.outputfiles:
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                if not key in jobspecs.filekeys:
                    messages.cfgerror('El nombre del archivo de salida "{0}" no fue definido'.format(key), 'outputfiles')
    else:
        messages.cfgerror('La lista de archivos de salida no existe o está vacía (outputfiles)')
    
    #TODO: MPI support for Slurm
    if jobspecs.parallelib:
        if jobspecs.parallelib.lower() == 'none':
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.nhost))
        elif jobspecs.parallelib.lower() == 'openmp':
            script.qctrl.append(jobspecs.qctrl.ncore.format(options.ncore))
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.nhost))
            script.command.append('OMP_NUM_THREADS=' + str(options.ncore))
        elif jobspecs.parallelib.lower() in mpilibs:
            if not 'mpilaunch' in jobspecs:
                messages.cfgerror('No se especificó si el programa es lanzado por mpirun (mpilaunch)')
            script.qctrl.append(jobspecs.qctrl.ncore.format(options.ncore))
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.nhost))
            if jobspecs.mpilaunch:
                script.command.append(jobspecs.mpilauncher[jobspecs.parallelib])
        else:
            messages.cfgerror('El tipo de paralelización ' + jobspecs.parallelib + ' no está soportado')
    else:
        messages.cfgerror('No se especificó el tipo de paralelización del programa (parallelib)')
    
    if jobspecs.versions:
        if not options.version:
            if 'version' in jobspecs.defaults:
                if jobspecs.defaults.version in jobspecs.versions:
                    options.version = jobspecs.defaults.version
                else:
                    messages.opterror('La versión establecida por defecto es inválida')
            else:
                options.version = dialogs.chooseone('Seleccione una versión', choices=natsort(jobspecs.versions.keys()))
                if not options.version in jobspecs.versions:
                    messages.opterror('La versión seleccionada es inválida')
    else:
        messages.cfgerror('La lista de versiones no existe o está vacía (versions)')

    if not options.version in jobspecs.versions:
       messages.opterror('La versión seleccionada no es válida')
    
    if not jobspecs.versions[options.version].executable:
        messages.cfgerror('No se especificó el ejecutable de la versión', options.version)
    
    script.environ.extend(jobspecs.onscript)

    for envar, filepath in jobspecs.export.items() | jobspecs.versions[options.version].export.items():
        abspath = AbsPath(filepath, cwdir=script.workdir).setkeys(cluster).validate()
        script.environ.append('export {}={}'.format(envar, abspath))
    
    for filepath in jobspecs.source + jobspecs.versions[options.version].source:
        script.environ.append('source {}'.format(AbsPath(filepath).setkeys(cluster).validate()))
    
    for module in jobspecs.load + jobspecs.versions[options.version].load:
        script.environ.append('module load {}'.format(module))
    
    try:
        script.command.append(AbsPath(jobspecs.versions[options.version].executable).setkeys(cluster).validate())
    except NotAbsolutePath:
        script.command.append(jobspecs.versions[options.version].executable)

    script.qctrl.append(jobspecs.qctrl.label.format(jobspecs.progname))
    script.qctrl.append(jobspecs.qctrl.queue.format(options.queue))
    script.qctrl.append(jobspecs.qctrl.output.format(AbsPath(jobspecs.logdir).setkeys(cluster).validate()))
    script.qctrl.append(jobspecs.qctrl.error.format(AbsPath(jobspecs.logdir).setkeys(cluster).validate()))
    
    if options.node:
        script.qctrl.append(jobspecs.qctrl.hosts.format(options.node))
    
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
            messages.cfgerror('El nombre del archivo de entrada/salida "{0}" no fue definido'.format(key), '(optionargs)')
        script.command.append('-{key} {val}'.format(key=key, val=jobspecs.filekeys[jobspecs.optionargs[key]]))
    
    for item in jobspecs.positionargs:
        for key in item.split('|'):
            if not key in jobspecs.filekeys:
                messages.cfgerror('El nombre del archivo de entrada/salida "{0}" no fue definido'.format(key), '(positionargs)')
        script.command.append('@' + p('|'.join(jobspecs.filekeys[i] for i in item.split('|'))))
    
    if 'stdin' in jobspecs:
        try: script.command.append('0<' + ' ' + jobspecs.filekeys[jobspecs.stdinput])
        except KeyError: messages.cfgerror('El nombre de archivo', q(jobspecs.stdinput), 'no fue definido (stdinput)')
    if 'stdoutput' in jobspecs:
        try: script.command.append('1>' + ' ' + jobspecs.filekeys[jobspecs.stdoutput])
        except KeyError: messages.cfgerror('El nombre de archivo', q(jobspecs.stdoutput), 'no fue definido (stdoutput)')
    if 'stderror' in jobspecs:
        try: script.command.append('2>' + ' ' + jobspecs.filekeys[jobspecs.stderror])
        except KeyError: messages.cfgerror('El nombre de archivo', q(jobspecs.stderror), 'no fue definido (stderror)')
    
    script.chdir = 'cd "{}"'.format
    script.runathead = 'ssh $head "{}"'.format
    if jobspecs.hostcopy == 'local':
        script.rmdir = 'rm -rf "{}"'.format
        script.mkdir = 'mkdir -p -m 700 "{}"'.format
        script.fetch = 'mv "{}" "{}"'.format
        script.fetchdir = 'cp -r "{}/." "{}"'.format
        script.remit = 'cp "{}" "{}"'.format
    elif jobspecs.hostcopy == 'remote':
        script.rmdir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'{0}\'"; done'.format
        script.mkdir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -p -m 700 "\'{0}\'"; done'.format
        script.fetch = 'for host in ${{hosts[*]}}; do scp $head:"\'{0}\'" $host:"\'{1}\'"; ssh $head rm "\'{0}\'"; done'.format
        script.fetchdir = 'for host in ${{hosts[*]}}; do ssh $head tar -cf- -C "\'{0}\'" . | ssh $host tar -xf- -C "\'{1}\'"; done'.format
        script.remit = 'scp "{}" $head:"\'{}\'"'.format
    else:
        messages.cfgerror('El método de copia', q(jobspecs.hostcopy), 'no es válido')
    
@catch_keyboard_interrupt
def localrun():

    try:
        inputdir, inputname, inputext = nextfile()
    except NonMatchingFile:
        return
    except InputFileError as e:
        messages.failure(e)
        return

    filebools = {}

    for key in jobspecs.filekeys:
        filebools[key] = path.isfile(pathjoin(inputdir, (inputname, key)))

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

    for parkey in jobspecs.parameters:
        if parkey + '-path' in options:
            rootpath = AbsPath(getattr(options, parkey + '-path'), cwdir=getcwd())
        elif parkey in jobspecs.defaults.parampaths:
            if parkey in options:
                paramsets = getattr(options, parkey).split('/')
            elif 'paramsets' in jobspecs.defaults and parkey in jobspecs.defaults.paramsets:
                if isinstance(jobspecs.defaults.paramsets[parkey], (list, tuple)):
                    paramsets = jobspecs.defaults.paramsets[parkey]
                else:
                    messages.opterror('Los conjuntos de parámetros por defecto deben definirse en una lista', p(parkey))
            else:
                paramsets = []
            pathcomponents = AbsPath(jobspecs.defaults.parampaths[parkey], cwdir=getcwd()).setkeys(cluster).populate()
            rootpath = AbsPath(next(pathcomponents))
            for component in pathcomponents:
                try:
                    rootpath = rootpath.joinpath(component.format(*paramsets))
                except IndexError:
                    choices = diritems(rootpath, component)
                    choice = dialogs.chooseone('Seleccione un conjunto de parámetros para el trabajo', jobname, p(parkey), choices=choices)
                    rootpath = rootpath.joinpath(choice)
        else:
            messages.cfgerror('Debe indicar la ruta al directorio de parámetros', p(parkey))
        if rootpath.exists():
            parameters.append(rootpath)
        else:
            messages.opterror('La ruta', rootpath, 'no existe', p(parkey))
    
    if options.outdir:
        outputdir = AbsPath(options.outdir, cwdir=inputdir)
    else:
        outputdir = AbsPath(jobspecs.defaults.outputdir, cwdir=inputdir).setkeys(dict(jobname=jobname)).validate()

    numkey = alnum(jobspecs.versions[options.version].number)
    hiddendir = AbsPath(outputdir, '.' + jobspecs.progkey + numkey)
    outputname = jobname + '.' + jobspecs.progkey + numkey

    inputfiles = []
    inputdirs = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            if path.isfile(pathjoin(inputdir, (inputname, key))):
                inputfiles.append(((pathjoin(hiddendir, jobspecs.filekeys[key])), pathjoin(script.workdir, jobspecs.filekeys[key])))
    
    for parameter in parameters:
        if parameter.isfile():
            inputfiles.append((parameter, pathjoin(script.workdir, path.basename(parameter))))
        elif parameter.isdir():
            inputdirs.append((pathjoin(parameter), script.workdir))

    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append((pathjoin(script.workdir, jobspecs.filekeys[key]), pathjoin(outputdir, (outputname, key))))
    
    if outputdir.isdir():
        if hiddendir.isdir():
            try:
                with open(pathjoin(hiddendir, 'jobid'), 'r') as t:
                    jobid = t.read()
                    jobstate = checkjob(jobid)
                    if callable(jobstate):
                        messages.failure(jobstate(jobname=jobname, jobid=jobid))
                        return
            except FileNotFoundError:
                pass
        elif hiddendir.exists():
            messages.failure('No se puede crear la carpeta', hiddendir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(hiddendir)
        if not set(outputdir.listdir()).isdisjoint(pathjoin((outputname, k)) for i in jobspecs.outputfiles for k in i.split('|')):
            if options.no is True or (options.yes is False and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                return
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                remove(pathjoin(outputdir, (outputname, key)))
        if inputdir != outputdir:
            for item in jobspecs.inputfiles:
                for key in item.split('|'):
                    remove(pathjoin(outputdir, (jobname, key)))
    elif outputdir.exists():
        messages.failure('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outputdir)
        makedirs(hiddendir)
    
#    if inputdir != outputdir:
    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            if path.isfile(pathjoin(inputdir, (inputname, key))):
                script.putfile(pathjoin(inputdir, (inputname, key)), pathjoin(hiddendir, jobspecs.filekeys[key]))
    
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
        messages.success('El trabajo', q(jobname), 'se correrá en', str(options.ncore), 'núcleo(s) en', cluster.name, 'con el jobid', jobid)
        with open(pathjoin(hiddendir, 'jobid'), 'w') as f:
            f.write(jobid)
    
parameters = []
remotefiles = []
script = Bunch()

