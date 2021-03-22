# -*- coding: utf-8 -*-
from string import Template
from . import dialogs, messages
from .queue import submitjob, checkjob
from .fileutils import AbsPath, NotAbsolutePath, diritems, buildpath, remove, makedirs, copyfile
from .utils import Bunch, IdentityList, natural, natsort, o, p, q, Q, join_args, boolstrs, removesuffix
from .shared import names, environ, hostspecs, jobspecs, options
from .details import mpilibs


def setup():

    script.header = []
    script.setup = []
    script.envars = []
    script.main = []

    if not hostspecs.scheduler:
        messages.error('No se especificó el nombre del sistema de colas', spec='scheduler')
    
    if options.common.ignore_defaults:
        jobspecs.defaults.pop('version', None)
        jobspecs.defaults.pop('parameterset', None)
    
    if 'wait' not in options.common:
        try:
            options.common.wait = float(hostspecs.defaults.wait)
        except AttributeError:
            options.common.wait = 0
    
    if 'nhost' not in options.common:
        options.common.nhost = 1

#TODO: Add suport for dialog boxes
#    if options.common.xdialog:
#        try:
#            from bulletin import TkDialogs
#        except ImportError:
#            raise SystemExit()
#        else:
#            dialogs.yesno = join_args(TkDialogs().yesno)
#            messages.failure = join_args(TkDialogs().message)
#            messages.success = join_args(TkDialogs().message)

    if not 'scratchdir' in hostspecs.defaults:
        messages.error('No se especificó el directorio temporal de escritura por defecto', spec='defaults.scratchdir')

    if 'scratch' in options.common:
        script.scrdir = AbsPath(buildpath(options.common.scratch, hostspecs.envars.jobid))
    else:
        try:
            script.scrdir = AbsPath(buildpath(hostspecs.defaults.scratchdir, hostspecs.envars.jobid)).setkeys(names).validate()
        except NotAbsolutePath:
            messages.error(hostspecs.defaults.scratchdir, 'no es una ruta absoluta', spec='defaults.scratchdir')

    if 'queue' not in options.common:
        if hostspecs.defaults.queue:
            options.common.queue = hostspecs.defaults.queue
        else:
            messages.error('No se especificó la cola por defecto', spec='defaults.queue')
    
    if not 'packagename' in jobspecs:
        messages.error('No se especificó el nombre del programa', spec='packagename')
    
    if not 'packagefix' in jobspecs:
        messages.error('No se especificó el sufijo del programa', spec='packagefix')
    
    if not 'jobdir' in jobspecs.defaults:
        messages.error('No se especificó el directorio de salida por defecto', spec='defaults.jobdir')

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
        for key in jobspecs.inputfiles:
            if not key in jobspecs.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='inputfiles')
    else:
        messages.error('La lista de archivos de entrada no existe o está vacía', spec='inputfiles')
    
    if jobspecs.outputfiles:
        for key in jobspecs.outputfiles:
            if not key in jobspecs.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='outputfiles')
    else:
        messages.error('La lista de archivos de salida no existe o está vacía', spec='outputfiles')

    if 'metadata' in hostspecs:
        for item in hostspecs.metadata:
            script.header.append(item.format(**jobspecs))

    #TODO: MPI support for Slurm
    if jobspecs.parallelib:
        if jobspecs.parallelib.lower() == 'none':
            for item in hostspecs.serial:
                script.header.append(item.format(**options.common))
        elif jobspecs.parallelib.lower() == 'openmp':
            for item in hostspecs.parallelin:
                script.header.append(item.format(**options.common))
            script.main.append('OMP_NUM_THREADS=' + str(options.common.nproc))
        elif jobspecs.parallelib.lower() in mpilibs:
            if not 'mpilaunch' in jobspecs:
                messages.error('No se especificó si el programa debe ser ejecutado por mpirun', spec='mpilaunch')
            for item in hostspecs.parallel:
                script.header.append(item.format(**options.common))
            if jobspecs.mpilaunch:
                script.main.append(hostspecs.mpilauncher[jobspecs.parallelib])
        # Parallel at requested hosts
#        elif 'hosts' in options.common:
#            for item in hostspecs.parallelat:
#                script.header.append(item.format(**options.common))
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
    
    for envar, path in jobspecs.export.items() | jobspecs.versions[options.common.version].export.items():
        abspath = AbsPath(path, cwd=script.scrdir).setkeys(names).validate()
        script.setup.append('export {0}={1}'.format(envar, abspath))

    for envar, path in jobspecs.append.items() | jobspecs.versions[options.common.version].append.items():
        abspath = AbsPath(path, cwd=script.scrdir).setkeys(names).validate()
        script.setup.append('{0}={1}:${0}'.format(envar, abspath))

    for path in jobspecs.source + jobspecs.versions[options.common.version].source:
        script.setup.append('source {}'.format(AbsPath(path).setkeys(names).validate()))

    if jobspecs.load or jobspecs.versions[options.common.version].load:
        script.setup.append('module purge')

    for module in jobspecs.load + jobspecs.versions[options.common.version].load:
        script.setup.append('module load {}'.format(module))

    try:
        script.main.append(AbsPath(jobspecs.versions[options.common.version].executable).setkeys(names).validate())
    except NotAbsolutePath:
        script.main.append(jobspecs.versions[options.common.version].executable)

    logdir = AbsPath(hostspecs.logdir).setkeys(names).validate()
    for item in hostspecs.logging:
        script.header.append(item.format(logdir=logdir))

    script.setup.append("shopt -s nullglob extglob")

    script.setenv = '{}="{}"'.format

    script.envars.extend(names.items())
    script.envars.extend(hostspecs.envars.items())
    script.envars.extend((i, jobspecs.filekeys[i]) for i in jobspecs.filevars)

    script.envars.append(("freeram", "$(free -m | tail -n+3 | head -1 | awk '{print $4}')"))
    script.envars.append(("totalram", "$(free -m | tail -n+2 | head -1 | awk '{print $2}')"))
    script.envars.append(("jobram", "$(($nproc*$totalram/$(nproc --all)))"))

    for key in jobspecs.optionargs:
        if not jobspecs.optionargs[key] in jobspecs.filekeys:
            messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='optionargs')
        script.main.append('-{key} {val}'.format(key=key, val=jobspecs.filekeys[jobspecs.optionargs[key]]))
    
    for item in jobspecs.positionargs:
        for key in item.split('|'):
            if not key in jobspecs.filekeys:
                messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='positionargs')
        script.main.append('@' + p('|'.join(jobspecs.filekeys[i] for i in item.split('|'))))
    
    if 'stdinput' in jobspecs:
        try:
            script.main.append('0<' + ' ' + jobspecs.filekeys[jobspecs.stdinput])
        except KeyError:
            messages.error('La clave', q(jobspecs.stdinput) ,'no tiene asociado ningún archivo', spec='stdinput')
    if 'stdoutput' in jobspecs:
        try:
            script.main.append('1>' + ' ' + jobspecs.filekeys[jobspecs.stdoutput])
        except KeyError:
            messages.error('La clave', q(jobspecs.stdoutput) ,'no tiene asociado ningún archivo', spec='stdoutput')
    if 'stderror' in jobspecs:
        try:
            script.main.append('2>' + ' ' + jobspecs.filekeys[jobspecs.stderror])
        except KeyError:
            messages.error('La clave', q(jobspecs.stderror) ,'no tiene asociado ningún archivo', spec='stderror')
    
    script.chdir = 'cd "{}"'.format
    script.execute = 'ssh $head "{}"'.format
    if hostspecs.filesync == 'local':
        script.rmdir = 'rm -rf "{}"'.format
        script.mkdir = 'mkdir -p -m 700 "{}"'.format
        script.fetch = 'mv "{}" "{}"'.format
        script.fetchdir = 'cp -r "{}/." "{}"'.format
        script.remit = 'cp "{}" "{}"'.format
    elif hostspecs.filesync == 'remote':
        script.rmdir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'{}\'"; done'.format
        script.mkdir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.fetch = 'for host in ${{hosts[*]}}; do scp $head:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.fetchdir = 'for host in ${{hosts[*]}}; do ssh $head tar -cf- -C "\'{0}\'" . | ssh $host tar -xf- -C "\'{1}\'"; done'.format
        script.remit = 'scp "{}" $head:"\'{}\'"'.format
    else:
        messages.error('El método de copia', q(hostspecs.filesync), 'no es válido', spec='filesync')

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
#            rootpath = AbsPath(getattr(options.parameterpaths, key + '-path'), cwd=options.common.workdir)
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
            pathcomponents = AbsPath(jobspecs.defaults.parameterpath[key], cwd=options.common.workdir).setkeys(names).populate()
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

    names.job = removesuffix(basename, '.' + jobspecs.packagefix)

    if 'prefix' in options.common:
        names.job = options.common.prefix + '.' + names.job

    if 'suffix' in options.common:
        names.job = names.job + '.' + options.common.suffix

    if 'jobdir' in options.common:
        jobdir = AbsPath(options.common.jobdir, cwd=parentdir)
    else:
        jobdir = AbsPath(jobspecs.defaults.jobdir, cwd=parentdir).setkeys(names).validate()

#TODO: Prepend program version to extension of output files if option is enabled
    progfix = jobspecs.packagefix + '.'.join(options.common.version.split())

    hiddendir = AbsPath(buildpath(jobdir, '.' + progfix))

    inputfiles = []
    inputdirs = []

    for key in jobspecs.inputfiles:
        if AbsPath(buildpath(parentdir, (basename, key))).isfile():
            inputfiles.append((buildpath(jobdir, (names.job, key)), buildpath(script.scrdir, jobspecs.filekeys[key])))
    
    for path in parameterpaths:
        if path.isfile():
            inputfiles.append((path, buildpath(script.scrdir, path.name)))
        elif path.isdir():
            inputdirs.append((buildpath(path), script.scrdir))

    outputfiles = []

    for key in jobspecs.outputfiles:
        outputfiles.append((buildpath(script.scrdir, jobspecs.filekeys[key]), buildpath(jobdir, (names.job, key))))
    
    if jobdir.isdir():
        if hiddendir.isdir():
            try:
                with open(buildpath(hiddendir, 'jobid'), 'r') as f:
                    jobid = f.read()
                jobstate = checkjob(jobid)
                if jobstate is not None:
                    messages.failure(jobstate.format(id=jobid, name=names.job))
                    return
            except FileNotFoundError:
                pass
        elif hiddendir.exists():
            messages.failure('No se puede crear la carpeta', hiddendir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(hiddendir)
        if not set(jobdir.listdir()).isdisjoint(buildpath((names.job, k)) for k in jobspecs.outputfiles):
            if options.common.no or (not options.common.yes and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', jobdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                messages.failure('Cancelado por el usuario')
                return
        for key in jobspecs.outputfiles:
            remove(buildpath(jobdir, (names.job, key)))
        if parentdir != jobdir:
            for key in jobspecs.inputfiles:
                remove(buildpath(jobdir, (names.job, key)))
    elif jobdir.exists():
        messages.failure('No se puede crear la carpeta', jobdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(jobdir)
        makedirs(hiddendir)
    
    for key in jobspecs.inputfiles:
        inputpath = AbsPath(buildpath(parentdir, (basename, key)))
        if inputpath.isfile():
            if options.common.interpolate and 'interpolable' in jobspecs and key in jobspecs.interpolable:
                with open(inputpath, 'r') as fr:
                    template = fr.read()
                try:
                    substituted = Template(template).substitute(options.keywords)
                except ValueError:
                    messages.failure('Hay variables de interpolación inválidas en el archivo de entrada', buildpath((basename, key)))
                    return
                except KeyError as e:
                    messages.failure('Hay variables de interpolación indefinidas en el archivo de entrada', buildpath((basename, key)), option=o(e.args[0]))
                    return
                with open(buildpath(jobdir, (names.job, key)), 'w') as fw:
                    fw.write(substituted)
            else:
                inputpath.copyto(buildpath(jobdir, (names.job, key)))
            if options.common.delete:
                remove(buildpath(parentdir, (basename, key)))

    jobscript = buildpath(hiddendir, 'jobscript')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash' + '\n')
        f.write(''.join(i + '\n' for i in script.header))
        f.write(hostspecs.title.format(names.job) + '\n')
        f.write(''.join(i + '\n' for i in script.setup))
        f.write(''.join(script.setenv(i, j) + '\n' for i, j in script.envars))
        f.write(script.setenv('job', names.job) + '\n')
        f.write('for host in ${hosts[*]}; do echo "<$host>"; done' + '\n')
        f.write(script.mkdir(script.scrdir) + '\n')
        f.write(''.join(script.fetch(i, j) + '\n' for i, j in inputfiles))
        f.write(''.join(script.fetchdir(i, j) + '\n' for i, j in inputdirs))
        f.write(script.chdir(script.scrdir) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.prescript))
        f.write(' '.join(script.main) + '\n')
        f.write(''.join(i + '\n' for i in jobspecs.postscript))
        f.write(''.join(script.remit(i, j) + '\n' for i, j in outputfiles))
        f.write(script.rmdir(script.scrdir) + '\n')
        f.write(''.join(i + '\n' for i in hostspecs.offscript))

    if options.common.dry:
        messages.success('Se procesó el trabajo', q(names.job), 'y se generaron los archivos para el envío en', hiddendir, option='--dry')
    else:
        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            messages.failure('El sistema de reportó un error al enviar el trabajo', q(names.job), p(error))
            return
        else:
            messages.success('El trabajo', q(names.job), 'se correrá en', str(options.common.nproc), 'núcleo(s) en', names.cluster, 'con número de trabajo', jobid)
            with open(buildpath(hiddendir, 'jobid'), 'w') as f:
                f.write(jobid)
    
parameterpaths = []
script = Bunch()

