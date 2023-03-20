import os
import sys
from time import time, sleep
from subprocess import CalledProcessError, call, check_output
from clinterface import messages, prompts
from .queue import submitjob, getjobstate
from .utils import AttrDict, GlobDict, IdentityList, ConfTemplate, FormatTemplate, PrefixTemplate
from .utils import _, o, p, q, Q, template_substitute, template_parse, natsorted as sorted
from .shared import names, nodes, paths, config, iospec, options, remoteargs, environ, wrappers
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
       messages.error('Formato desconocido:', molformat)

def initialize():

    script.head = {}
    script.body = []

    for key, path in options.targetfiles.items():
        if not path.isfile():
            messages.error('El archivo de entrada', path, 'no existe', option=o(key))

    if options.remote.host:
        (paths.home/'.ssh').mkdir()
        paths.socket = paths.home / '.ssh' / pathjoin((options.remote.host, 'sock'))
        try:
            options.remote.root = check_output(['ssh', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=60', '-S', paths.socket, \
                options.remote.host, 'printenv QREMOTEROOT']).strip().decode(sys.stdout.encoding)
        except CalledProcessError as e:
            messages.error(e.output.decode(sys.stdout.encoding).strip())
        if not options.remote.root:
            messages.error('El servidor no está configurado para aceptar trabajos')

    if options.common.prompt:
        settings.defaults = False
    else:
        settings.defaults = True

    options.interpolationdict = {}

    for key in iospec.interpolationvars:
        try:
            options.interpolationdict[key] = options.interpolation[key]
        except KeyError:
            pass
    for i, var in enumerate(options.interpolation.posvars, start=1):
        options.interpolationdict[str(i)] = var

    if options.interpolationdict or options.interpolation.mol or options.interpolation.trjmol:
        options.interpolate = True
    else:
        options.interpolate = False

    if options.interpolate:
        if options.interpolation.mol:
            for i, path in enumerate(options.interpolation.mol, start=1):
                path = AbsPath(path, cwd=options.common.cwd)
                molprefix = path.stem
                coords = readmol(path)[-1]
                options.interpolationdict['mol' + str(i)] = geometry_block(coords)
        elif options.interpolation.trjmol:
            path = AbsPath(options.interpolation.trjmol, cwd=options.common.cwd)
            molprefix = path.stem
            for i, coords in enumerate(readmol(path), start=1):
                options.interpolationdict['mol' + str(i)] = geometry_block(coords)
        if options.interpolation.prefix:
            try:
                settings.prefix = PrefixTemplate(options.interpolation.prefix).substitute(options.interpolationdict)
            except ValueError as e:
                messages.error(_('El prefijo $prefix contiene variables de interpolación inválidas').substitute(prefix=options.interpolation.prefix), e.args[0])
            except KeyError as e:
                messages.error(_('El prefijo $prefix contiene variables de interpolación indefinidas').substitute(prefix=options.interpolation.prefix), key=e.args[0])
        else:
            if options.interpolation.mol:
                if len(options.interpolation.mol) == 1:
                    settings.prefix = molprefix
                else:
                    messages.error('Se debe especificar un prefijo cuando se especifican múltiples archivos de coordenadas')
            elif options.interpolation.trjmol:
                settings.prefix = molprefix
            else:
                messages.error('Se debe especificar un prefijo para interpolar sin archivo coordenadas')

    try:
        config.delay = float(config.delay)
    except ValueError:
        messages.error('El tiempo de espera debe ser un número', conf='delay')
    except AttributeError:
        config.delay = 0
    
    if not 'scratch' in config.defaults:
        messages.error('No se especificó el directorio de escritura por defecto', spec='defaults.scratch')

    if 'scratch' in options.common:
        settings.workdir = options.common.scratch / '$jobid'
    else:
        settings.workdir = AbsPath(ConfTemplate(config.defaults.scratch).substitute(names)) / '$jobid'

    if 'queue' not in options.common:
        if 'queue' in config.defaults:
            options.common.queue = config.defaults.queue
        else:
            messages.error('Debe especificar la cola a la que desea enviar el trabajo')
    
    for key in options.parametervars:
        if '/' in options.parametervars[key]:
            messages.error(options.parametervars[key], 'no puede ser una ruta', option=key)

    if 'mpilaunch' in iospec:
        try: iospec.mpilaunch = booleans[iospec.mpilaunch]
        except KeyError:
            messages.error('Este valor requiere ser "True" o "False"', spec='mpilaunch')
    
    if not iospec.filekeys:
        messages.error('La lista de archivos del programa no existe o está vacía', spec='filekeys')
    
    if iospec.inputfiles:
        for key in iospec.inputfiles:
            if not key in iospec.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='inputfiles')
    else:
        messages.error('La lista de archivos de entrada no existe o está vacía', spec='inputfiles')
    
    if iospec.outputfiles:
        for key in iospec.outputfiles:
            if not key in iospec.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='outputfiles')
    else:
        messages.error('La lista de archivos de salida no existe o está vacía', spec='outputfiles')

    if options.remote.host:
        return

    ############ Local execution ###########

    script.head['jobname'] = None

    if 'jobtype' in config:
        script.head['jobtype'] = ConfTemplate(config.jobtype).substitute(jobtype=config.specname)

    script.head['queue'] = ConfTemplate(config.queue).substitute(options.common)

    #TODO MPI support for Slurm
    if iospec.parallelib:
        if iospec.parallelib.lower() == 'none':
            if 'hosts' in options.common:
                for i, item in enumerate(config.serialat):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.serial):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
        elif iospec.parallelib.lower() == 'openmp':
            if 'hosts' in options.common:
                for i, item in enumerate(config.singlehostat):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.singlehost):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
            script.body.append('OMP_NUM_THREADS=' + str(options.common.nproc))
        elif iospec.parallelib.lower() == 'standalone':
            if 'hosts' in options.common:
                for i, item in enumerate(config.multihostat):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.multihost):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
        elif iospec.parallelib.lower() in wrappers:
            if 'hosts' in options.common:
                for i, item in enumerate(config.multihostat):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
            else:
                for i, item in enumerate(config.multihost):
                    script.head['span' + str(i)] = ConfTemplate(item).substitute(options.common)
            script.body.append(ConfTemplate(config.mpilauncher[iospec.parallelib]).substitute(options.common))
        else:
            messages.error('El tipo de paralelización', iospec.parallelib, 'no está soportado', spec='parallelib')
    else:
        messages.error('No se especificó el tipo de paralelización del programa', spec='parallelib')

    if not config.versions:
        messages.error('La lista de versiones no existe o está vacía', spec='versions')

    for version in config.versions:
        if not 'executable' in config.versions[version]:
            messages.error('No se especificó el ejecutable', spec='versions[{}].executable'.format(version))
    
    for version in config.versions:
        config.versions[version].merge({'load':[], 'source':[], 'export':{}})

    selector.set_message('Seleccione una versión:')
    selector.set_options(config.versions.keys())

    if 'version' in options.common:
        if options.common.version not in config.versions:
            messages.error('La versión', options.common.version, 'no es válida', option='version')
        settings.version = options.common.version
    elif 'version' in config.defaults:
        if not config.defaults.version in config.versions:
            messages.error('La versión establecida por defecto es inválida', spec='defaults.version')
        if settings.defaults:
            settings.version = config.defaults.version
        else:
            selector.set_single_default(config.defaults.version)
            settings.version = selector.single_choice()
    else:
        settings.version = selector.single_choice()

    ############ Find parameter paths ############

    config.parameterpaths = []

    for paramset in iospec.parameters:
        if paramset in config.parameters:
            for path in config.parameters[paramset]:
                config.parameterpaths.append(path)
        else:
            messages.error(_('No se definió la ruta al conjunto de parámetros $name').substitute(name=paramset))

    ############ Interactive parameter selection ###########

    formatdict = {}
    formatdict.update(names)

    if settings.defaults:
        formatdict.update(config.defaults.parametervars)

    formatdict.update(options.parametervars)

    for path in config.parameterpaths:
        componentlist = pathsplit(ConfTemplate(path).safe_substitute(formatdict))
        trunk = AbsPath(componentlist.pop(0))
        for component in componentlist:
            trunk.assertdir()
            try:
                ConfTemplate(component).substitute()
            except KeyError:
                if options:
                    selector.set_message('Seleccione un conjunto de parámetros:')
                    selector.set_options(sorted(trunk.glob(ConfTemplate(component).substitute(GlobDict()))))
                    choice = selector.single_choice()
                    options.parametervars.update(template_parse(component, choice))
                    trunk = trunk/choice
                else:
                    messages.error(trunk, 'no contiene elementos coincidentes con la ruta', path)
            else:
                trunk = trunk/component

    ############ End of interactive parameter selection ###########

    try:
        script.body.append(AbsPath(ConfTemplate(config.versions[settings.version].executable).substitute(names)))
    except NotAbsolutePath:
        script.body.append(config.versions[settings.version].executable)

    for i, path in enumerate(config.logfiles):
        script.head['log' + str(i)] = ConfTemplate(path).safe_substitute(dict(logdir=AbsPath(ConfTemplate(config.logdir).substitute(names))))

    script.head['shopt'] = "shopt -s nullglob extglob"

    for key, val in config.export.items() | config.versions[settings.version].export.items():
        if val:
            script.head[key + 'var'] = 'export {}={}'.format(key, val)
        else:
            messages.error('El valor de la variable de entorno {} es nulo'.format(envar), spec='export')

    for i, path in enumerate(config.source + config.versions[settings.version].source):
        if path:
            script.head['source' + str(i)] = 'source {}'.format(AbsPath(ConfTemplate(path).substitute(names)))
        else:
            messages.error('La ruta al script de configuración es nula', spec='source')

    if config.load or config.versions[settings.version].load:
        script.head['purge'] = 'module purge'

    for i, module in enumerate(config.load + config.versions[settings.version].load):
        if module:
            script.head['load' + str(i)] = 'module load {}'.format(module)
        else:
            messages.error('El nombre del módulo es nulo', spec='load')

    for key, val in config.envars.items():
        script.head[key + 'var'] = '{}="{}"'.format(key, val)

    for key, val in iospec.filevars.items():
        script.head[key + 'file'] = '{}="{}"'.format(key, iospec.filekeys[val])

    for key, val in names.items():
        script.head[key + 'name'] = '{}name="{}"'.format(key, val)

    for key, val in nodes.items():
        script.head[key + 'node'] = '{}node="{}"'.format(key, val)

    script.head['freeram'] = "freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')"
    script.head['totalram'] = "totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')"
    script.head['jobram'] = "jobram=$(($nproc*$totalram/$(nproc --all)))"

    for key in iospec.optargs:
        if not iospec.optargs[key] in iospec.filekeys:
            messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='optargs')
        script.body.append('-{key} {val}'.format(key=key, val=iospec.filekeys[iospec.optargs[key]]))
    
    for item in iospec.posargs:
        for key in item.split('|'):
            if not key in iospec.filekeys:
                messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='posargs')
        script.body.append('@' + p('|'.join(iospec.filekeys[i] for i in item.split('|'))))
    
    if 'stdinfile' in iospec:
        try:
            script.body.append('0<' + ' ' + iospec.filekeys[iospec.stdinfile])
        except KeyError:
            messages.error('La clave', q(iospec.stdinfile) ,'no tiene asociado ningún archivo', spec='stdinfile')
    if 'stdoutfile' in iospec:
        try:
            script.body.append('1>' + ' ' + iospec.filekeys[iospec.stdoutfile])
        except KeyError:
            messages.error('La clave', q(iospec.stdoutfile) ,'no tiene asociado ningún archivo', spec='stdoutfile')
    if 'stderror' in iospec:
        try:
            script.body.append('2>' + ' ' + iospec.filekeys[iospec.stderror])
        except KeyError:
            messages.error('La clave', q(iospec.stderror) ,'no tiene asociado ningún archivo', spec='stderror')
    
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
        messages.error('El método de copia', q(config.filesync), 'no es válido', spec='filesync')


def submit(parentdir, inputname, filtergroups):

    filestatus = {}
    for key in iospec.filekeys:
        path = AbsPath(pathjoin(parentdir, (inputname, key)))
        filestatus[key] = path.isfile() or key in options.targetfiles

    for conflict, message in iospec.conflicts.items():
        if BoolParser(conflict).evaluate(filestatus):
            messages.error(message, p(inputname))

    if 'prefix' in settings:
        jobname = settings.prefix + '.' + inputname
    else:
        jobname = inputname

    script.head['jobname'] = ConfTemplate(config.jobname).substitute(jobname=jobname)
    script.head['jobnamevar'] = 'jobname="{}"'.format(jobname)

    if 'out' in options.common:
        outdir = AbsPath(options.common.out, cwd=parentdir)
    else:
        outdir = AbsPath(jobname, cwd=parentdir)

    literalfiles = {}
    interpolatedfiles = {}

    if options.common.raw:
        stagedir = parentdir
    else:
        if outdir == parentdir:
            messages.failure('El directorio de salida debe ser distinto al directorio padre')
            return
        stagedir = outdir
        for key in iospec.inputfiles:
            srcpath = AbsPath(pathjoin(parentdir, (inputname, key)))
            destpath = pathjoin(stagedir, (jobname, key))
            if srcpath.isfile():
                if 'interpolable' in iospec and key in iospec.interpolable:
                    with open(srcpath, 'r') as f:
                        contents = f.read()
                        if options.interpolate:
                            try:
                                interpolatedfiles[destpath] = template_substitute(
                                    contents,
                                    options.interpolationdict,
                                    anchor=options.interpolation.anchor,
                                )
#                                print(interpolatedfiles[destpath])
                            except ValueError:
                                messages.failure(_('El archivo de entrada $file contiene variables de interpolación inválidas').substitute(file=pathjoin((inputname, key))), e.args[0])
                                return
                            except KeyError as e:
                                messages.failure(_('El archivo de entrada $file contiene variables de interpolación indefinidas').substitute(file=pathjoin((inputname, key))), key=e.args[0])
                                return
                        else:
                            try:
                                interpolatedfiles[destpath] = template_substitute(contents, {}, anchor=options.interpolation.anchor)
                            except ValueError:
                                pass
                            except KeyError as e:
                                completer.set_message(_('Parece que hay variables de interpolación en el archivo de entrada $path ¿desea continuar sin interpolar?').substitute(path=pathjoin((inputname, key))))
                                if completer.binary_choice():
                                    literalfiles[destpath] = srcpath
                                else:
                                    return
                else:
                    literalfiles[destpath] = srcpath

    jobdir = AbsPath(pathjoin(stagedir, '.job'))

    inputfileexts = ['.' + i for i in iospec.inputfiles]
    outputfileexts = ['.' + i for i in iospec.outputfiles]

    if outdir.isdir():
        if jobdir.isdir():
            try:
                with open(pathjoin(jobdir, 'id'), 'r') as f:
                    jobid = f.read()
                jobstate = getjobstate(jobid)
                if jobstate is not None:
                    messages.failure(jobstate.format(id=jobid, name=jobname))
                    return
            except FileNotFoundError:
                pass
        if not set(outdir.listdir()).isdisjoint(pathjoin((jobname, key)) for key in iospec.outputfiles):
            completer.set_message(_('Si corre este cálculo los archivos de salida existentes en el directorio $outdir serán sobreescritos, ¿desea continuar de todas formas?').substitute(outdir=outdir))
            if options.common.no or (not options.common.yes and not completer.binary_choice()):
                messages.failure('Cancelado por el usuario')
                return
        for ext in outputfileexts:
            outdir.append(jobname + ext).remove()
        if parentdir != outdir:
            for ext in inputfileexts:
                outdir.append(jobname + ext).remove()
    else:
        try:
            outdir.makedirs()
        except FileExistsError:
            messages.failure('No se puede crear la carpeta', outdir, 'porque ya existe un archivo con ese nombre')
            return

    for destpath, litfile in literalfiles.items():
        litfile.copyfile(destpath)

    for destpath, contents in interpolatedfiles.items():
        with open(destpath, 'w') as f:
            f.write(contents)

    for key, targetfile in options.targetfiles.items():
        targetfile.symlink(pathjoin(stagedir, (jobname, iospec.fileoptions[key])))

    if options.remote.host:

        reloutdir = os.path.relpath(outdir, paths.home)
        remotehome = pathjoin(options.remote.root, (names.user, names.host))
        remotetemp = pathjoin(options.remote.root, (names.user, names.host, 'temp'))
        remoteargs.flags.add('raw')
        remoteargs.flags.add('job')
        remoteargs.flags.add('move')
        remoteargs.options['cwd'] = pathjoin(remotetemp, reloutdir)
        remoteargs.options['out'] = pathjoin(remotehome, reloutdir)
        for key, val in options.parametervars.items():
            remoteargs.options[key] = val
        filelist = []
        for key in iospec.filekeys:
            if os.path.isfile(pathjoin(outdir, (jobname, key))):
                filelist.append(pathjoin(paths.home, '.', reloutdir, (jobname, key)))
        arglist = ['ssh', '-qt', '-S', paths.socket, options.remote.host]
        arglist.extend(env + '=' + val for env, val in environ.items())
        arglist.append(names.command)
        arglist.extend(o(opt) for opt in remoteargs.flags)
        arglist.extend(o(opt, Q(val)) for opt, val in remoteargs.options.items())
        arglist.extend(o(opt, Q(val)) for opt, lst in remoteargs.multoptions.items() for val in lst)
        arglist.append(jobname)
        if options.debug.dry_run:
            print('<FILE LIST>', ' '.join(filelist), '</FILE LIST>')
            print('<COMMAND LINE>', ' '.join(arglist[3:]), '</COMMAND LINE>')
        else:
            try:
                check_output(['rsync', '-e', "ssh -S '{}'".format(paths.socket), '-qRLtz'] + filelist + [options.remote.host + ':' + remotetemp])
                check_output(['rsync', '-e', "ssh -S '{}'".format(paths.socket), '-qRLtz', '-f', '-! */'] + filelist + [options.remote.host + ':' + remotehome])
            except CalledProcessError as e:
                messages.error(e.output.decode(sys.stdout.encoding).strip())
            call(arglist)

        return

    ############ Local execution ###########

    formatdict = {}
    formatdict.update(names)
    formatdict.update(config.defaults.parametervars)
    formatdict.update(options.parametervars)

    for path in config.parameterpaths:
        try:
            path = FormatTemplate(path).safe_substitute(formatdict)
            path = FormatTemplate(path).substitute(filtergroups)
        except ValueError as e:
            messages.error(_('La ruta $path contiene variables de interpolación inválidas').substitute(path=path), e.args[0])
        except KeyError as e:
            messages.error(_('La ruta $path contiene variables de interpolación indefinidas').substitute(path=path), key=e.args[0])
        componentlist = pathsplit(path)
        trunk = AbsPath(componentlist.pop(0))
        for component in componentlist:
            trunk.assertdir()
            trunk = trunk / component
        parameterpaths.append(trunk)

    imports = []
    exports = []

    for key in iospec.inputfiles:
        if AbsPath(pathjoin(parentdir, (inputname, key))).isfile():
            imports.append(script.importfile(pathjoin(stagedir, (jobname, key)), pathjoin(settings.workdir, iospec.filekeys[key])))

    for key in options.targetfiles:
        imports.append(script.importfile(pathjoin(stagedir, (jobname, iospec.fileoptions[key])), pathjoin(settings.workdir, iospec.filekeys[iospec.fileoptions[key]])))

    for path in parameterpaths:
        if path.isfile():
            imports.append(script.importfile(path, pathjoin(settings.workdir, path.name)))
        elif path.isdir():
            imports.append(script.importdir(pathjoin(path), settings.workdir))
        else:
            messages.error('La ruta de parámetros', path, 'no existe')

    for key in iospec.outputfiles:
        exports.append(script.exportfile(pathjoin(settings.workdir, iospec.filekeys[key]), pathjoin(outdir, (jobname, key))))

    try:
        jobdir.mkdir()
    except FileExistsError:
        messages.failure('No se puede crear la carpeta', jobdir, 'porque ya existe un archivo con ese nombre')
        return

    jobscript = pathjoin(jobdir, 'script')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash -x' + '\n')
        f.write(''.join(i + '\n' for i in script.head.values()))
        f.write(script.makedir(settings.workdir) + '\n')
        f.write(''.join(i + '\n' for i in imports))
        f.write(script.chdir(settings.workdir) + '\n')
        f.write(''.join(i + '\n' for i in iospec.prescript))
        f.write(' '.join(script.body) + '\n')
        f.write(''.join(i + '\n' for i in iospec.postscript))
        f.write(''.join(i + '\n' for i in exports))
        f.write(script.removedir(settings.workdir) + '\n')
        f.write(''.join(i + '\n' for i in config.offscript))

    if options.debug.dry_run:
        messages.success('Se procesó el trabajo', q(jobname), 'y se generaron los archivos para el envío en', jobdir)
    else:
        try:
            sleep(config.delay + options.common.delay + os.stat(paths.lock).st_mtime - time())
        except (ValueError, FileNotFoundError) as e:
            pass
        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            messages.failure('El gestor de trabajos reportó un error al enviar el trabajo', q(jobname), p(error))
            return
        else:
            messages.success('El trabajo', q(jobname), 'se correrá en', str(options.common.nproc), 'núcleo(s) en', names.cluster, 'con el número', jobid)
            with open(pathjoin(jobdir, 'id'), 'w') as f:
                f.write(jobid)
            with open(paths.lock, 'a'):
                os.utime(paths.lock, None)
