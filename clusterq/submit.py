import os
import sys
import time
from subprocess import CalledProcessError, call, check_output
from clinterface import messages, prompts, _
#from tkdialogs import messages, prompts
from .queue import submitjob, getjobstate
from .utils import AttrDict, GlobDict, LogDict
from .utils import ConfigTemplate, FilterGroupTemplate, InterpolationTemplate
from .utils import opt, template_parse, natsorted as sorted
from .shared import parameterdict, interpolationdict
from .shared import names, nodes, paths, config, options, remoteargs, environ
from .fileutils import AbsPath, NotAbsolutePath, pathsplit, pathjoin, file_except_info
from .parsing import BoolParser
from .readmol import readmol

parameterpaths = []
settings = AttrDict()
script = AttrDict()

selector = prompts.Selector()
completer = prompts.Completer()
completer.set_truthy_options(['si', 'yes'])
completer.set_falsy_options(['no'])

booleans = {'True':True, 'False':False}

def geometry_block(coords):
    if names.display in ('Gaussian', 'deMon2k'):
        return '\n'.join('{:<2s}  {:10.4f}  {:10.4f}  {:10.4f}'.format(*line) for line in coords)
    elif names.display in ('DFTB+'):
       atoms = []
       blocklines = []
       for line in coords:
           if not line[0] in atoms:
               atoms.append(line[0])
       blocklines.append('{:5} C'.format(len(coords)))
       blocklines.append(' '.join(atoms))
       for i, line in enumerate(coords, start=1):
           blocklines.append('{:5}  {:3}  {:10.4f}  {:10.4f}  {:10.4f}'.format(i, atoms.index(line[0]) + 1, line[1], line[2], line[3]))
       return '\n'.join(blocklines)
    else:
       messages.error(_('Formato desconocido'), f'molformat={molformat}')

def initialize():

    script.head = {}
    script.body = []

    for key, path in options.targetfiles.items():
        if not path.isfile():
            messages.error(_('El archivo de entrada no existe'), f'options.targetfiles.items[{key}]={path}')

    if options.remote.host:
        (paths.home/'.ssh').mkdir()
        paths.socket = paths.home/'.ssh'/options.remote.host%'sock'
        try:
            options.remote.root = check_output(['ssh', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=60', '-S', paths.socket, \
                options.remote.host, 'printenv QREMOTEROOT']).strip().decode(sys.stdout.encoding)
        except CalledProcessError as e:
            messages.error(_('Error al conectar con el servidor $host', host=options.remote.host), e.output.decode(sys.stdout.encoding).strip())
        if not options.remote.root:
            messages.error(_('El servidor $host no está configurado para aceptar trabajos', host=options.remote.host))

    if options.common.prompt:
        settings.defaults = False
    else:
        settings.defaults = True

    interpolationdict.update(options.interpolationoptions)

    for i, var in enumerate(options.interpolation.posvars, start=1):
        interpolationdict[str(i)] = var

    if options.interpolation.mol or options.interpolation.trjmol or interpolationdict:
        options.interpolate = True
    else:
        options.interpolate = False

    for key, value in options.parameteroptions.items():
        if '/' in options.parameteroptions[key]:
            messages.error(_('El nombre del conjunto de parámetros no es válido'), f'options.parameteroptions[{key}]={value}')

    parameterdict.update(options.parameteroptions)

    if options.interpolate:
        if options.interpolation.mol:
            for i, path in enumerate(options.interpolation.mol, start=1):
                path = AbsPath(path, parent=options.common.cwd)
                molprefix = path.stem
                coords = readmol(path)[-1]
                interpolationdict['mol' + str(i)] = geometry_block(coords)
        elif options.interpolation.trjmol:
            path = AbsPath(options.interpolation.trjmol, parent=options.common.cwd)
            molprefix = path.stem
            for i, coords in enumerate(readmol(path), start=1):
                interpolationdict['mol' + str(i)] = geometry_block(coords)
        if options.interpolation.prefix:
            try:
                settings.prefix = InterpolationTemplate(options.interpolation.prefix).substitute(interpolationdict)
            except ValueError as e:
                messages.error(_('El prefijo contiene variables de interpolación inválidas'), f'options.interpolation.prefix={options.interpolation.prefix}, key={e.args[0]}')
            except KeyError as e:
                messages.error(_('El prefijo contiene variables de interpolación indefinidas'), f'options.interpolation.prefix={options.interpolation.prefix}, key={e.args[0]}')
        else:
            if options.interpolation.mol:
                if len(options.interpolation.mol) == 1:
                    settings.prefix = molprefix
                else:
                    messages.error(_('Se debe especificar un prefijo cuando se especifican múltiples archivos de coordenadas'))
            elif options.interpolation.trjmol:
                settings.prefix = molprefix
            else:
                messages.error(_('Se debe especificar un prefijo para interpolar sin archivo coordenadas'))

    try:
        config.delay = float(config.delay)
    except ValueError:
        messages.error(_('El tiempo de espera debe ser un número'), f'config.delay={config.delay}')
    except AttributeError:
        config.delay = 0
    
    if not 'scratch' in config.defaults:
        messages.error(_('No se especificó el directorio de escritura por defecto'), f'config.defaults.scratch={config.defaults.scratch}')

    if 'scratch' in options.common:
        settings.execdir = options.common.scratch/'$jobid'
    else:
        settings.execdir = AbsPath(ConfigTemplate(config.defaults.scratch).substitute(names))/'$jobid'

    if 'queue' not in options.common:
        if 'queue' in config.defaults:
            options.common.queue = config.defaults.queue
        else:
            messages.error(_('Debe especificar la cola a la que desea enviar el trabajo'))
    
    if 'mpilaunch' in config:
        try: config.mpilaunch = booleans[config.mpilaunch]
        except KeyError:
            messages.error(_('El valor de este ajuste debe ser True o False'), f'config.mpilaunch={config.mpilaunch}')
    
    if not config.filekeys:
        messages.error(_('La lista de archivos del programa no existe o está vacía'), 'config.filekeys')
    
    if config.inputfiles:
        for key in config.inputfiles:
            if not key in config.filekeys:
                messages.error(_('Elemento no encontrado'), f'{key} in config.inputfiles but not in config.filekeys')
    else:
        messages.error(_('La lista de archivos de entrada está vacía'), 'config.inputfiles')
    
    if config.outputfiles:
        for key in config.outputfiles:
            if not key in config.filekeys:
                messages.error(_('Elemento no encontrado'), f'{key} in config.outputfiles but not in config.filekeys')
    else:
        messages.error(_('La lista de archivos de salida está vacía'), 'config.outputfiles')

    if options.remote.host:
        return

    ############ Local execution ###########

    script.head['jobname'] = None

    if 'jobtype' in config:
        script.head['jobtype'] = ConfigTemplate(config.jobtype).substitute(jobtype=config.specname)

    script.head['queue'] = ConfigTemplate(config.queue).substitute(options.common)

    #TODO MPI support for Slurm
    if config.parallel:
        if config.parallel.lower() == 'none':
            if 'hosts' in options.common:
                for i, item in enumerate(config.serialat):
                    script.head['span' + str(i)] = ConfigTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.serial):
                    script.head['span' + str(i)] = ConfigTemplate(item).substitute(options.common)
        elif config.parallel.lower() == 'omp':
            if 'hosts' in options.common:
                for i, item in enumerate(config.singlehostat):
                    script.head['span' + str(i)] = ConfigTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.singlehost):
                    script.head['span' + str(i)] = ConfigTemplate(item).substitute(options.common)
            script.body.append('OMP_NUM_THREADS=' + str(options.common.nproc))
        elif config.parallel.lower() == 'mpi':
            if 'hosts' in options.common:
                for i, item in enumerate(config.multihostat):
                    script.head['span' + str(i)] = ConfigTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.multihost):
                    script.head['span' + str(i)] = ConfigTemplate(item).substitute(options.common)
            if 'mpilib' in config:
                if config.mpilib in config.mpirun:
                    script.body.append(ConfigTemplate(config.mpirun[config.mpilib]).substitute(options.common))
                elif config.mpilib == 'builtin':
                    pass
                else:
                    messages.error(_('Libreríá MPI no soportada'), 'config.mpilib={config.mpilib}')
            else:
                messages.error(_('No se especificó la librería MPI del programa'), 'config.mpilib')
        else:
            messages.error(_('Tipo de paralelización no soportado'), 'config.parallel={config.parallel}')
    else:
        messages.error(_('No se especificó el tipo de paralelización del programa'), 'config.parallel')

    if not config.versions:
        messages.error(_('La lista de versiones no existe o está vacía'), 'config.versions')

    for version in config.versions:
        if not 'executable' in config.versions[version]:
            messages.error(_('No se especificó el ejecutable'), f'config.versions[{version}].executable')
    
    for version in config.versions:
        config.versions[version].merge({'load':[], 'source':[], 'export':{}})

    selector.set_message(_('Seleccione una versión:'))
    selector.set_options(config.versions.keys())

    if 'version' in options.common:
        if options.common.version not in config.versions:
            messages.error(_('La versión no es válida'), f'options.common.version={options.common.version}')
        settings.version = options.common.version
    elif 'version' in config.defaults:
        if not config.defaults.version in config.versions:
            messages.error(_('La versión establecida por defecto no es válida'), f'config.defaults.version={config.defaults.version}')
        if settings.defaults:
            settings.version = config.defaults.version
        else:
            selector.set_single_default(config.defaults.version)
            settings.version = selector.single_choice()
    else:
        settings.version = selector.single_choice()

    ############ Interactive parameter selection ###########

    for i, path in enumerate(config.parameterpaths):
        logdict = LogDict()
        FilterGroupTemplate(path).substitute(logdict)
        if logdict.logged_keys:
            logdict = LogDict()
            InterpolationTemplate(path).safe_substitute(logdict)
            if logdict.logged_keys:
                messages.error(_('La ruta $path contiene variables de interpolación indefinidas'), f'config.parameterpaths[{i}]={path}')
        else:
            path = ConfigTemplate(path).safe_substitute(names)
            path = InterpolationTemplate(path).safe_substitute(parameterdict)
            componentlist = pathsplit(path)
            trunk = AbsPath(componentlist.pop(0))
            for component in componentlist:
                trunk.assertdir()
                try:
                    InterpolationTemplate(component).substitute()
                except KeyError:
                    selector.set_message(_('Seleccione un conjunto de parámetros:'))
                    selector.set_options(sorted(trunk.glob(InterpolationTemplate(component).substitute(GlobDict()))))
                    choice = selector.single_choice()
                    parameterdict.update(template_parse(component, choice))
                    trunk = trunk/choice
                else:
                    trunk = trunk/component

    ############ End of interactive parameter selection ###########

    try:
        script.body.append(AbsPath(ConfigTemplate(config.versions[settings.version].executable).substitute(names)))
    except NotAbsolutePath:
        script.body.append(config.versions[settings.version].executable)

    for i, path in enumerate(config.logfiles):
        script.head['log' + str(i)] = ConfigTemplate(path).safe_substitute(dict(logdir=AbsPath(ConfigTemplate(config.logdir).substitute(names))))

    script.head['shopt'] = "shopt -s nullglob extglob"

    for key, value in config.export.items():
        if value:
            script.head[key + 'var'] = 'export {}={}'.format(key, value)
        else:
            messages.error(_('La variable de entorno está vacía'), f'config.export[{key}]')

    for key, value in config.versions[settings.version].export.items():
        if value:
            script.head[key + 'var'] = 'export {}={}'.format(key, value)
        else:
            messages.error(_('La variable de entorno está vacía'), f'config.export[{key}]')

    for i, path in enumerate(config.source + config.versions[settings.version].source):
        if path:
            script.head['source' + str(i)] = 'source {}'.format(AbsPath(ConfigTemplate(path).substitute(names)))
        else:
            messages.error(_('La ruta del script de configuración está vacía'), 'config.source')

    if config.load or config.versions[settings.version].load:
        script.head['purge'] = 'module purge'

    for i, module in enumerate(config.load + config.versions[settings.version].load):
        if module:
            script.head['load' + str(i)] = 'module load {}'.format(module)
        else:
            messages.error(_('El nombre del módulo es nulo'), 'config.load')

    for key, value in config.envars.items():
        script.head[key + 'var'] = '{}="{}"'.format(key, value)

    for key, value in config.filevars.items():
        script.head[key + 'file'] = '{}="{}"'.format(key, config.filekeys[value])

    for key, value in names.items():
        script.head[key + 'name'] = '{}name="{}"'.format(key, value)

    for key, value in nodes.items():
        script.head[key + 'node'] = '{}node="{}"'.format(key, value)

    script.head['freeram'] = "freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')"
    script.head['totalram'] = "totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')"
    script.head['jobram'] = "jobram=$(($nproc*$totalram/$(nproc --all)))"

    for key in config.optargs:
        if not config.optargs[key] in config.filekeys:
            messages.error(_('Elemento no encontrado'), f'{key} in config.optargs but not in config.filekeys')
        script.body.append('-{key} {val}'.format(key=key, val=config.filekeys[config.optargs[key]]))
    
    for item in config.posargs:
        for key in item.split('|'):
            if not key in config.filekeys:
                messages.error(_('Elemento no encontrado'), f'{key} in config.posargs but not in config.filekeys')
        script.body.append('@(' + '|'.join(config.filekeys[i] for i in item.split('|')) + ')')
    
    if 'stdinfile' in config:
        try:
            script.body.append('0<' + ' ' + config.filekeys[config.stdinfile])
        except KeyError:
            messages.error(_('Elemento no encontrado'), f'config.stdinfile={config.stdinfile} not in config.filekeys')

    if 'stdoutfile' in config:
        try:
            script.body.append('1>' + ' ' + config.filekeys[config.stdoutfile])
        except KeyError:
            messages.error(_('Elemento no encontrado'), 'config.stdoutfile={config.stdoutfile} not in config.filekeys')

    if 'stderrfile' in config:
        try:
            script.body.append('2>' + ' ' + config.filekeys[config.stderrfile])
        except KeyError:
            messages.error(_('Elemento no encontrado'), 'config.stderrfile={config.stderrfile} not in config.filekeys')
    
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
        messages.error(_('El método de copia no es válido'), 'config.filesync={config.filesync}')


def submit(workdir, inputname, filtergroups):

    filestatus = {}
    for key in config.filekeys:
        path = AbsPath(pathjoin(workdir, (inputname, key)))
        filestatus[key] = path.isfile() or key in options.targetfiles

    for conflict, message in config.conflicts.items():
        if BoolParser(conflict).evaluate(filestatus):
            messages.error(message, f'inputname={inputname}')

    if 'prefix' in settings:
        jobname = settings.prefix + '.' + inputname
    else:
        jobname = inputname

    script.head['jobname'] = ConfigTemplate(config.jobname).substitute(jobname=jobname)
    script.head['jobnamevar'] = 'jobname="{}"'.format(jobname)

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
            srcpath = AbsPath(pathjoin(workdir, (inputname, key)))
            destpath = pathjoin(stagedir, (jobname, key))
            if srcpath.isfile():
                if 'interpolable' in config and key in config.interpolable:
                    with open(srcpath, 'r') as f:
                        contents = f.read()
                        if options.interpolate:
                            try:
                                interpolatedfiles[destpath] = InterpolationTemplate(contents).substitute(interpolationdict)
                            except ValueError:
                                messages.failure(_('El archivo $file contiene variables de interpolación inválidas', file=srcpath.name), f'key={e.args[0]}')
                                return
                            except KeyError as e:
                                messages.failure(_('El archivo $file contiene variables de interpolación indefinidas', file=srcpath.name), f'key={e.args[0]}')
                                return
                        else:
                            try:
                                interpolatedfiles[destpath] = InterpolationTemplate(contents).substitute({})
                            except ValueError:
                                pass
                            except KeyError as e:
                                completer.set_message(_('Parece que hay variables de interpolación en el archivo $file ¿desea continuar sin interpolar?', file=srcpath.name))
                                if completer.binary_choice():
                                    literalfiles[destpath] = srcpath
                                else:
                                    return
                else:
                    literalfiles[destpath] = srcpath

    jobdir = AbsPath(pathjoin(stagedir, '.job'))

    inputfileexts = ['.' + i for i in config.inputfiles]
    outputfileexts = ['.' + i for i in config.outputfiles]

    if outdir.isdir():
        if jobdir.isdir():
            try:
                with open(pathjoin(jobdir, 'id'), 'r') as f:
                    jobid = f.read()
                success, status = getjobstate(jobid)
                if not success:
                    messages.failure(InterpolationTemplate(status).substitute(jobname=jobname))
                    return
            except FileNotFoundError:
                pass
        if not set(outdir.listdir()).isdisjoint(pathjoin((jobname, key)) for key in config.outputfiles):
            completer.set_message(_('Si corre este cálculo los archivos de salida existentes en el directorio $outdir serán sobreescritos, ¿desea continuar de todas formas?', outdir=outdir))
            if options.common.no or (not options.common.yes and not completer.binary_choice()):
                messages.failure(_('Cancelado por el usuario'))
                return
        for ext in outputfileexts:
            (outdir/jobname%ext).remove()
        if workdir != outdir:
            for ext in inputfileexts:
                (outdir/jobname%ext).remove()
    else:
        try:
            outdir.makedirs()
        except FileExistsError:
            messages.failure(_('No se puede crear la carpeta $outdir porque ya existe un archivo con el mismo nombre', outdir=outdir))
            return

    for destpath, litfile in literalfiles.items():
        litfile.copyas(destpath)

    for destpath, contents in interpolatedfiles.items():
        with open(destpath, 'w') as f:
            f.write(contents)

    for key, targetfile in options.targetfiles.items():
        targetfile.symlink(pathjoin(stagedir, (jobname, config.fileoptions[key])))

    if options.remote.host:

        remoteargs.gather(options.common)
        reloutdir = os.path.relpath(outdir, paths.home)
        remotehome = pathjoin(options.remote.root, (names.user, names.host))
        remotetemp = pathjoin(options.remote.root, (names.user, names.host, 'temp'))
        remoteargs.flags.add('raw')
        remoteargs.flags.add('job')
        remoteargs.flags.add('move')
        remoteargs.options['cwd'] = pathjoin(remotetemp, reloutdir)
        remoteargs.options['out'] = pathjoin(remotehome, reloutdir)
        for key, value in parameterdict.items():
            remoteargs.options[key] = val
        filelist = []
        for key in config.filekeys:
            if os.path.isfile(pathjoin(outdir, (jobname, key))):
                filelist.append(pathjoin(paths.home, '.', reloutdir, (jobname, key)))
        arglist = ['ssh', '-qt', '-S', paths.socket, options.remote.host]
        arglist.extend(env + '=' + val for env, val in environ.items())
        arglist.append(names.command)
        arglist.extend(opt(key) for key in remoteargs.flags)
        arglist.extend(opt(key, value) for key, value in remoteargs.options.items())
        arglist.extend(opt(key, value) for key, listval in remoteargs.multoptions.items() for value in listval)
        arglist.append(jobname)
        if options.debug.dry_run:
            print('<FILE LIST>', ' '.join(filelist), '</FILE LIST>')
            print('<COMMAND LINE>', ' '.join(arglist[3:]), '</COMMAND LINE>')
        else:
            try:
                check_output(['rsync', '-e', "ssh -S '{}'".format(paths.socket), '-qRLtz'] + filelist + [options.remote.host + ':' + remotetemp])
                check_output(['rsync', '-e', "ssh -S '{}'".format(paths.socket), '-qRLtz', '-f', '-! */'] + filelist + [options.remote.host + ':' + remotehome])
            except CalledProcessError as e:
                messages.error(_('Error al conectar con el servidor $host', host=options.remote.host), e.output.decode(sys.stdout.encoding).strip())
            call(arglist)

        return

    ############ Local execution ###########

    for path in config.parameterpaths:
        try:
            path = ConfigTemplate(path).safe_substitute(names)
            path = FilterGroupTemplate(path).substitute(filtergroups)
            path = InterpolationTemplate(path).substitute(parameterdict)
        except ValueError as e:
            messages.error(_('La ruta $path contiene variables de interpolación inválidas', path=path), f'key={e.args[0]}')
        except KeyError as e:
            messages.error(_('La ruta $path contiene variables de interpolación indefinidas', path=path), f'key={e.args[0]}')
        componentlist = pathsplit(path)
        trunk = AbsPath(componentlist.pop(0))
        for component in componentlist:
            trunk.assertdir()
            trunk = trunk/component
        parameterpaths.append(trunk)

    imports = []
    exports = []

    for key in config.inputfiles:
        if AbsPath(pathjoin(workdir, (inputname, key))).isfile():
            imports.append(script.importfile(pathjoin(stagedir, (jobname, key)), pathjoin(settings.execdir, config.filekeys[key])))

    for key in options.targetfiles:
        imports.append(script.importfile(pathjoin(stagedir, (jobname, config.fileoptions[key])), pathjoin(settings.execdir, config.filekeys[config.fileoptions[key]])))

    for path in parameterpaths:
        if path.isfile():
            imports.append(script.importfile(path, pathjoin(settings.execdir, path.name)))
        elif path.isdir():
            imports.append(script.importdir(pathjoin(path), settings.execdir))
        else:
            messages.error(_('La ruta de parámetros $path no existe', path=path))

    for key in config.outputfiles:
        exports.append(script.exportfile(pathjoin(settings.execdir, config.filekeys[key]), pathjoin(outdir, (jobname, key))))

    try:
        jobdir.mkdir()
    except FileExistsError:
        messages.failure(_('No se puede crear la carpeta $jobdir porque ya existe un archivo con ese nombre', jobdir=jobdir))
        return

    jobscript = pathjoin(jobdir, 'script')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash -x' + '\n')
        f.write(''.join(i + '\n' for i in script.head.values()))
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
        messages.success(_('Se procesó el trabajo "$jobname" y se generaron los archivos para el envío en el directorio $jobdir', jobname=jobname, jobdir=jobdir))
    else:
        try:
            time.sleep(config.delay + options.common.delay + os.stat(paths.lock).st_mtime - time.time())
        except (ValueError, FileNotFoundError) as e:
            pass
        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            messages.failure(_('El gestor de trabajos reportó un error al enviar el trabajo $jobname', error, jobname=jobname))
            return
        else:
            messages.success(_('El trabajo "$jobname" se correrá en $nproc núcleo(s) en $clustername con el número $jobid', jobname=jobname, nproc=options.common.nproc, clustername=names.cluster, jobid=jobid))
            with open(pathjoin(jobdir, 'id'), 'w') as f:
                f.write(jobid)
            with open(paths.lock, 'a'):
                os.utime(paths.lock, None)
