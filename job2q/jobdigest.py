# -*- coding: utf-8 -*-
import sys
from importlib import import_module
from os import listdir, getcwd
from argparse import ArgumentParser
from . import dialogs
from . import messages
from .details import mpilibs
from .classes import Bunch, AbsPath
from .utils import natsort, p, q, sq, boolstrings, join_positional_args, wordseps
from .jobparse import cluster, jobspecs, options, files
from .exceptions import NotAbsolutePath
from .chemistry import readxyz

def digest():

    if not jobspecs.scheduler:
        messages.cfgerror('<scheduler> No se especificó el nombre del sistema de colas')
    
    environment.extend(jobspecs.onscript)

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
            messages.cfgerror('No se especificó el directorio temporal de escritura "scrdir"')
    
    try:
        options.scrdir = AbsPath(options.scrdir, **cluster)
    except NotAbsolutePath:
        messages.cfgerror('La opción "scrdir" debe ser una ruta absoluta')
    
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
    
    #TODO: MPI support for Slurm
    if jobspecs.parallelib:
        if jobspecs.parallelib.lower() == 'none':
            jobcomments.append(jobformat.nhost(options.nhost))
        elif jobspecs.parallelib.lower() == 'openmp':
            jobcomments.append(jobformat.ncore(options.ncore))
            jobcomments.append(jobformat.nhost(options.nhost))
            commandline.append('OMP_NUM_THREADS=' + str(options.ncore))
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

    versionspec = jobspecs.versions[options.version]
    
    if not versionspec.executable:
        messages.cfgerror('No se especificó el ejecutable de la versión', options.version)
    
    for key, value in jobspecs.export.items():
        environment.append('export {}={}'.format(key, value.format(**cluster)))
    
    for key, value in versionspec.export.items():
        environment.append('export {}={}'.format(key, value.format(**cluster)))
    
    for srcfile in jobspecs.source + versionspec.source:
        environment.append('source {}'.format(AbsPath(srcfile, **cluster)))
    
    for module in jobspecs.load + versionspec.load:
        environment.append('module load {}'.format(module))
    
    try:
        commandline.append(AbsPath(versionspec.executable, **cluster))
    except NotAbsolutePath:
        commandline.append(versionspec.executable)
    
    jobspecs.logdir = jobspecs.logdir.format(**cluster)

    jobcomments.append(jobformat.label(jobspecs.progname))
    jobcomments.append(jobformat.queue(options.queue))
    jobcomments.append(jobformat.output(jobspecs.logdir))
    jobcomments.append(jobformat.error(jobspecs.logdir))
    
    if options.node:
        jobcomments.append(jobformat.hosts(options.node))
    
    environment.append("shopt -s nullglob extglob")
    environment.append("head=" + cluster.head)
    environment.extend('='.join(i) for i in jobenvars.items())
    environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    environment.append("jobram=$(($ncore*$totalram/$(nproc --all)))")
    
    for var in jobspecs.filevars:
        environment.append(var + '=' + sq(jobspecs.filekeys[jobspecs.filevars[var]]))
    
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
    if 'stderror' in jobspecs:
        try: commandline.append('2>' + ' ' + jobspecs.filekeys[jobspecs.stderror])
        except KeyError: messages.cfgerror('El nombre de archivo "' + jobspecs.stderror + '" en el tag <error> no fue definido.')
    
    for key in jobspecs.keywords:
        if options[key] is not None:
            keywords[key] = options[key]

    if options.template and options.molfile:
        try:
            molfile = AbsPath(options.molfile)
        except NotAbsolutePath:
            molfile = AbsPath(getcwd(), options.molfile)
        if molfile.isfile():
            if molfile.hasext('.xyz'):
                keywords['mol0'] = molfile
                for i, step in enumerate(readxyz(molfile), 1):
                    keywords['mol' + str(i)] = '\n'.join('{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format(*atom) for atom in step['coords'])
                if not options.jobname:
                    options.jobname = molfile.stem
            else:
                messages.opterror('Solamente están soportados archivos de coordenadas en formato xyz')
        elif molfile.isdir():
            messages.opterror('El archivo de coordenadas', molfile, 'es un directorio')
        elif molfile.exists():
            messages.opterror('El archivo de coordenadas', molfile, 'no es un archivo regular')
        else:
            messages.opterror('El archivo de coordenadas', molfile, 'no existe')
    elif options.template and not options.molfile and not options.jobname:
        messages.opterror('Se debe especificar el archivo de coordenadas o el nombre del trabajo para interpolar el archivo de entrada')
    elif options.molfile and not options.template:
        messages.warning('Se especificó un archivo de coordenadas pero no se solicitó interpolar el archivo de entrada')
        
    node.workdir = AbsPath(options.scrdir, jobenvars.jobid)

    node.chdir = 'cd "{}"'.format
    head.run = 'ssh $head "{}"'.format
    if jobspecs.hostcopy == 'local':
        node.mkdir = 'mkdir -p -m 700 "{}"'.format
        node.deletedir = 'rm -rf "{}"'.format
        node.fetch = 'cp "{}" "{}"'.format
        head.fetch = 'cp "{}" "{}"'.format
    elif jobspecs.hostcopy == 'remote':
        node.mkdir = 'mkdir -p -m 700 "{0}"\nfor host in ${{hosts[*]}}; do ssh $host mkdir -p -m 700 "\'{0}\'"; done'.format
        node.deletedir = 'rm -rf "{0}"\nfor host in ${{hosts[*]}}; do ssh $host rm -rf "\'{0}\'"; done'.format
        node.fetch = 'scp $head:"\'{0}\'" "{1}"\nfor host in ${{hosts[*]}}; do scp $head:"\'{0}\'" $host:"\'{1}\'"; done'.format
        head.fetch = 'scp "{}" $head:"\'{}\'"'.format
    elif jobspecs.hostcopy == 'jump':
        node.mkdir = 'mkdir -p -m 700 "{0}"\nfor host in ${{hosts[*]}}; do ssh $head ssh $host mkdir -pm 700 "\'{0}\'"; done'.format
        node.deletedir = 'rm -rf "{0}"\nfor host in ${{hosts[*]}}; do ssh $head ssh $host rm -rf "\'{0}\'"; done'.format
        node.fetch = 'scp $head:"\'{0}\'" "{1}"\nfor host in ${{hosts[*]}}; do ssh $head scp "\'{0}\'" $host:"\'{1}\'"; done'.format
        head.fetch = 'scp "{}" $head:"\'{}\'"'.format
    else:
        messages.cfgerror('El método de copia', q(jobspecs.hostcopy), 'no es válido')
    
keywords = {}
jobcomments = []
environment = []
commandline = []
parameters = []
head = Bunch({})
node = Bunch({})
