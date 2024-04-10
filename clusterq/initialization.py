import sys
#from tkdialogs import messages, prompts
from clinterface import messages, prompts, _
from subprocess import CalledProcessError, check_output
from .shared import booleans, names, nodes, paths, config, options, settings, status, script, parameterdict, interpolationdict, parameterpaths
from .utils import GlobDict, LogDict, ConfigTemplate, FilterGroupTemplate, InterpolationTemplate, template_parse, natural_sorted as sorted
from .fileutils import AbsPath, NotAbsolutePath
from .readmol import readmol, molblock

selector = prompts.Selector()
completer = prompts.Completer()
completer.set_truthy_options(['si', 'yes'])
completer.set_falsy_options(['no'])

def initialize():

    status.initialized = True

    script.head = {}
    script.body = []

    for key, path in options.targetfiles.items():
        if not path.isfile():
            messages.error(_('El archivo de entrada no existe'), f'options.targetfiles.items[{key}]={path}')

    if options.remote.host:
        (paths.home/'.ssh').mkdir()
        paths.socket = paths.home/'.ssh'/options.remote.host*'sock'
        try:
            paths.remotedir = check_output(['ssh', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=60', '-S', paths.socket, \
                options.remote.host, 'printenv CLUSTERQ_REMOTE || true']).strip().decode(sys.stdout.encoding)
        except CalledProcessError as e:
            messages.error(_('Error al conectar con el servidor $host', host=options.remote.host), e.output.decode(sys.stdout.encoding).strip())
        if paths.remotedir:
            paths.remotedir = AbsPath(paths.remotedir)
        else:
            messages.error(_('El servidor $host no está configurado para aceptar trabajos', host=options.remote.host))

    if options.common.prompt:
        settings.defaults = False
    else:
        settings.defaults = True

    interpolationdict.update(options.interpolopts)

    for i, var in enumerate(options.interpolation.posvars, start=1):
        interpolationdict[str(i)] = var

    if options.interpolation.mol or options.interpolation.trjmol or interpolationdict:
        options.interpolate = True
    else:
        options.interpolate = False

    for key, value in options.parameteropts.items():
        if '/' in options.parameteropts[key]:
            messages.error(_('El nombre del conjunto de parámetros no es válido'), f'options.parameteropts[{key}]={value}')

    parameterdict.update(options.parameteropts)

    if options.interpolate:
        if options.interpolation.mol:
            for i, path in enumerate(options.interpolation.mol, start=1):
                path = AbsPath(path, parent=options.common.cwd)
                molprefix = path.stem
                coords = readmol(path)[-1]
                interpolationdict[f'mol{i}'] = molblock(coords)
        elif options.interpolation.trjmol:
            path = AbsPath(options.interpolation.trjmol, parent=options.common.cwd)
            molprefix = path.stem
            for i, coords in enumerate(readmol(path), start=1):
                interpolationdict[f'mol{i}'] = molblock(coords)
        if options.interpolation.prefix:
            try:
                settings.prefix = InterpolationTemplate(options.interpolation.prefix).substitute(interpolationdict)
            except ValueError as e:
                messages.error(_('El prefijo contiene variables de interpolación inválidas'), f'options.interpolation.prefix={options.interpolation.prefix}, key={e.args[0]}')
            except KeyError as e:
                messages.error(_('El prefijo contiene variables de interpolación indefinidas'), f'options.interpolation.prefix={options.interpolation.prefix}, key={e.args[0]}')
        elif options.interpolation.suffix:
            try:
                settings.suffix = InterpolationTemplate(options.interpolation.suffix).substitute(interpolationdict)
            except ValueError as e:
                messages.error(_('El prefijo contiene variables de interpolación inválidas'), f'options.interpolation.suffix={options.interpolation.suffix}, key={e.args[0]}')
            except KeyError as e:
                messages.error(_('El prefijo contiene variables de interpolación indefinidas'), f'options.interpolation.suffix={options.interpolation.suffix}, key={e.args[0]}')
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

    if 'delay' in options.common:
        delay = options.common.delay
    elif 'delay' in config.defaults:
        delay = config.defaults.delay
    else:
        delay = None

    if delay is not None:
        try:
            config.local.delay = float(delay)
        except ValueError:
            messages.error(_('El tiempo de espera entre trabajos debe ser un número'), f'delay={delay}')
    
    if not 'scratch' in config.defaults:
        messages.error(_('No se especificó el directorio de escritura por defecto'), f'config.defaults.scratch={config.defaults.scratch}')

    if 'scratch' in options.common:
        settings.execdir = AbsPath(options.common.scratch/'$jobid')
    else:
        settings.execdir = AbsPath(ConfigTemplate(config.defaults.scratch).substitute(names))/'$jobid'

    if 'queue' in options.common:
        options.local.queue = options.common.queue
    elif 'queue' in config.defaults:
        options.local.queue = config.defaults.queue
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

    script.head['queue'] = ConfigTemplate(config.queue).substitute(options.local)

    #TODO MPI support for Slurm
    if config.parallel:
        if config.parallel.lower() == 'none':
            if 'hosts' in options.common:
                for i, item in enumerate(config.serialat):
                    script.head[f'span{i}'] = ConfigTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.serial):
                    script.head[f'span{i}'] = ConfigTemplate(item).substitute(options.common)
        elif config.parallel.lower() == 'omp':
            if 'hosts' in options.common:
                for i, item in enumerate(config.singlehostat):
                    script.head[f'span{i}'] = ConfigTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.singlehost):
                    script.head[f'span{i}'] = ConfigTemplate(item).substitute(options.common)
            script.body.append(f'OMP_NUM_THREADS={options.common.nproc}')
        elif config.parallel.lower() == 'mpi':
            if 'hosts' in options.common:
                for i, item in enumerate(config.multihostat):
                    script.head[f'span{i}'] = ConfigTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.multihost):
                    script.head[f'span{i}'] = ConfigTemplate(item).substitute(options.common)
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
            trunk = AbsPath()
            for part in AbsPath(path).parts:
                trunk.assertdir()
                try:
                    InterpolationTemplate(part).substitute()
                except KeyError:
                    selector.set_message(_('Seleccione un conjunto de parámetros:'))
                    selector.set_options(sorted(trunk.glob(InterpolationTemplate(part).substitute(GlobDict()))))
                    choice = selector.single_choice()
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
        script.head[f'log{i}'] = ConfigTemplate(path).safe_substitute(dict(logdir=AbsPath(ConfigTemplate(config.logdir).substitute(names))))

    script.head['shopt'] = "shopt -s nullglob extglob"

    for key, value in config.export.items():
        if value:
            script.head[f'{key}var'] = f'export {key}={value}'
        else:
            messages.error(_('La variable de entorno está vacía'), f'config.export[{key}]')

    for key, value in config.versions[settings.version].export.items():
        if value:
            script.head[f'{key}var'] = f'export {key}={value}'
        else:
            messages.error(_('La variable de entorno está vacía'), f'config.export[{key}]')

    for i, path in enumerate(config.source + config.versions[settings.version].source):
        if path:
            script.head[f'source{i}'] = f'source {AbsPath(ConfigTemplate(path).substitute(names))}'
        else:
            messages.error(_('La ruta del script de configuración está vacía'), 'config.source')

    if config.load or config.versions[settings.version].load:
        script.head['purge'] = 'module purge'

    for i, module in enumerate(config.load + config.versions[settings.version].load):
        if module:
            script.head[f'load{i}'] = f'module load {module}'
        else:
            messages.error(_('El nombre del módulo es nulo'), 'config.load')

    for key, value in config.envars.items():
        script.head[f'{key}'] = f'{key}="{value}"'

    for key, value in config.filevars.items():
        script.head[f'{key}'] = f'{key}="{config.filekeys[value]}"'

    for key, value in names.items():
        script.head[f'{key}name'] = f'{key}name="{value}"'

    for key, value in nodes.items():
        script.head[f'{key}node'] = f'{key}node="{value}"'

    script.head['freeram'] = "freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')"
    script.head['totalram'] = "totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')"
    script.head['jobram'] = "jobram=$(($nproc*$totalram/$(nproc --all)))"

    for key in config.optargs:
        if not config.optargs[key] in config.filekeys:
            messages.error(_('Elemento no encontrado'), f'{key} in config.optargs but not in config.filekeys')
        script.body.append(f'-{key} {config.filekeys[config.optargs[key]]}')
    
    for item in config.posargs:
        for key in item.split('|'):
            if not key in config.filekeys:
                messages.error(_('Elemento no encontrado'), f'{key} in config.posargs but not in config.filekeys')
        script.body.append(f"@({'|'.join(config.filekeys[i] for i in item.split('|'))})")
    
    if 'stdinfile' in config:
        try:
            script.body.append(f'0< {config.filekeys[config.stdinfile]}')
        except KeyError:
            messages.error(_('Elemento no encontrado'), f'config.stdinfile={config.stdinfile} not in config.filekeys')

    if 'stdoutfile' in config:
        try:
            script.body.append(f'1> {config.filekeys[config.stdoutfile]}')
        except KeyError:
            messages.error(_('Elemento no encontrado'), f'config.stdoutfile={config.stdoutfile} not in config.filekeys')

    if 'stderrfile' in config:
        try:
            script.body.append(f'2> {config.filekeys[config.stderrfile]}')
        except KeyError:
            messages.error(_('Elemento no encontrado'), f'config.stderrfile={config.stderrfile} not in config.filekeys')
    
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
