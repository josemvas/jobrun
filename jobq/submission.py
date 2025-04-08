import os
import sys
import time
from clinterface import messages, prompts, _
from subprocess import CalledProcessError, call, check_output
from .queue import submitjob, getjobstatus
from .shared import names, nodes, paths, config, options, environ, settings, script, parameterdict, interpolationdict, parameterpaths
from .utils import GlobDict, LogDict, ConfigTemplate, FilterGroupTemplate, InterpolationTemplate, ArgGroups, booleans, option, template_parse
from .readmol import readmol, molblock
from .fileutils import AbsPath, NotAbsolutePath

selector = prompts.Selector()
completer = prompts.Completer()
truthy_options = ['si', 'yes']
falsy_options = ['no']

def configure_submission():

    script.meta = []
    script.vars = []
    script.config = []
    script.body = []

    try:
        paths.jobq.mkdir()
    except FileExistsError:
        messages.error(_('No se puede crear el directorio ~/.jobq porque existe un archivo con el mismo nombre'))

    if (paths.jobq/'config').isfile():
        config.update(json.load(paths.jobq/'config'))

    try:
        config.packagename
    except AttributeError:
        messages.error(_('No se definió el nombre del programa'))

    try:
        names.cluster = config.clustername
    except AttributeError:
        messages.error(_('No se definió el nombre del clúster'))

    try:
        nodes.head = config.headnode
    except AttributeError:
        nodes.head = names.host

    try:
        environ.TELEGRAM_BOT_URL = os.environ['TELEGRAM_BOT_URL']
        environ.TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    except KeyError:
        pass

#    for key, path in options.restartfiles.items():
#        if not path.isfile():
#            messages.error(_('El archivo de reinicio $path no existe'), path=path)

    if options.remote.remote_host:
        (paths.home/'.ssh').mkdir()
        paths.socket = paths.home/'.ssh'/options.remote.remote_host%'sock'
        try:
            paths.remotedir = check_output(['ssh', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=60', '-S', paths.socket, \
                options.remote.remote_host, 'printenv CLUSTERQ_REMOTE_ROOT || true']).strip().decode(sys.stdout.encoding)
        except CalledProcessError as e:
            messages.error(_('No se pudo conectar con el servidor $host: $error'), host=options.remote.remote_host, error=e.output.decode(sys.stdout.encoding).strip())
        if paths.remotedir:
            paths.remotedir = AbsPath(paths.remotedir)
        else:
            messages.error(_('El servidor $host no está configurado para aceptar trabajos', host=options.remote.remote_host))

    interpolationdict.update(options.interpolopts)

    for i, var in enumerate(options.interpolation.posvars, start=1):
        interpolationdict[str(i)] = var

    if options.interpolation.mol or options.interpolation.trjmol or interpolationdict:
        options.interpolate = True
    else:
        options.interpolate = False

    for key, value in options.parameteropts.items():
        if '/' in options.parameteropts[key]:
            messages.error(_('El nombre del conjunto de parámetros no es válido: parameteropts[$key]=$value'), key=key, value=value)

    parameterdict.update(options.parameteropts)

    if options.interpolate:
        if options.interpolation.mol:
            for i, path in enumerate(options.interpolation.mol, start=1):
                path = AbsPath(path, parent=options.common.cwd)
                molprefix = path.stem
                coords = readmol(path)[-1]
                interpolationdict[f'mol{i}'] = molblock(coords, config.progspecfile)
        elif options.interpolation.trjmol:
            path = AbsPath(options.interpolation.trjmol, parent=options.common.cwd)
            molprefix = path.stem
            for i, coords in enumerate(readmol(path), start=1):
                interpolationdict[f'mol{i}'] = molblock(coords, config.progspecfile)
        if options.interpolation.prefix:
            try:
                settings.prefix = InterpolationTemplate(options.interpolation.prefix).substitute(interpolationdict)
            except ValueError as e:
                messages.error(_('El prefijo contiene variables de interpolación inválidas'), prefix=options.interpolation.prefix, key=e.args[0])
            except KeyError as e:
                messages.error(_('El prefijo contiene variables de interpolación indefinidas'), prefix=options.interpolation.prefix, key=e.args[0])
        elif options.interpolation.suffix:
            try:
                settings.suffix = InterpolationTemplate(options.interpolation.suffix).substitute(interpolationdict)
            except ValueError as e:
                messages.error(_('El sufijo contiene variables de interpolación inválidas'), suffix=options.interpolation.suffix, key=e.args[0])
            except KeyError as e:
                messages.error(_('El sufijo contiene variables de interpolación indefinidas'), suffix=options.interpolation.suffix, key=e.args[0])
        else:
            if options.interpolation.mol:
                if len(options.interpolation.mol) == 1:
                    settings.prefix = molprefix
                else:
                    messages.error(_('Se debe especificar un prefijo o sufijo cuando se especifican múltiples archivos de coordenadas'))
            elif options.interpolation.trjmol:
                settings.prefix = molprefix
            else:
                messages.error(_('Se debe especificar un prefijo o sufijo para interpolar sin archivo coordenadas'))

    if not 'scratch' in config.defaults:
        messages.error(_('No se especificó el directorio de escritura por defecto'))

    if 'scratch' in options.common:
        settings.execdir = AbsPath(options.common.scratch/'$jobid')
    else:
        settings.execdir = AbsPath(ConfigTemplate(config.defaults.scratch).substitute(names))/'$jobid'

    if 'mpilaunch' in config:
        try: config.mpilaunch = booleans[config.mpilaunch]
        except KeyError:
            messages.error(_('Se requier un valor boolenano'), mpilaunch=config.mpilaunch)
    
    if not config.filekeys:
        messages.error(_('Se requiere una lista de claves de archivo no vacía'), filekeys=config.filekeys)
    
    if config.inputfiles:
        for key in config.inputfiles:
            if not key in config.filekeys:
                messages.error(_('$key está en config.inputfiles pero no en config.filekeys'), key=key)
    else:
        messages.error(_('Se requiere una lista de archivos de entrada no vacía'), inputfiles=config.inputfiles)
    
    if config.outputfiles:
        for key in config.outputfiles:
            if not key in config.filekeys:
                messages.error(_('$key está en config.outputfiles pero no en config.filekeys'), key=key)
    else:
        messages.error(_('Se requiere una lista de archivos de salida no vacía'), outputfiles=config.outputfiles)

    if options.remote.remote_host:
        return

    ############ Local execution ###########

    if 'jobtype' in config:
        script.meta.append(ConfigTemplate(config.jobtype).substitute(jobtype=config.packagename))

    if 'queue' in options.common:
        script.meta.append(ConfigTemplate(config.queue).substitute(queue=options.common.queue))
    elif 'queue' in config.defaults:
        script.meta.append(ConfigTemplate(config.queue).substitute(queue=config.defaults.queue))

    #TODO MPI support for Slurm
    if config.parallel:
        if config.parallel.lower() == 'none':
            if 'hosts' in options.common:
                for i, item in enumerate(config.serialat):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            else:
                for i, item in enumerate(config.serial):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
        elif config.parallel.lower() == 'omp':
            if 'hosts' in options.common:
                for i, item in enumerate(config.singlehostat):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            else:
                for i, item in enumerate(config.singlehost):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            script.body.append(f'OMP_NUM_THREADS={options.common.nproc}')
        elif config.parallel.lower() == 'mpi':
            if 'hosts' in options.common:
                for i, item in enumerate(config.multihostat):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            else:
                for i, item in enumerate(config.multihost):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            if 'mpilib' in config:
                if config.mpilib in config.mpirun:
                    script.body.append(ConfigTemplate(config.mpirun[config.mpilib]).substitute(options.common))
                elif config.mpilib == 'builtin':
                    pass
                else:
                    messages.error(_('Libreríá MPI no soportada'), mpilib=config.mpilib)
            else:
                messages.error(_('No se especificó la biblioteca MPI del programa (mpilib)'))
        else:
            messages.error(_('Tipo de paralelización no soportado'), parallel=config.parallel)
    else:
        messages.error(_('No se especificó el tipo de paralelización del programa (parallel)'))

    if not config.versions:
        messages.error(_('Se requiere una lista de versiones no vacía'), versions=config.versions)

    for version in config.versions:
        if not 'executable' in config.versions[version]:
            messages.error(_('No se especificó el ejecutable del programa'), version=version)
    
    for version in config.versions:
        config.versions[version].update({'load':[], 'source':[], 'export':{}})

    prompt = _('Seleccione una versión:')

    if 'version' in options.common:
        if options.common.version not in config.versions:
            messages.error(_('La versión del programa solicitada no es válida'), version=options.common.version)
        settings.version = options.common.version
    elif 'version' in config.defaults:
        if not config.defaults.version in config.versions:
            messages.error(_('La versión del programa establecida por defecto no es válida'), version=config.defaults.version)
        if options.common.prompt:
            settings.version = selector.single_choice(prompt, config.versions.keys(), config.defaults.version)
        else:
            settings.version = config.defaults.version
    else:
        settings.version = selector.single_choice(prompt, config.versions.keys())

    ############ Interactive parameter selection ###########

    for i, path in enumerate(config.parameterpaths):
        logdict = LogDict()
        FilterGroupTemplate(path).substitute(logdict)
        if logdict.logged_keys:
            logdict = LogDict()
            InterpolationTemplate(path).safe_substitute(logdict)
            if logdict.logged_keys:
                messages.error(_('La ruta $path contiene variables de interpolación indefinidas'), path=path, keys=logdict.logged_keys)
        else:
            path = ConfigTemplate(path).safe_substitute(names)
            path = InterpolationTemplate(path).safe_substitute(parameterdict)
            trunk = AbsPath()
            for part in AbsPath(path).parts:
                trunk.assertdir()
                try:
                    InterpolationTemplate(part).substitute()
                except KeyError:
                    prompt = _('Seleccione un conjunto de parámetros:')
                    option_list = sorted(trunk.glob(InterpolationTemplate(part).substitute(GlobDict())))
                    choice = selector.single_choice(prompt, option_list)
                    parameterdict.update(template_parse(part, choice))
                    trunk = trunk/choice
                else:
                    trunk = trunk/part

    ############ End of interactive parameter selection ###########

    try:
        script.body.append(AbsPath(ConfigTemplate(config.versions[settings.version].executable).substitute(names)))
    except NotAbsolutePath:
        script.body.append(config.versions[settings.version].executable)

    for i, path in enumerate(config.logfiles):
        script.meta.append(ConfigTemplate(path).safe_substitute(dict(logdir=AbsPath(ConfigTemplate(config.logdir).substitute(names)))))

    for key, value in config.export.items():
        if value:
            script.config.append(f'export {key}={value}')
        else:
            messages.error(_('La variable config.export[$key] no está definida'), key=key)

    for key, value in config.versions[settings.version].export.items():
        if value:
            script.config.append(f'export {key}={value}')
        else:
            messages.error(_('La variable config.export[$key] no está definida'), key=key)

    for i, path in enumerate(config.source + config.versions[settings.version].source):
        if path:
            script.config.append(f'source {AbsPath(ConfigTemplate(path).substitute(names))}')
        else:
            messages.error(_('La ruta del script de entorno no está definida'))

    if config.load or config.versions[settings.version].load:
        script.config.append('module purge')

    for i, module in enumerate(config.load + config.versions[settings.version].load):
        if module:
            script.config.append(f'module load {module}')
        else:
            messages.error(_('El nombre del módulo de entorno no está definido'))

    for key, value in config.envars.items():
        script.vars.append(f'{key}="{value}"')

    script.vars.append("totram=$(free | awk 'NR==2{print $2}')")
    script.vars.append("totproc=$(getconf _NPROCESSORS_ONLN)")
    script.vars.append("maxram=$(($totram*$nproc/$totproc))")

    for key, value in config.filevars.items():
        script.vars.append(f'{key}="{config.filekeys[value]}"')

    for key, value in names.items():
        script.vars.append(f'{key}name="{value}"')

    for key, value in nodes.items():
        script.vars.append(f'{key}node="{value}"')

    for key in config.optargs:
        if not config.optargs[key] in config.filekeys:
            messages.error(_('$key está en config.optargs pero no en config.filekeys'), key=key)
        script.body.append(f'-{key} {config.filekeys[config.optargs[key]]}')
    
    for item in config.posargs:
        for key in item.split('|'):
            if not key in config.filekeys:
                messages.error(_('$key está en config.posargs pero no en config.filekeys'), key=key)
        script.body.append(f"@({'|'.join(config.filekeys[i] for i in item.split('|'))})")
    
    if 'stdinfile' in config:
        try:
            script.body.append(f'0< {config.filekeys[config.stdinfile]}')
        except KeyError:
            messages.error(_('$stdinfile no está en config.filekeys'), stdinfile=config.stdinfile)

    if 'stdoutfile' in config:
        try:
            script.body.append(f'1> {config.filekeys[config.stdoutfile]}')
        except KeyError:
            messages.error(_('$stdoutfile no está en config.filekeys'), stdoutfile=config.stdoutfile)

    if 'stderrfile' in config:
        try:
            script.body.append(f'2> {config.filekeys[config.stderrfile]}')
        except KeyError:
            messages.error(_('$stderrfile no está en config.filekeys'), stderrfile=config.stderrfile)
    
    script.chdir = 'cd "{}"'.format
    if config.filesync == 'local':
        script.makedir = 'mkdir -p -m 700 "{}"'.format
        script.removedir = 'rm -rf "{}"'.format
        if options.common.move:
            script.importfile = 'mv "{}" "{}"'.format
        else:
            script.importfile = 'cp "{}" "{}"'.format
        script.importdir = 'cp -r "{}/." "{}"'.format
        script.exportfile = 'cp "{}" "{}"'.format
    elif config.filesync == 'remote':
        script.makedir = 'for host in ${{hosts[*]}}; do rsh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.removedir = 'for host in ${{hosts[*]}}; do rsh $host rm -rf "\'{}\'"; done'.format
        if options.common.move:
            script.importfile = 'for host in ${{hosts[*]}}; do rcp $headnode:"\'{0}\'" $host:"\'{1}\'" && rsh $headnode rm "\'{0}\'"; done'.format
        else:
            script.importfile = 'for host in ${{hosts[*]}}; do rcp $headnode:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.importdir = 'for host in ${{hosts[*]}}; do rsh $host cp -r "\'{0}/.\'" "\'{1}\'"; done'.format
        script.exportfile = 'rcp "{}" $headnode:"\'{}\'"'.format
    elif config.filesync == 'secure':
        script.makedir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.removedir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'{}\'"; done'.format
        if options.common.move:
            script.importfile = 'for host in ${{hosts[*]}}; do scp $headnode:"\'{0}\'" $host:"\'{1}\'" && ssh $headnode rm "\'{0}\'"; done'.format
        else:
            script.importfile = 'for host in ${{hosts[*]}}; do scp $headnode:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.importdir = 'for host in ${{hosts[*]}}; do ssh $host cp -r "\'{0}/.\'" "\'{1}\'"; done'.format
        script.exportfile = 'scp "{}" $headnode:"\'{}\'"'.format
    else:
        messages.error(_('El método de copia no es válido'), filesync=config.filesync)
def submit_single_job(workdir, inputname, filtergroups):

    if 'prefix' in settings:
        jobname = f'{settings.prefix}_{inputname}'
    elif 'suffix' in settings:
        jobname = f'{inputname}_{settings.suffix}'
    else:
        jobname = inputname

    script.vars.append(f'jobname="{jobname}"')
    script.meta.append(ConfigTemplate(config.jobname).substitute(jobname=jobname))

    if 'out' in options.common:
        outdir = AbsPath(options.common.out, parent=workdir)
    else:
        outdir = AbsPath(jobname, parent=workdir)

    literalfiles = {}
    interpolatedfiles = {}

    if options.common.raw:
        stagedir = workdir
    else:
        if outdir == workdir:
            messages.failure(_('El directorio de salida debe ser distinto al directorio de trabajo'))
            return
        stagedir = outdir
        for key in config.inputfiles:
            srcpath = workdir/inputname%key
            destpath = stagedir/jobname%key
            if srcpath.isfile():
                if 'interpolable' in config and key in config.interpolable:
                    with open(srcpath, 'r') as f:
                        contents = f.read()
                        if options.interpolate:
                            try:
                                interpolatedfiles[destpath] = InterpolationTemplate(contents).substitute(interpolationdict)
                            except ValueError:
                                messages.failure(_('El archivo $file contiene variables de interpolación inválidas'), file=srcpath, key=e.args[0])
                                return
                            except KeyError as e:
                                messages.failure(_('El archivo $file contiene variables de interpolación indefinidas'), file=srcpath, key=e.args[0])
                                return
                        else:
                            try:
                                interpolatedfiles[destpath] = InterpolationTemplate(contents).substitute({})
                            except ValueError:
                                pass
                            except KeyError as e:
                                prompt = _('Parece que hay variables de interpolación en el archivo $file ¿desea continuar sin interpolar?', file=srcpath)
                                if completer.binary_choice(prompt, truthy_options, falsy_options):
                                    literalfiles[destpath] = srcpath
                                else:
                                    return
                else:
                    literalfiles[destpath] = srcpath

    jobdir = stagedir/'.job'

    if outdir.isdir():
        if jobdir.isdir():
            try:
                with open(jobdir/'id', 'r') as f:
                    jobid = f.read()
                success, jobstatus = getjobstatus(jobid)
                if not success:
                    messages.failure(jobstatus, name=jobname, path=outdir)
                    return
            except FileNotFoundError:
                pass
        if not set(outdir.listdir()).isdisjoint(f'{jobname}.{key}' for key in config.outputfiles):
            prompt = _('Si corre este cálculo los archivos de salida existentes en el directorio $outdir serán sobreescritos, ¿desea continuar de todas formas?', outdir=outdir)
            if options.common.no or (not options.common.yes and not completer.binary_choice(prompt, truthy_options, falsy_options)):
                messages.failure(_('Cancelado por el usuario'))
                return
        if workdir != outdir:
            for ext in config.inputfiles:
                (outdir/jobname%ext).remove()
        for ext in config.outputfiles:
            (outdir/jobname%ext).remove()
    else:
        try:
            outdir.makedirs()
        except FileExistsError:
            messages.failure(_('No se puede crear la carpeta $outdir porque ya existe un archivo con el mismo nombre'), outdir=outdir)
            return

    for destpath, litfile in literalfiles.items():
        litfile.copyas(destpath)

    for destpath, contents in interpolatedfiles.items():
        with open(destpath, 'w') as f:
            f.write(contents)

#    for key, targetfile in options.restartfiles.items():
#        targetfile.symlink(stagedir/jobname%config.fileopts[key])

    ############ Remote execution ###########

    if options.remote.remote_host:
        remote_args = ArgGroups()
        reloutdir = os.path.relpath(outdir, paths.home)
        remote_tmpdir = paths.remotedir/names.user%names.host/'tmp'
        remote_outdir = paths.remotedir/names.user%names.host/'out'
        remote_args.gather(options.common)
        remote_args.flags.add('raw')
        remote_args.flags.add('job')
        remote_args.flags.add('move')
        remote_args.options['cwd'] = remote_tmpdir/reloutdir
        remote_args.options['out'] = remote_outdir/reloutdir
        for key, value in parameterdict.items():
            remote_args.options[key] = val
        filelist = []
        for key in config.filekeys:
            if (outdir/jobname%key).isfile():
                filelist.append(paths.home/'.'/reloutdir/jobname%key)
        arglist = ['ssh', '-qt', '-S', paths.socket, options.remote.remote_host]
        arglist.extend(f'{env}={val}' for env, val in environ.items())
        arglist.append(names.command)
        arglist.extend(option(key) for key in remote_args.flags)
        arglist.extend(option(key, value) for key, value in remote_args.options.items())
        arglist.extend(option(key, value) for key, listval in remote_args.multoptions.items() for value in listval)
        arglist.append(jobname)
        if options.debug.dry_run:
            print('<FILE LIST>', ' '.join(filelist), '</FILE LIST>')
            print('<COMMAND LINE>', ' '.join(arglist), '</COMMAND LINE>')
        else:
            try:
                check_output(['ssh', '-S', paths.socket, options.remote.remote_host, f"mkdir -p '{remote_tmpdir}' '{remote_outdir}'"])
                check_output([f'rsync', '-e', "ssh -S '{paths.socket}'", '-qRLtz'] + filelist + [f'{options.remote.remote_host}:{remote_tmpdir}'])
                check_output([f'rsync', '-e', "ssh -S '{paths.socket}'", '-qRLtz', '-f', '-! */'] + filelist + [f'{options.remote.remote_host}:{remote_outdir}'])
            except CalledProcessError as e:
                messages.error(_('Error al copiar los archivos al servidor $host'), host=options.remote.remote_host, error=e.output.decode(sys.stdout.encoding).strip())
            call(arglist)
        return

    ############ Local execution ###########

    for path in config.parameterpaths:
        try:
            path = ConfigTemplate(path).safe_substitute(names)
            path = FilterGroupTemplate(path).substitute(filtergroups)
            path = InterpolationTemplate(path).substitute(parameterdict)
        except ValueError as e:
            messages.error(_('La ruta $path contiene variables de interpolación inválidas'), path=path, key=e.args[0])
        except KeyError as e:
            messages.error(_('La ruta $path contiene variables de interpolación indefinidas'), path=path, key=e.args[0])
        trunk = AbsPath()
        for part in AbsPath(path).parts:
            trunk.assertdir()
            trunk = trunk/part
        parameterpaths.append(trunk)

    imports = []
    exports = []

    for key in config.inputfiles:
        if (workdir/inputname%key).isfile():
            imports.append(script.importfile(stagedir/jobname%key, settings.execdir/config.filekeys[key]))

#    for key in options.restartfiles:
#        imports.append(script.importfile(stagedir/jobname%config.fileopts[key], settings.execdir/config.filekeys[config.fileopts[key]]))

    for path in parameterpaths:
        if path.isfile():
            imports.append(script.importfile(path, settings.execdir/path.name))
        elif path.isdir():
            imports.append(script.importdir(path, settings.execdir))
        else:
            messages.error(_('La ruta de parámetros $path no existe'), path=path)

    for key in config.outputfiles:
        exports.append(script.exportfile(settings.execdir/config.filekeys[key], outdir/jobname%key))

    try:
        jobdir.mkdir()
    except FileExistsError:
        messages.failure(_('No se puede crear la carpeta $jobdir porque ya existe un archivo con ese nombre'), jobdir=jobdir)
        return

    jobscript = jobdir/'script'

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash -x' + '\n')
        f.write(''.join(i + '\n' for i in script.meta))
        f.write('shopt -s extglob nullglob' + '\n')
        f.write(''.join(i + '\n' for i in script.vars))
        f.write(''.join(i + '\n' for i in script.config))
        f.write(script.makedir(settings.execdir) + '\n')
        f.write(''.join(i + '\n' for i in imports))
        f.write(script.chdir(settings.execdir) + '\n')
        f.write(''.join(i + '\n' for i in config.prescript))
        f.write(' '.join(script.body) + '\n')
        f.write(''.join(i + '\n' for i in config.postscript))
        f.write(''.join(i + '\n' for i in exports))
        f.write(script.removedir(settings.execdir) + '\n')
        f.write(''.join(i + '\n' for i in config.offscript))

    if options.debug.dry_run:

        messages.success(_('Se procesó el trabajo "$jobname" y se generaron los archivos para el envío en el directorio $jobdir'), jobname=jobname, jobdir=jobdir)

    else:

        try:
            delay = float(config.delay) + os.stat(paths.jobq/'lockfile').st_mtime - time.time()
        except ValueError:
            messages.error(_('El tiempo de espera no es numérico'), delay=config.delay)
        except (FileNotFoundError) as e:
            pass
        else:
            if delay > 0:
                time.sleep(delay)
    
        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            messages.failure(_('El gestor de trabajos reportó un problema al enviar el trabajo $jobname'), jobname=jobname, error=error)
            return
        else:
            messages.success(_('El trabajo "$jobname" se correrá en $nproc núcleo(s) en $clustername con el número $jobid'), jobname=jobname, nproc=options.common.nproc, clustername=names.cluster, jobid=jobid)
            with open(jobdir/'id', 'w') as f:
                f.write(jobid)
            with open(paths.jobq/'lockfile', 'a'):
                os.utime(paths.jobq/'lockfile', None)
