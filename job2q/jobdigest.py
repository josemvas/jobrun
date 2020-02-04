# -*- coding: utf-8 -*-
import sys
from importlib import import_module
from os import path, listdir, getcwd
from argparse import ArgumentParser
from . import dialogs
from . import messages
from .details import mpilibs
from .classes import Bunch, AbsPath
from .utils import pathjoin, natsort, p, q, sq, boolstrings, join_positional_args, wordseps
from .jobparse import cluster, jobspecs, options, files
from .exceptions import NotAbsolutePath
from .chemistry import readxyz

def digest():

    if not jobspecs.scheduler:
        messages.cfgerror('<scheduler> No se especificó el nombre del sistema de colas')
    
    scheduler = import_module('.schedulers.' + jobspecs.scheduler, package='job2q')
    jobformat = Bunch(scheduler.jobformat)
    jobenvars = Bunch(scheduler.jobenvars)
    mpilauncher = scheduler.mpilauncher
    
    if options.sort:
        files.sort(key=natsort)
    elif options.sortrev:
        files.sort(key=natsort, reverse=True)
    
    if options.wait is None:
        try: options.wait = float(jobspecs.defaults.waitime)
        except AttributeError: options.wait = 0
    
    if options.xdialog:
        try:
            from bulletin import TkDialogs
        except ImportError:
            raise SystemExit()
        else:
            dialogs.yesno = join_positional_args(wordseps)(TkDialogs().yesno)
            messages.failure = join_positional_args(wordseps)(TkDialogs().message)
            messages.success = join_positional_args(wordseps)(TkDialogs().message)

    if not options.outdir and not jobspecs.defaults.outputdir:
        messages.cfgerror('Debe especificar la carpeta de salida por el programa no establece una por defecto')
            
    if not options.scrdir:
        if jobspecs.defaults.scrdir:
            options.scrdir = jobspecs.defaults.scrdir
        else:
            messages.cfgerror('<scrdir> No se especificó el directorio temporal de escritura por defecto')
    
    options.scrdir = AbsPath(options.scrdir)
    
    if not options.queue:
        if jobspecs.defaults.queue:
            options.queue = jobspecs.defaults.queue
        else:
            messages.cfgerror('<default><queue> No se especificó la cola por defecto')
    
    if not jobspecs.progname:
        messages.cfgerror('<title> No se especificó el nombre del programa')
    
    if not jobspecs.progkey:
        messages.cfgerror('<title> No se especificó la clave del programa')
    
    if 'mpilauncher' in jobspecs:
        try: jobspecs.mpilauncher = boolstrings[jobspecs.mpilauncher]
        except KeyError:
            messages.cfgerror('<mpilauncher> El texto de este tag debe ser "True" o "False"')
    
    if options.interactive:
        jobspecs.defaults = []
    
    if not jobspecs.filekeys:
        messages.cfgerror('<filekeys> La lista de archivos del programa no existe o está vacía')
    
    if jobspecs.inputfiles:
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if not key in jobspecs.filekeys:
                    messages.cfgerror('<inputfiles><e>{0}</e> El nombre de este archivo de entrada no fue definido'.format(key))
    else:
        messages.cfgerror('<inputfiles> La lista de archivos de entrada no existe o está vacía')
    
    if jobspecs.outputfiles:
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                if not key in jobspecs.filekeys:
                    messages.cfgerror('<otputfiles><e>{0}</e> El nombre de este archivo de salida no fue definido'.format(key))
    else:
        messages.cfgerror('<outputfiles> La lista de archivos de salida no existe o está vacía')
    
    if jobspecs.versions:
        if not options.version:
            if 'version' in jobspecs.defaults:
                if jobspecs.defaults.version in jobspecs.versions:
                    options.version = jobspecs.defaults.version
                else:
                    messages.opterror('La versión establecida por default es inválida')
            else:
                options.version = dialogs.chooseone('Seleccione una versión', choices=sorted(list(jobspecs.versions), key=natsort))
                if not options.version in jobspecs.versions:
                    messages.opterror('La versión seleccionada es inválida')
    else:
        messages.cfgerror('<versions> La lista de versiones no existe o está vacía')
    
    if not jobspecs.versions[options.version].executable:
        messages.cfgerror('No se especificó el ejecutable de la versión', options.version)
    
    executable = jobspecs.versions[options.version].executable
    profile = jobspecs.versions[options.version].profile
    
    for key in jobspecs.parameters:
        try:
            parameterdir = AbsPath(jobspecs.parameters[key], expand=True)
        except NotAbsolutePath:
            parameterdir = AbsPath(getcwd(), jobspecs.parameters[key], expand=True)
        try:
            items = parameterdir.listdir()
        except FileNotFoundError as e:
            messages.cfgerror('El directorio de parámetros', parameterdir, 'no existe')
        if not items:
            messages.cfgerror('El directorio de parámetros', parameterdir, 'está vacío')
        if options[key]:
            parameterset = options[key]
        else:
            if key in jobspecs.defaults.parameters:
                parameterset = jobspecs.defaults.parameters[key]
            else:
                parameterset = dialogs.chooseone('Seleccione un conjunto de parámetros', p(key), choices=sorted(items, key=natsort))
        if path.exists(path.join(parameterdir, parameterset)):
            parameters.append(path.join(parameterdir, parameterset))
        else:
            messages.opterror('La ruta de parámetros', path.join(parameterdir, parameterset), 'no existe')
    
    jobcomments.append(jobformat.label(jobspecs.progname))
    jobcomments.append(jobformat.queue(options.queue))
    jobcomments.append(jobformat.stdoutput(options.scrdir))
    jobcomments.append(jobformat.stderr(options.scrdir))
    
    if options.node:
        jobcomments.append(jobformat.hosts(options.node))
    
    #TODO: MPI support for Slurm
    if jobspecs.parallelib:
        if jobspecs.parallelib.lower() == 'none':
            jobcomments.append(jobformat.nhost(options.nhost))
        elif jobspecs.parallelib.lower() == 'openmp':
            jobcomments.append(jobformat.ncore(options.ncore))
            jobcomments.append(jobformat.nhost(options.nhost))
            environment.append('export OMP_NUM_THREADS=' + str(options.ncore))
        elif jobspecs.parallelib.lower() in mpilibs:
            if not 'mpilauncher' in jobspecs:
                messages.cfgerror('<mpilauncher> No se especificó si el programa es lanzado por mpirun')
            jobcomments.append(jobformat.ncore(options.ncore))
            jobcomments.append(jobformat.nhost(options.nhost))
            if jobspecs.mpilauncher:
                commandline.append(mpilauncher[jobspecs.parallelib])
        else:
            messages.cfgerror('El tipo de paralelización ' + jobspecs.parallelib + ' no está soportado')
    else:
        messages.cfgerror('<parallelib> No se especificó el tipo de paralelización del programa')
    
    environment.append("head=" + cluster.head)
    environment.extend('='.join(i) for i in jobenvars.items())
    environment.extend(jobspecs.onscript)
    
    for profile in jobspecs.profile + profile:
        environment.append(profile)
    
    for var in jobspecs.filevars:
        environment.append(var + '=' + sq(jobspecs.filekeys[jobspecs.filevars[var]]))
    
    environment.append("shopt -s nullglob extglob")
    environment.append("workdir=" + q(path.join(options.scrdir, jobenvars.jobid)))
    environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    environment.append("jobram=$(($ncore*$totalram/$(nproc --all)))")
    environment.append("progname=" + sq(jobspecs.progname))
    
    try:
        commandline.append(AbsPath(executable, expand=True))
    except NotAbsolutePath:
        commandline.append(executable)
    
    for key in jobspecs.optionargs:
        if not jobspecs.optionargs[key] in jobspecs.filekeys:
            messages.cfgerror('<optionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
        commandline.append('-{key} {val}'.format(key=key, val=jobspecs.filekeys[jobspecs.optionargs[key]]))
    
    for item in jobspecs.positionargs:
        for key in item.split('|'):
            if not key in jobspecs.filekeys:
                messages.cfgerror('<positionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
        commandline.append('@' + p('|'.join(jobspecs.filekeys[i] for i in item.split('|'))))
    
    if 'stdin' in jobspecs:
        try: commandline.append('0<' + ' ' + jobspecs.filekeys[jobspecs.stdin])
        except KeyError: messages.cfgerror('El nombre de archivo "' + jobspecs.stdin + '" en el tag <stdin> no fue definido.')
    if 'stdoutput' in jobspecs:
        try: commandline.append('1>' + ' ' + jobspecs.filekeys[jobspecs.stdoutput])
        except KeyError: messages.cfgerror('El nombre de archivo "' + jobspecs.stdoutput + '" en el tag <stdoutput> no fue definido.')
    if 'stderr' in jobspecs:
        try: commandline.append('2>' + ' ' + jobspecs.filekeys[jobspecs.stderr])
        except KeyError: messages.cfgerror('El nombre de archivo "' + jobspecs.stderr + '" en el tag <stderr> no fue definido.')
    
    for key in jobspecs.keywords:
        if key in options:
            keywords[key] = options[key]

    if options.template:
        if options.molfile:
            try:
                molpath = AbsPath(options.molfile)
            except NotAbsolutePath:
                molpath = AbsPath(getcwd(), options.molfile)
            if molpath.isfile():
                keywords['mol0'] = molpath
                if molpath.hasext('.xyz'):
                    for i, step in enumerate(readxyz(molpath), 1):
                        keywords['mol' + str(i)] = '\n'.join('{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format(*atom) for atom in step['coords'])
                    if not options.jobname:
                        options.jobname = molpath.stem
                else:
                    messages.opterror('Solamente están soportados archivos de coordenadas en formato xyz')
            elif molpath.isdir():
                messages.opterror('El archivo de coordenadas', molpath, 'es un directorio')
            elif molpath.exists():
                messages.opterror('El archivo de coordenadas', molpath, 'no es un archivo regular')
            else:
                messages.opterror('El archivo de coordenadas', molpath, 'no existe')
        elif not options.jobname:
            messages.opterror('Se debe especificar el archivo de coordenadas y/o el nombre del trabajo para poder interpolar')
        

keywords = {}
jobcomments = []
environment = []
remotefiles = []
commandline = []
parameters = []
