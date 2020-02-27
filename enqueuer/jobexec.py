# -*- coding: utf-8 -*-
import sys
from time import sleep
from os import path, execv, getcwd
from subprocess import call, check_output
from importlib import import_module
from . import dialogs
from . import messages
from .utils import Bunch, IdentityList, alnum, natkey, natsort, p, q, sq, catch_keyboard_interrupt, boolstrs
from .jobinit import cluster, program, envars, jobspecs, options, files, keywords, interpolate, jobprefix, remote_run
from .fileutils import AbsPath, NotAbsolutePath, diritems, pathjoin, remove, makedirs, copyfile
from .jobutils import InputFileError
from .boolparse import BoolParser
from .details import mpilibs

scheduler = import_module('.schedulers.' + jobspecs.scheduler, package='enqueuer')
jobformat = Bunch(scheduler.jobformat)
jobenvars = Bunch(scheduler.jobenvars)

def nextfile():
    file = files.pop(0)
    try:
        filepath = AbsPath(file)
    except NotAbsolutePath:
        filepath = AbsPath(getcwd(), file)
    inputdir = filepath.parent()
    basename = filepath.name
    if filepath.isfile():
        for key in (k for i in jobspecs.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                inputname = basename[:-len(key)-1]
                inputext = key
                break
        else:
            raise InputFileError('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobspecs.progname)
    elif filepath.isdir():
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'es un directorio')
    elif filepath.exists():
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'no es un archivo regular')
    else:
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'no existe')
    if interpolate:
        templatename = inputname
        inputname = '.'.join((jobprefix, inputname))
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (templatename, key))):
                    with open(pathjoin(inputdir, (templatename, key)), 'r') as fr, open(pathjoin(inputdir, (inputname, key)), 'w') as fw:
                        try:
                            fw.write(fr.read().format(**keywords))
                        except KeyError as e:
                            raise InputFileError('No se definió la variable de interpolación', q(e.args[0]), 'del archivo de entrada', pathjoin((templatename, key)))
    return inputdir, inputname, inputext

@catch_keyboard_interrupt
def wait():
    sleep(options.wait)

@catch_keyboard_interrupt
def connect():
    cluster.remoteshare = check_output(['ssh', remote_run, 'echo', '-n', '$JOBSHARE']).decode(sys.stdout.encoding)
    if not cluster.remoteshare:
        messages.runerror('El servidor remoto no acepta trabajos de otro servidor')
        

@catch_keyboard_interrupt
def remoterun():
    if remotefiles:
        execv('/usr/bin/ssh', [__file__, '-t', remote_run] + ['{}={}'.format(envar, value) for envar, value in envars.items()] + [program] + ['--{}'.format(option) if value is True else '--{}={}'.format(option, value) for option, value in vars(options).items() if value] + remotefiles)

@catch_keyboard_interrupt
def dryrun():
    try:
        inputdir, inputname, inputext = nextfile()
    except InputFileError as e:
        messages.failure(e)
        return

@catch_keyboard_interrupt
def upload():
    try:
        inputdir, inputname, inputext = nextfile()
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
    call(['rsync', '-qRtz'] + transferlist + [remote_run + ':' + pathjoin(cluster.remoteshare, userhost)])

@catch_keyboard_interrupt
def setup():

    if not jobspecs.scheduler:
        messages.cfgerror('No se especificó el nombre del sistema de colas (scheduler)')
    
    if getattr(options, 'ignore-defaults'):
        jobspecs.defaults.pop('version')
    
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
        try:
            script.workdir = AbsPath(options.scrdir, jobenvars.jobid)
        except NotAbsolutePath:
            script.workdir = AbsPath(getcwd(), options.scrdir, jobenvars.jobid)
    else:
        try:
            script.workdir = AbsPath(jobspecs.defaults.scratchdir, jobenvars.jobid)
        except NotAbsolutePath:
            messages.cfgerror(jobspecs.defaults.scratchdir, 'no es una ruta absoluta (scratchdir)')

    script.comments = []
    script.environ = []
    script.command = []

    if not options.queue:
        if jobspecs.defaults.queue:
            options.queue = jobspecs.defaults.queue
        else:
            messages.cfgerror('No se especificó la cola por defecto (default:queue)')
    
    if not jobspecs.progname:
        messages.cfgerror('No se especificó el nombre del programa (progname)')
    
    if not jobspecs.progkey:
        messages.cfgerror('No se especificó la clave del programa (progkey)')
    
    if 'mpilauncher' in jobspecs:
        try: jobspecs.mpilauncher = boolstrs[jobspecs.mpilauncher]
        except KeyError:
            messages.cfgerror('Este valor requiere ser "True" o "False" (mpilauncher)')
    
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
            script.comments.append(jobformat.nhost(options.nhost))
        elif jobspecs.parallelib.lower() == 'openmp':
            script.comments.append(jobformat.ncore(options.ncore))
            script.comments.append(jobformat.nhost(options.nhost))
            script.command.append('OMP_NUM_THREADS=' + str(options.ncore))
        elif jobspecs.parallelib.lower() in mpilibs:
            if not 'mpilauncher' in jobspecs:
                messages.cfgerror('No se especificó si el programa es lanzado por mpirun (mpilauncher)')
            script.comments.append(jobformat.ncore(options.ncore))
            script.comments.append(jobformat.nhost(options.nhost))
            if jobspecs.mpilauncher:
                script.command.append(scheduler.mpilauncher[jobspecs.parallelib])
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

    if options.version in jobspecs.versions:
        versionspec = jobspecs.versions[options.version]
    else:
       messages.opterror('La versión seleccionada no es válida')
    
    if not versionspec.executable:
        messages.cfgerror('No se especificó el ejecutable de la versión', options.version)
    
    script.environ.extend(jobspecs.onscript)

    for envar, path in jobspecs.export.items() | versionspec.export.items():
        try:
            abspath = AbsPath(path).kexpand(cluster)
        except NotAbsolutePath:
            abspath = AbsPath(path.format(workdir=script.workdir))
        script.environ.append('export {}={}'.format(envar, abspath))
    
    for path in jobspecs.source + versionspec.source:
        script.environ.append('source {}'.format(AbsPath(path).kexpand(cluster)))
    
    for module in jobspecs.load + versionspec.load:
        script.environ.append('module load {}'.format(module))
    
    try:
        script.command.append(AbsPath(versionspec.executable).kexpand(cluster))
    except NotAbsolutePath:
        script.command.append(versionspec.executable)

    script.comments.append(jobformat.label(jobspecs.progname))
    script.comments.append(jobformat.queue(options.queue))
    script.comments.append(jobformat.output(AbsPath(jobspecs.logdir).kexpand(cluster)))
    script.comments.append(jobformat.error(AbsPath(jobspecs.logdir).kexpand(cluster)))
    
    if options.node:
        script.comments.append(jobformat.hosts(options.node))
    
    script.environ.append("shopt -s nullglob extglob")
    script.environ.append("head=" + cluster.head)
    script.environ.extend('='.join(i) for i in jobenvars.items())
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
        script.mkdir = 'mkdir -p -m 700 "{}"'.format
        script.rmdir = 'rm -rf "{}"'.format
        script.fetch = 'cp "{}" "{}"'.format
        script.fetch = 'cp "{}" "{}"'.format
        script.fetchdir = 'cp -r "{}/." "{}"'.format
        script.remit = 'cp "{}" "{}"'.format
    elif jobspecs.hostcopy == 'remote':
        script.mkdir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -p -m 700 "\'{0}\'"; done'.format
        script.rmdir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'{0}\'"; done'.format
        script.fetch = 'for host in ${{hosts[*]}}; do scp $head:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.fetchdir = 'for host in ${{hosts[*]}}; do ssh $head tar -cf- -C "\'{0}\'" . | ssh $host tar -xf- -C "\'{1}\'"; done'.format
        script.remit = 'scp "{}" $head:"\'{}\'"'.format
    else:
        messages.cfgerror('El método de copia', q(jobspecs.hostcopy), 'no es válido')
    
@catch_keyboard_interrupt
def localrun():

    try:
        inputdir, inputname, inputext = nextfile()
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
    
    progkey = jobspecs.progkey + alnum(options.version)

    if inputname.endswith('.' + progkey):
        jobname = inputname[:-len(progkey)-1]
    elif inputname.endswith('.' + jobspecs.progkey):
        jobname = inputname[:-len(jobspecs.progkey)-1]
    else:
        jobname = inputname

    for parkey in jobspecs.parameters:
        if parkey + 'path' in options:
            try:
                rootpath = AbsPath(getattr(options, parkey + 'path'))
            except NotAbsolutePath:
                rootpath = AbsPath(getcwd(), getattr(options, parkey + 'path'))
        elif parkey in jobspecs.defaults.parameters:
            try:
                abspath = AbsPath(jobspecs.defaults.parameters[parkey])
            except NotAbsolutePath:
                abspath = AbsPath(getcwd(), jobspecs.defaults.parameters[parkey])
            rootpath = AbsPath('/')
            defaults = getattr(options, parkey + 'set').split(':') if parkey + 'set' in options else []
            for prefix, suffix, default in abspath.setkeys(cluster).splitkeys(defaults):
                if default and not getattr(options, 'ignore-defaults'):
                    rootpath = rootpath.joinpath(prefix, default, suffix)
                else:
                    choices = diritems(rootpath.joinpath(prefix))
                    choice = dialogs.chooseone('Seleccione un conjunto de parámetros para el trabajo', jobname, p(parkey), choices=choices)
                    rootpath = rootpath.joinpath(prefix, choice, suffix)
        else:
            messages.opterror('Debe indicar la ruta al directorio de parámetros', p(parkey))
        if rootpath.exists():
            parameters.append(rootpath)
        else:
            messages.opterror('La ruta', rootpath, 'no existe', p(parkey))
    
    if options.outdir:
        try:
            outputdir = AbsPath(options.outdir)
        except NotAbsolutePath:
            outputdir = AbsPath(inputdir, options.outdir)
    else:
        try:
            outputdir = AbsPath(jobspecs.defaults.outputdir).kexpand(dict(jobname=jobname))
        except NotAbsolutePath:
            outputdir = AbsPath(inputdir, jobspecs.defaults.outputdir).kexpand(dict(jobname=jobname))

    hiddendir = AbsPath(outputdir, '.' + jobname + '.' + progkey)
    outputname = jobname + '.' + progkey

    inputfiles = []
    inputdirs = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            if path.isfile(pathjoin(inputdir, (inputname, key))):
                inputfiles.append(((pathjoin(outputdir, (jobname, key))), pathjoin(script.workdir, jobspecs.filekeys[key])))
    
    for parameter in parameters:
        if parameter.isfile():
            inputfiles.append((parameter, pathjoin(script.workdir, parameter)))
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
                    jobstate = scheduler.checkjob(jobid)
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
    
    if inputdir != outputdir:
        action = path.rename if options.move else copyfile
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (inputname, key))):
                    action(pathjoin(inputdir, (inputname, key)), pathjoin(outputdir, (jobname, key)))
    
    script.comments.append(jobformat.name(jobname))

    offscript = []

    for line in jobspecs.offscript:
        try:
           offscript.append(line.format(jobname=jobname, clustername=cluster.name, **envars))
        except KeyError:
           pass

    jobscript = pathjoin(hiddendir, 'jobscript')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash' + '\n')
        f.write(''.join(i + '\n' for i in script.comments))
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
        jobid = scheduler.queuejob(jobscript)
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

