# -*- coding: utf-8 -*-
from string import Template
from . import dialogs, messages
from .queue import submitjob, checkjob
from .fileutils import AbsPath, NotAbsolutePath, buildpath, remove, makedirs, copyfile
from .utils import Bunch, IdentityList, natural, natsort, o, p, q, Q, join_args, boolstrs
from .shared import names, environ, hostspecs, jobspecs, options
from .details import mpilibs
from .readmol import readmol

def interpolate():
    if options.common.interpolate:
        for index, value in enumerate(options.common.interpolationlist, 1):
            options.interpolationdict['x' + str(index)] = value
        if options.common.mol:
            index = 0
            for path in options.common.mol:
                index += 1
                path = AbsPath(path, cwd=options.common.root)
                coords = readmol(path)[-1]
                options.interpolationdict['mol' + str(index)] = '\n'.join('{0:<2s}  {1:10.4f}  {2:10.4f}  {3:10.4f}'.format(*atom) for atom in coords)
            if not 'prefix' in options.common:
                if len(options.common.mol) == 1:
                    options.common.prefix = path.stem
                else:
                    messages.error('Se debe especificar un prefijo cuando se especifican múltiples archivos de coordenadas')
        elif 'trjmol' in options.common:
            index = 0
            path = AbsPath(options.common.molall, cwd=options.common.root)
            for coords in readmol(path):
                index += 1
                options.interpolationdict['mol' + str(index)] = '\n'.join('{0:<2s}  {1:10.4f}  {2:10.4f}  {3:10.4f}'.format(*atom) for atom in coords)
            prefix.append(path.stem)
            if not 'prefix' in options.common:
                options.common.prefix = path.stem
        else:
            if not 'prefix' in options.common and not 'suffix' in options.common:
                messages.error('Se debe especificar un prefijo o un sufijo para interpolar sin archivo coordenadas')
    else:
        if options.interpolationdict or options.common.interpolationlist or options.common.mol or 'trjmol' in options.common:
            messages.error('Se especificaron variables de interpolación pero no se va a interpolar nada')

def initialize():

    script.header = []
    script.setup = []
    script.envars = []
    script.main = []

    if not hostspecs.scheduler:
        messages.error('No se especificó el nombre del gestor de trabajos', spec='scheduler')
    
    if options.common.nodefaults:
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
#            from tkdialog import TkDialog
#        except ImportError:
#            raise SystemExit()
#        else:
#            dialogs.yesno = join_args(TkDialog().yesno)
#            messages.failure = join_args(TkDialog().message)
#            messages.success = join_args(TkDialog().message)

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
    
    if not 'packagekey' in jobspecs:
        messages.error('No se especificó el sufijo del programa', spec='packagekey')
    
    for key in options.parameters:
        if '/' in options.parameters[key]:
            messages.error(options.parameters[key], 'no puede ser una ruta', option=key)

    if 'mpilaunch' in jobspecs:
        try: jobspecs.mpilaunch = boolstrs[jobspecs.mpilaunch]
        except KeyError:
            messages.error('Este valor requiere ser "True" o "False"', spec='mpilaunch')
    
    if not jobspecs.filekeys:
        messages.error('La lista de archivos del programa no existe o está vacía', spec='filekeys')
    
    if jobspecs.infiles:
        for key in jobspecs.infiles:
            if not key in jobspecs.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='infiles')
    else:
        messages.error('La lista de archivos de entrada no existe o está vacía', spec='infiles')
    
    if jobspecs.outfiles:
        for key in jobspecs.outfiles:
            if not key in jobspecs.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='outfiles')
    else:
        messages.error('La lista de archivos de salida no existe o está vacía', spec='outfiles')

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

    for key in jobspecs.optargs:
        if not jobspecs.optargs[key] in jobspecs.filekeys:
            messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='optargs')
        script.main.append('-{key} {val}'.format(key=key, val=jobspecs.filekeys[jobspecs.optargs[key]]))
    
    for item in jobspecs.posargs:
        for key in item.split('|'):
            if not key in jobspecs.filekeys:
                messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='posargs')
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

    parameterdict = {}
    parameterdict.update(jobspecs.defaults.parameters)
    parameterdict.update(options.parameters)

#    #TODO: Move this code to the submit function
#    #TODO: Use filter groups to set parameters
#    #TODO: Use template strings to interpolate
#    for key, value in options.parameterdict.items():
#        if value.startswith('%'):
#            try:
#                index = int(value[1:]) - 1
#            except ValueError:
#                messages.error(value, 'debe tener un índice numérico', option=o(key))
#            if index not in range(len(filtergroups)):
#                messages.error(value, 'El índice está fuera de rango', option=o(key))
#            parameterdict.update({key: filtergroups[index]})

    for path in jobspecs.defaults.parameterpaths:
        partlist = AbsPath(path, cwd=options.common.root).setkeys(names).parts()
        rootpath = AbsPath(next(partlist))
        for part in partlist:
            try:
                rootpath = rootpath.joinpath(part.format(**parameterdict))
            except KeyError:
                choices = rootpath.listdir()
                choice = dialogs.chooseone('Seleccione una opción', choices=choices)
                rootpath = rootpath.joinpath(choice)
        if rootpath.exists():
            parameterpaths.append(rootpath)
        else:
            messages.error('La ruta', path, 'no existe', spec='defaults.parameterpaths')


def submit(rootdir, basename):

    packagext = '.' + jobspecs.packagekey
    names.job = basename[:-len(packagext)] if basename.endswith(packagext) else basename

    if 'prefix' in options.common:
        names.job = options.common.prefix.format(*options.common.interpolationlist, **options.interpolationdict) + '.' + names.job

    if 'suffix' in options.common:
        names.job = names.job + '.' + options.common.suffix.format(*options.common.interpolationlist, **options.interpolationdict)

    if 'outdir' in options.common:
        outdir = AbsPath(options.common.outdir, cwd=rootdir)
    else:
        if 'jobdir' in jobspecs.defaults and jobspecs.defaults.jobdir:
            outdir = AbsPath(names.job, cwd=rootdir)
        else:
            outdir = AbsPath(rootdir)

    if basename.endswith('.' + jobspecs.packagekey):
        names.job = names.job + packagext

#TODO: Prepend program version to extension of output files if option is enabled
    progfix = jobspecs.packagekey + '.'.join(options.common.version.split())

    hiddendir = AbsPath(buildpath(outdir, '.' + progfix))

    inputfiles = []
    inputdirs = []

    for key in options.optionalfiles:
        inputfiles.append((buildpath(outdir, (names.job, jobspecs.fileoptions[key])), buildpath(script.scrdir, jobspecs.filekeys[jobspecs.fileoptions[key]])))

    for key in jobspecs.infiles:
        if AbsPath(buildpath(rootdir, (basename, key))).isfile():
            inputfiles.append((buildpath(outdir, (names.job, key)), buildpath(script.scrdir, jobspecs.filekeys[key])))
    
    for path in parameterpaths:
        if path.isfile():
            inputfiles.append((path, buildpath(script.scrdir, path.name)))
        elif path.isdir():
            inputdirs.append((buildpath(path), script.scrdir))

    outputfiles = []

    for key in jobspecs.outfiles:
        outputfiles.append((buildpath(script.scrdir, jobspecs.filekeys[key]), buildpath(outdir, (names.job, key))))
    
    if outdir.isdir():
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
        if not set(outdir.listdir()).isdisjoint(buildpath((names.job, k)) for k in jobspecs.outfiles):
            if options.common.no or (not options.common.yes and not dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outdir,'serán sobreescritos, ¿desea continuar de todas formas?')):
                messages.failure('Cancelado por el usuario')
                return
        for key in jobspecs.outfiles:
            remove(buildpath(outdir, (names.job, key)))
        if rootdir != outdir:
            for key in jobspecs.infiles:
                remove(buildpath(outdir, (names.job, key)))
    elif outdir.exists():
        messages.failure('No se puede crear la carpeta', outdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outdir)
        makedirs(hiddendir)

    for key in options.optionalfiles:
        options.optionalfiles[key].linkto(buildpath(outdir, (names.job, jobspecs.fileoptions[key])))

    for key in jobspecs.infiles:
        inputpath = AbsPath(buildpath(rootdir, (basename, key)))
        if inputpath.isfile():
            if options.common.interpolate and 'interpolable' in jobspecs and key in jobspecs.interpolable:
                with open(inputpath, 'r') as fr:
                    template = fr.read()
                try:
                    substituted = Template(template).substitute(options.interpolationdict)
                except ValueError:
                    messages.failure('Hay variables de interpolación inválidas en el archivo de entrada', buildpath((basename, key)))
                    return
                except KeyError as e:
                    messages.failure('Hay variables de interpolación sin definir en el archivo de entrada', buildpath((basename, key)), option=o(e.args[0]))
                    return
                with open(buildpath(outdir, (names.job, key)), 'w') as fw:
                    fw.write(substituted)
            elif rootdir != outdir:
                inputpath.copyto(buildpath(outdir, (names.job, key)))
            if options.common.delete:
                remove(buildpath(rootdir, (basename, key)))

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
            messages.failure('El gestor de trabajos reportó un error al enviar el trabajo', q(names.job), p(error))
            return
        else:
            messages.success('El trabajo', q(names.job), 'se correrá en', str(options.common.nproc), 'núcleo(s) en', names.cluster, 'con número de trabajo', jobid)
            with open(buildpath(hiddendir, 'jobid'), 'w') as f:
                f.write(jobid)
    
parameterpaths = []
script = Bunch()

