# -*- coding: utf-8 -*-
import re
import sys
from os import getcwd
from string import Formatter
from . import dialogs
from . import messages
from .queue import submitjob, checkjob
from .fileutils import AbsPath, NotAbsolutePath, diritems, buildpath, remove, makedirs, copyfile
from .utils import Bunch, IdentityList, natural, natsort, o, p, q, Q, join_args, boolstrs, removesuffix
from .shared import sysinfo, envars, jobspecs, options
from .details import mpilibs


def setup():

    script.environ = []
    script.command = []
    script.qctrl = []

    if not jobspecs.scheduler:
        messages.error('No se especificó el nombre del sistema de colas', spec='scheduler')
    
    if options.common.defaults:
        jobspecs.defaults.get('version', None)
        jobspecs.defaults.get('parameterset', None)
    
    if 'wait' not in options.common:
        try:
            options.common.wait = float(jobspecs.defaults.waitime)
        except AttributeError:
            options.common.wait = 0
    
    if 'nproc' not in options.common:
        options.common.nproc = 1
    
    if 'nhost' not in options.common:
        options.common.nhost = 1

    if options.common.xdialog:
        try:
            from bulletin import TkDialogs
        except ImportError:
            raise SystemExit()
        else:
            dialogs.yesno = join_args(TkDialogs().yesno)
            messages.failure = join_args(TkDialogs().message)
            messages.success = join_args(TkDialogs().message)

    if not 'outdir' in jobspecs.defaults:
        messages.error('No se especificó el directorio de salida por defecto', spec='defaults.outdir')

    if not 'scratchdir' in jobspecs.defaults:
        messages.error('No se especificó el directorio temporal de escritura por defecto', spec='defaults.scratchdir')

    if 'scratch' in options.common:
        script.workdir = AbsPath(buildpath(options.common.scratch, jobspecs.qenv.jobid))
    else:
        try:
            script.workdir = AbsPath(buildpath(jobspecs.defaults.scratchdir, jobspecs.qenv.jobid)).setkeys(sysinfo).validate()
        except NotAbsolutePath:
            messages.error(jobspecs.defaults.scratchdir, 'no es una ruta absoluta', spec='defaults.scratchdir')

    if 'queue' not in options.common:
        if jobspecs.defaults.queue:
            options.common.queue = jobspecs.defaults.queue
        else:
            messages.error('No se especificó la cola por defecto', spec='defaults.queue')
    
    if not jobspecs.progname:
        messages.error('No se especificó el nombre del programa', spec='progname')
    
    if not jobspecs.progkey:
        messages.error('No se especificó la clave del programa', spec='progkey')
    
    for key in options.parameters:
        if '/' in options.parameters[key]:
            messages.error(options.parameters[key], 'no puede ser una ruta', option=key)

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
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.common.nhost))
        elif jobspecs.parallelib.lower() == 'openmp':
            script.qctrl.append(jobspecs.qctrl.nproc.format(options.common.nproc))
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.common.nhost))
            script.command.append('OMP_NUM_THREADS=' + str(options.common.nproc))
        elif jobspecs.parallelib.lower() in mpilibs:
            if not 'mpilaunch' in jobspecs:
                messages.error('No se especificó si el programa debe ser ejecutado por mpirun', spec='mpilaunch')
            script.qctrl.append(jobspecs.qctrl.nproc.format(options.common.nproc))
            script.qctrl.append(jobspecs.qctrl.nhost.format(options.common.nhost))
            if jobspecs.mpilaunch:
                script.command.append(jobspecs.mpilauncher[jobspecs.parallelib])
        else:
            messages.error('El tipo de paralelización', jobspecs.parallelib, 'no está soportado', spec='parallelib')
    else:
        messages.error('No se especificó el tipo de paralelización del programa', spec='parallelib')
    
    if jobspecs.versions:
        if 'version' not in options.common:
            if 'version' in jobspecs.defaults:
                if jobspecs.defaults.version in jobspecs.versions:
                    options.common.version = jobspecs.defaults.version
                else:
                    messages.error('La versión establecida por defecto es inválida', spec='defaults.version')
            else:
                options.common.version = dialogs.chooseone('Seleccione una versión', choices=natsort(jobspecs.versions.keys()))
        if options.common.version not in jobspecs.versions:
            messages.error('La versión', options.common.version, 'no es válida', option='version')
    else:
        messages.error('La lista de versiones no existe o está vacía', spec='versions')

    if not jobspecs.versions[options.common.version].executable:
        messages.error('No se especificó el ejecutable', spec='versions[{}].executable'.format(options.common.version))
    
    script.environ.extend(jobspecs.onscript)

    for envar, path in jobspecs.export.items() | jobspecs.versions[options.common.version].export.items():
        abspath = AbsPath(path, cwd=script.workdir).setkeys(sysinfo).validate()
        script.environ.append('export {}={}'.format(envar, abspath))
    
    for path in jobspecs.source + jobspecs.versions[options.common.version].source:
        script.environ.append('source {}'.format(AbsPath(path).setkeys(sysinfo).validate()))
    
    for module in jobspecs.load + jobspecs.versions[options.common.version].load:
        script.environ.append('module load {}'.format(module))
    
    try:
        script.command.append(AbsPath(jobspecs.versions[options.common.version].executable).setkeys(sysinfo).validate())
    except NotAbsolutePath:
        script.command.append(jobspecs.versions[options.common.version].executable)

    script.qctrl.append(jobspecs.qctrl.label.format(jobspecs.progname))
    script.qctrl.append(jobspecs.qctrl.queue.format(options.common.queue))
    script.qctrl.append(jobspecs.qctrl.output.format(AbsPath(jobspecs.logdir).setkeys(sysinfo).validate()))
    script.qctrl.append(jobspecs.qctrl.error.format(AbsPath(jobspecs.logdir).setkeys(sysinfo).validate()))
    
    if 'nodes' in options.common:
        script.qctrl.append(jobspecs.qctrl.nodes.format(options.common.nodes))
    
    script.environ.append("shopt -s nullglob extglob")
    script.environ.append("head=" + sysinfo.headname)
    script.environ.extend('='.join(i) for i in jobspecs.qenv.items())
    script.environ.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    script.environ.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    script.environ.append("jobram=$(($nproc*$totalram/$(nproc --all)))")
    
    for var in jobspecs.filevars:
        script.environ.append(var + '=' + Q(jobspecs.filekeys[jobspecs.filevars[var]]))
    
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

#TODO: Check if variables in parameter sets match filter groups
#    if 'filter' in options.common:
#        pattern = re.compile(options.common.filter)
#        for item in jobspecs.parameters + [i + '-path' for i in jobspecs.parameters]:
#            if item in options.parameters or item in options.parameterpaths:
#                for key in Formatter().parse(getattr(options.parameters, item)):
#                    if key[1] is not None:
#                        try:
#                            if int(key[1]) not in range(pattern.groups()):
#                                messages.error('El nombre o ruta', getattr(options.parameters, key), 'contiene referencias no numéricas', option=key)
#                        except ValueError:
#                            messages.error('El nombre o ruta', getattr(options.parameters, key), 'contiene referencias fuera de rango', option=key)

#TODO: Use filter matchings groups to build the parameter list
#    for key in options.parameters:
#        for var in getattr(options.parameters, key).split(','): 
#            if var.startswith('%'):
#                parameterlist.append(match.groups(var[1:]))
#            else:
#                parameterlist.append(var[1:])

    for key in jobspecs.parameters:
#TODO: Replace --key-path options with single --addpath option
#        if key + '-path' in options.parameterpaths:
#            rootpath = AbsPath(getattr(options.parameterpaths, key + '-path'), cwd=options.common.cwd)
        if key in jobspecs.defaults.parameterpath:
            if key in options.parameters:
                parameterlist = options.parameters[key].split(',')
            elif 'parameterset' in jobspecs.defaults and key in jobspecs.defaults.parameterset:
                if isinstance(jobspecs.defaults.parameterset[key], (list, tuple)):
                    parameterlist = jobspecs.defaults.parameterset[key]
                else:
                    messages.error('La clave', key, 'no es una lista', spec='defaults.parameterset')
            else:
                parameterlist = []
            pathcomponents = AbsPath(jobspecs.defaults.parameterpath[key], cwd=options.common.cwd).setkeys(sysinfo).populate()
            rootpath = AbsPath(next(pathcomponents))
            for component in pathcomponents:
                try:
                    rootpath = rootpath.joinpath(component.format(*parameterlist))
                except IndexError:
                    choices = diritems(rootpath, component)
                    choice = dialogs.chooseone('Seleccione un conjunto de parámetros', p(key), choices=choices)
                    rootpath = rootpath.joinpath(choice)
        else:
            messages.error('El conjunto de parámetros seleccionado no existe', spec='defaults.parameterpath[{}]'.format(key))
        if rootpath.exists():
            parameterpaths.append(rootpath)
        else:
            messages.error('La ruta', rootpath, 'no existe', option='{}-path'.format(key), spec='defaults.parameterpath[{}]'.format(key))



def submit(parentdir, basename):

    for key in options.fileopts:
        options.fileopts[key].linkto(buildpath(parentdir, (basename, jobspecs.fileopts[key])))

    jobname = removesuffix(basename, '.' + jobspecs.progkey)

    if options.interpolation:
        jobname = options.common.molfix + '.' + jobname

    if 'suffix' in options.common:
        jobname = jobname + '.' + options.common.suffix

    if 'outdir' in options.common:
        outdir = AbsPath(options.common.outdir, cwd=parentdir)
    else:
        outdir = AbsPath(jobspecs.defaults.outdir, cwd=parentdir).setkeys({'jobname':jobname}).validate()

#TODO: Prepend program version to extension of output files if option is enabled
    progfix = jobspecs.progkey + '.'.join(options.common.version.split())

    hiddendir = AbsPath(buildpath(outdir, '.' + progfix))

    inputfiles = []
    inputdirs = []

    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            if AbsPath(buildpath(parentdir, (basename, key))).isfile():
                inputfiles.append(((buildpath(hiddendir, jobspecs.filekeys[key])), buildpath(script.workdir, jobspecs.filekeys[key])))
    
    for path in parameterpaths:
        if path.isfile():
            inputfiles.append((path, buildpath(script.workdir, path.name)))
        elif path.isdir():
            inputdirs.append((buildpath(path), script.workdir))

    outputfiles = []

    for item in jobspecs.outputfiles:
        for key in item.split('|'):
            outputfiles.append((buildpath(script.workdir, jobspecs.filekeys[key]), buildpath(outdir, (jobname, key))))
    
    if outdir.isdir():
        if hiddendir.isdir():
            try:
                with open(buildpath(hiddendir, 'jobid'), 'r') as f:
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
        if not set(outdir.listdir()).isdisjoint(buildpath((jobname, k)) for i in jobspecs.outputfiles for k in i.split('|')):
            if options.common.no or (not options.common.yes and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                messages.failure('Cancelado por el usuario')
                return
        for item in jobspecs.outputfiles:
            for key in item.split('|'):
                remove(buildpath(outdir, (jobname, key)))
        if parentdir != outdir:
            for item in jobspecs.inputfiles:
                for key in item.split('|'):
                    remove(buildpath(outdir, (jobname, key)))
    elif outdir.exists():
        messages.failure('No se puede crear la carpeta', outdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outdir)
        makedirs(hiddendir)
    
    for item in jobspecs.inputfiles:
        for key in item.split('|'):
            inputpath = AbsPath(buildpath(parentdir, (basename, key)))
            if inputpath.isfile():
                if options.interpolation:
                    with open(inputpath, 'r') as fr, open(buildpath(hiddendir, jobspecs.filekeys[key]), 'w') as fw:
                        try:
                            fw.write(fr.read().format(**options.keywords))
                        except KeyError as e:
                            messages.failure('No se definieron todas las variables de interpolación del archivo', buildpath([basename, key]), option=o(e.args[0]))
                            return
                else:
                    inputpath.copyto(buildpath(hiddendir, jobspecs.filekeys[key]))
                if options.common.delete:
                    remove(buildpath(parentdir, (basename, key)))
        
    script.qctrl.append(jobspecs.qctrl.name.format(jobname))

    offscript = []

    for line in jobspecs.offscript:
        try:
           offscript.append(line.format(jobname=jobname, clustername=sysinfo.clustername, **envars))
        except KeyError:
           pass

    jobscript = buildpath(hiddendir, 'jobscript')

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

    if options.common.dry:
        messages.success('Se procesó el trabajo', q(jobname), 'y se generaron los archivos para el envío en', hiddendir, option='--dry')
    else:
        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            messages.failure('El sistema de reportó un error al enviar el trabajo', q(jobname), p(error))
            return
        else:
            messages.success('El trabajo', q(jobname), 'se correrá en', str(options.common.nproc), 'núcleo(s) en', sysinfo.clustername, 'con número de trabajo', jobid)
            with open(buildpath(hiddendir, 'jobid'), 'w') as f:
                f.write(jobid)
    
parameterpaths = []
script = Bunch()

