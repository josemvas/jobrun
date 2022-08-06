import os
import sys
from time import time, sleep
from subprocess import CalledProcessError, call, check_output
from clinterface import Selector, Completer
from . import messages
from .defs import wrappers
from .queue import submitjob, getjobstate
from .utils import natsorted as sorted
from .utils import AttrDict, FormatDict, IdentityList, o, p, q, Q, _, join_args, booldict, getformatkeys, interpolate, format_parse
from .shared import names, nodes, paths, environ, sysconf, queuespec, packagespec, options, remoteargs
from .fileutils import AbsPath, NotAbsolutePath, pathsplit, pathjoin, remove
from .parsing import BoolParser
from .readmol import readmol

parameterpaths = []
settings = AttrDict()
script = AttrDict()

selector = Selector()
completer = Completer()

def geometry_block(coords):
    if packagespec.packagename in ('Gaussian', 'deMon2k'):
        return '\n'.join('{:<2s}  {:10.4f}  {:10.4f}  {:10.4f}'.format(*line) for line in coords)
    elif packagespec.packagename in ('DFTB+'):
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

    script.main = []
    script.setup = []
    script.header = []
    script.envars = []

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

    if options.interpolation.vars or options.interpolation.mol or 'trjmol' in options.interpolation:
        options.interpolation.interpolate = True
    else:
        options.interpolation.interpolate = False

    options.interpolation.list = []
    options.interpolation.dict = {}

    if options.interpolation.interpolate:
        if options.interpolation.vars:
            for var in options.interpolation.vars:
                left, separator, right = var.partition('=')
                if separator:
                    if right:
                        options.interpolation.dict[left] = right
                    else:
                        messages.error('No se especificó ningín valor para la variable de interpolación', left)
                else:
                    options.interpolation.list.append(left)
        if options.interpolation.mol:
            index = 0
            for path in options.interpolation.mol:
                index += 1
                path = AbsPath(path, cwd=options.common.cwd)
                coords = readmol(path)[-1]
                options.interpolation.dict['mol' + str(index)] = geometry_block(coords)
            if not 'prefix' in options.interpolation:
                if len(options.interpolation.mol) == 1:
                    settings.prefix = path.stem
                else:
                    messages.error('Se debe especificar un prefijo cuando se especifican múltiples archivos de coordenadas')
        elif 'trjmol' in options.interpolation:
            index = 0
            path = AbsPath(options.interpolation.trjmol, cwd=options.common.cwd)
            for coords in readmol(path):
                index += 1
                options.interpolation.dict['mol' + str(index)] = geometry_block(coords)
            if not 'prefix' in options.interpolation:
                settings.prefix = path.stem
        else:
            if not 'prefix' in options.interpolation and not 'suffix' in options.interpolation:
                messages.error('Se debe especificar un prefijo o un sufijo para interpolar sin archivo coordenadas')

    try:
        sysconf.delay = float(sysconf.delay)
    except ValueError:
        messages.error('El tiempo de espera debe ser un número', conf='delay')
    except AttributeError:
        sysconf.delay = 0
    
    if not 'scratch' in sysconf.defaults:
        messages.error('No se especificó el directorio de escritura por defecto', spec='defaults.scratch')

    if 'scratch' in options.common:
        settings.workdir = options.common.scratch / '$jobid'
    else:
        settings.workdir = AbsPath(sysconf.defaults.scratch.format_map(names)) / '$jobid'

    if 'queue' not in options.common:
        if 'queue' in sysconf.defaults:
            options.common.queue = sysconf.defaults.queue
        else:
            messages.error('Debe especificar la cola a la que desea enviar el trabajo')
    
    if not 'packagename' in packagespec:
        messages.error('No se especificó el nombre del programa', spec='packagename')
    
    for key in options.parameterkeys:
        if '/' in options.parameterkeys[key]:
            messages.error(options.parameterkeys[key], 'no puede ser una ruta', option=key)

    if 'mpilaunch' in packagespec:
        try: packagespec.mpilaunch = booldict[packagespec.mpilaunch]
        except KeyError:
            messages.error('Este valor requiere ser "True" o "False"', spec='mpilaunch')
    
    if not packagespec.filekeys:
        messages.error('La lista de archivos del programa no existe o está vacía', spec='filekeys')
    
    if packagespec.inputfiles:
        for key in packagespec.inputfiles:
            if not key in packagespec.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='inputfiles')
    else:
        messages.error('La lista de archivos de entrada no existe o está vacía', spec='inputfiles')
    
    if packagespec.outputfiles:
        for key in packagespec.outputfiles:
            if not key in packagespec.filekeys:
                messages.error('La clave', q(key), 'no tiene asociado ningún archivo', spec='outputfiles')
    else:
        messages.error('La lista de archivos de salida no existe o está vacía', spec='outputfiles')

    if 'prefix' in options.interpolation:
        try:
            settings.prefix = interpolate(
                options.interpolation.prefix,
                anchor='%',
                formlist=options.interpolation.list,
                formdict=options.interpolation.dict,
            )
        except ValueError as e:
            messages.error('Hay variables de interpolación inválidas en el prefijo', opt='--prefix', var=e.args[0])
        except (IndexError, KeyError) as e:
            messages.error('Hay variables de interpolación sin definir en el prefijo', opt='--prefix', var=e.args[0])

    if 'suffix' in options.interpolation:
        try:
            settings.suffix = interpolate(
                options.interpolation.suffix,
                anchor='%',
                formlist=options.interpolation.list,
                formdict=options.interpolation.dict,
            )
        except ValueError as e:
            messages.error('Hay variables de interpolación inválidas en el sufijo', opt='--suffix', var=e.args[0])
        except (IndexError, KeyError) as e:
            messages.error('Hay variables de interpolación sin definir en el sufijo', opt='--suffix', var=e.args[0])

    if options.remote.host:
        return

    ############ Local execution ###########

    if 'jobinfo' in queuespec:
        script.header.append(queuespec.jobinfo.format(packagespec.packagename))

    #TODO MPI support for Slurm
    if packagespec.parallelib:
        if packagespec.parallelib.lower() == 'none':
            if 'nodelist' in options.common:
                for item in queuespec.serialat:
                    script.header.append(item.format(**options.common))
            else:
                for item in queuespec.serial:
                    script.header.append(item.format(**options.common))
        elif packagespec.parallelib.lower() == 'openmp':
            if 'nodelist' in options.common:
                for item in queuespec.singlehostat:
                    script.header.append(item.format(**options.common))
            else:
                for item in queuespec.singlehost:
                    script.header.append(item.format(**options.common))
            script.main.append('OMP_NUM_THREADS=' + str(options.common.nproc))
        elif packagespec.parallelib.lower() == 'standalone':
            if 'nodelist' in options.common:
                for item in queuespec.multihostat:
                    script.header.append(item.format(**options.common))
            else:
                for item in queuespec.multihost:
                    script.header.append(item.format(**options.common))
        elif packagespec.parallelib.lower() in wrappers:
            if 'nodelist' in options.common:
                for item in queuespec.multihostat:
                    script.header.append(item.format(**options.common))
            else:
                for item in queuespec.multihost:
                    script.header.append(item.format(**options.common))
            script.main.append(queuespec.mpilauncher[packagespec.parallelib])
        else:
            messages.error('El tipo de paralelización', packagespec.parallelib, 'no está soportado', spec='parallelib')
    else:
        messages.error('No se especificó el tipo de paralelización del programa', spec='parallelib')

    if not sysconf.versions:
        messages.error('La lista de versiones no existe o está vacía', spec='versions')

    for version in sysconf.versions:
        if not 'executable' in sysconf.versions[version]:
            messages.error('No se especificó el ejecutable', spec='versions[{}].executable'.format(version))
    
    for version in sysconf.versions:
        sysconf.versions[version].merge({'load':[], 'source':[], 'export':{}})

    selector.message = 'Seleccione una versión:'
    selector.options = tuple(sysconf.versions.keys())

    if 'version' in options.common:
        if options.common.version not in sysconf.versions:
            messages.error('La versión', options.common.version, 'no es válida', option='version')
        settings.version = options.common.version
    elif 'version' in sysconf.defaults:
        if not sysconf.defaults.version in sysconf.versions:
            messages.error('La versión establecida por defecto es inválida', spec='defaults.version')
        if settings.defaults:
            settings.version = sysconf.defaults.version
        else:
            selector.default = sysconf.defaults.version
            settings.version = selector.single_choice()
    else:
        settings.version = selector.single_choice()

    ############ Interactive parameter selection ###########

    formatdict = FormatDict()
    formatdict.update(names)

    if settings.defaults:
        formatdict.update(sysconf.defaults.parameterkeys)

    formatdict.update(options.parameterkeys)

    for path in sysconf.parameterpaths:
        componentlist = pathsplit(path.format_map(formatdict))
        trunk = AbsPath(componentlist.pop(0))
        for component in componentlist:
            try:
                trunk.assertdir()
            except OSError as e:
                messages.excinfo(e, trunk)
                raise SystemExit
            if getformatkeys(component):
                selector.message = 'Seleccione un conjunto de parámetros:'
                selector.options = sorted(trunk.glob(component.format_map(FormatDict('*'))))
                if selector.options:
                    choice = selector.single_choice()
                    options.parameterkeys.update(format_parse(component, choice))
                    trunk = trunk / choice
                else:
                    messages.error(trunk, 'no contiene elementos coincidentes con la ruta', path)
            else:
                trunk = trunk / component

    ############ End of interactive parameter selection ###########

    for envar, value in sysconf.export.items() | sysconf.versions[settings.version].export.items():
        if value:
            script.setup.append('export {0}={1}'.format(envar, value))
        else:
            messages.error('El valor de la variable de entorno {} es nulo'.format(envar), spec='export')

    for path in sysconf.source + sysconf.versions[settings.version].source:
        if path:
            script.setup.append('source {}'.format(AbsPath(path.format_map(names))))
        else:
            messages.error('La ruta al script de configuración es nula', spec='source')

    if sysconf.load or sysconf.versions[settings.version].load:
        script.setup.append('module purge')

    for module in sysconf.load + sysconf.versions[settings.version].load:
        if module:
            script.setup.append('module load {}'.format(module))
        else:
            messages.error('El nombre del módulo es nulo', spec='load')

    try:
        script.main.append(AbsPath(sysconf.versions[settings.version].executable.format_map(names)))
    except NotAbsolutePath:
        script.main.append(sysconf.versions[settings.version].executable)

    for path in queuespec.logfiles:
        script.header.append(path.format(AbsPath(sysconf.logdir.format_map(names))))

    script.setup.append("shopt -s nullglob extglob")

    script.setenv = '{}="{}"'.format

    script.envars.extend(queuespec.envars.items())
    script.envars.extend((k + 'name', v) for k, v in names.items())
    script.envars.extend((k + 'node', v) for k, v in nodes.items())
    script.envars.extend((k, packagespec.filekeys[v]) for k, v in packagespec.filevars.items())

    script.envars.append(("freeram", "$(free -m | tail -n+3 | head -1 | awk '{print $4}')"))
    script.envars.append(("totalram", "$(free -m | tail -n+2 | head -1 | awk '{print $2}')"))
    script.envars.append(("jobram", "$(($nproc*$totalram/$(nproc --all)))"))

    for key in packagespec.optargs:
        if not packagespec.optargs[key] in packagespec.filekeys:
            messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='optargs')
        script.main.append('-{key} {val}'.format(key=key, val=packagespec.filekeys[packagespec.optargs[key]]))
    
    for item in packagespec.posargs:
        for key in item.split('|'):
            if not key in packagespec.filekeys:
                messages.error('La clave', q(key) ,'no tiene asociado ningún archivo', spec='posargs')
        script.main.append('@' + p('|'.join(packagespec.filekeys[i] for i in item.split('|'))))
    
    if 'stdinfile' in packagespec:
        try:
            script.main.append('0<' + ' ' + packagespec.filekeys[packagespec.stdinfile])
        except KeyError:
            messages.error('La clave', q(packagespec.stdinfile) ,'no tiene asociado ningún archivo', spec='stdinfile')
    if 'stdoutfile' in packagespec:
        try:
            script.main.append('1>' + ' ' + packagespec.filekeys[packagespec.stdoutfile])
        except KeyError:
            messages.error('La clave', q(packagespec.stdoutfile) ,'no tiene asociado ningún archivo', spec='stdoutfile')
    if 'stderror' in packagespec:
        try:
            script.main.append('2>' + ' ' + packagespec.filekeys[packagespec.stderror])
        except KeyError:
            messages.error('La clave', q(packagespec.stderror) ,'no tiene asociado ningún archivo', spec='stderror')
    
    script.chdir = 'cd "{}"'.format
    if sysconf.filesync == 'local':
        script.makedir = 'mkdir -p -m 700 "{}"'.format
        script.removedir = 'rm -rf "{}"'.format
        if options.common.temporary:
            script.importfile = 'mv "{}" "{}"'.format
        else:
            script.importfile = 'cp "{}" "{}"'.format
        script.importdir = 'cp -r "{}/." "{}"'.format
        script.exportfile = 'cp "{}" "{}"'.format
    elif sysconf.filesync == 'remote':
        script.makedir = 'for host in ${{hostlist[*]}}; do rsh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.removedir = 'for host in ${{hostlist[*]}}; do rsh $host rm -rf "\'{}\'"; done'.format
        if options.common.temporary:
            script.importfile = 'for host in ${{hostlist[*]}}; do rcp $headnode:"\'{0}\'" $host:"\'{1}\'" && rsh $headnode rm "\'{0}\'"; done'.format
        else:
            script.importfile = 'for host in ${{hostlist[*]}}; do rcp $headnode:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.importdir = 'for host in ${{hostlist[*]}}; do rsh $host cp -r "\'{0}/.\'" "\'{1}\'"; done'.format
        script.exportfile = 'rcp "{}" $headnode:"\'{}\'"'.format
    elif sysconf.filesync == 'secure':
        script.makedir = 'for host in ${{hostlist[*]}}; do ssh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.removedir = 'for host in ${{hostlist[*]}}; do ssh $host rm -rf "\'{}\'"; done'.format
        if options.common.temporary:
            script.importfile = 'for host in ${{hostlist[*]}}; do scp $headnode:"\'{0}\'" $host:"\'{1}\'" && ssh $headnode rm "\'{0}\'"; done'.format
        else:
            script.importfile = 'for host in ${{hostlist[*]}}; do scp $headnode:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.importdir = 'for host in ${{hostlist[*]}}; do ssh $host cp -r "\'{0}/.\'" "\'{1}\'"; done'.format
        script.exportfile = 'scp "{}" $headnode:"\'{}\'"'.format
    else:
        messages.error('El método de copia', q(sysconf.filesync), 'no es válido', spec='filesync')


def submit(parentdir, inputname, filtergroups):

    filebools = {key: AbsPath(pathjoin(parentdir, (inputname, key))).isfile() or key in options.targetfiles for key in packagespec.filekeys}
    for conflict, message in packagespec.conflicts.items():
        if BoolParser(conflict).evaluate(filebools):
            messages.error(message, p(inputname))

    jobname = inputname

    if 'prefix' in settings:
        jobname = settings.prefix + '.' + jobname

    if 'suffix' in settings:
        jobname = jobname +  '.' + settings.suffix

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
        for key in packagespec.inputfiles:
            srcpath = AbsPath(pathjoin(parentdir, (inputname, key)))
            destpath = pathjoin(stagedir, (jobname, key))
            if srcpath.isfile():
                if 'interpolable' in packagespec and key in packagespec.interpolable:
                    with open(srcpath, 'r') as f:
                        contents = f.read()
                        if options.interpolation.interpolate:
                            try:
                                interpolatedfiles[destpath] = interpolate(
                                    contents,
                                    anchor=options.interpolation.anchor,
                                    formlist=options.interpolation.list,
                                    formdict=options.interpolation.dict,
                                )
                            except ValueError:
                                messages.failure('Hay variables de interpolación inválidas en el archivo de entrada', pathjoin((inputname, key)))
                                return
                            except (IndexError, KeyError) as e:
                                messages.failure('Hay variables de interpolación sin definir en el archivo de entrada', pathjoin((inputname, key)), p(e.args[0]))
                                return
                        else:
                            try:
                                interpolatedfiles[destpath] = interpolate(contents, anchor=options.interpolation.anchor)
                            except ValueError:
                                pass
                            except (IndexError, KeyError) as e:
                                completer.message = _('Parece que hay variables de interpolación en el archivo de entrada $path ¿desea continuar sin interpolar?').substitute(path=pathjoin((inputname, key)))
                                completer.options = {True: ['si', 'yes'], False: ['no']}
                                if completer.binary_choice():
                                    literalfiles[destpath] = srcpath
                                else:
                                    return
                else:
                    literalfiles[destpath] = srcpath

    jobdir = AbsPath(pathjoin(stagedir, '.job'))

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
        if not set(outdir.listdir()).isdisjoint(pathjoin((jobname, k)) for k in packagespec.outputfiles):
            completer.message = _('Si corre este cálculo los archivos de salida existentes en el directorio $outdir serán sobreescritos, ¿desea continuar de todas formas?').substitute(outdir=outdir)
            completer.options = {True: ['si', 'yes'], False: ['no']}
            if options.common.no or (not options.common.yes and not completer.binary_choice()):
                messages.failure('Cancelado por el usuario')
                return
        for key in packagespec.outputfiles:
            remove(pathjoin(outdir, (jobname, key)))
        if parentdir != outdir:
            for key in packagespec.inputfiles:
                remove(pathjoin(outdir, (jobname, key)))
    else:
        try:
            outdir.makedirs()
        except FileExistsError:
            messages.failure('No se puede crear la carpeta', outdir, 'porque ya existe un archivo con ese nombre')
            return

    for destpath, litfile in literalfiles.items():
        litfile.copyto(destpath)

    for destpath, contents in interpolatedfiles.items():
        with open(destpath, 'w') as f:
            f.write(contents)

    for key, targetfile in options.targetfiles.items():
        targetfile.linkto(pathjoin(stagedir, (jobname, packagespec.fileoptions[key])))

    if options.remote.host:

        reloutdir = os.path.relpath(outdir, paths.home)
        remotehome = pathjoin(options.remote.root, (names.user, names.host))
        remotetemp = pathjoin(options.remote.root, (names.user, names.host, 'temp'))
        remoteargs.switches.add('raw')
        remoteargs.switches.add('jobargs')
        remoteargs.switches.add('temporary')
        remoteargs.constants['cwd'] = pathjoin(remotetemp, reloutdir)
        remoteargs.constants['out'] = pathjoin(remotehome, reloutdir)
        for key, value in options.parameterkeys.items():
            remoteargs.constants[key] = interpolate(value, anchor='%', formlist=filtergroups)
        filelist = []
        for key in packagespec.filekeys:
            if os.path.isfile(pathjoin(outdir, (jobname, key))):
                filelist.append(pathjoin(paths.home, '.', reloutdir, (jobname, key)))
        arglist = ['ssh', '-qt', '-S', paths.socket, options.remote.host]
        arglist.extend(env + '=' + val for env, val in environ.items())
        arglist.append('jobsubmit')
        arglist.append(names.package)
        arglist.extend(o(opt) for opt in remoteargs.switches)
        arglist.extend(o(opt, Q(val)) for opt, val in remoteargs.constants.items())
        arglist.extend(o(opt, Q(val)) for opt, lst in remoteargs.lists.items() for val in lst)
        arglist.append(jobname)
        if options.debug.dryrun:
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

    formatdict = FormatDict()
    formatdict.update(names)

    if settings.defaults:
        for key, value in sysconf.defaults.parameterkeys.items():
            try:
                formatdict[key] = interpolate(value, anchor='%', formlist=filtergroups)
            except ValueError:
                messages.error('Hay variables de interpolación inválidas en la opción por defecto', key)
            except IndexError:
                messages.error('Hay variables de interpolación sin definir en la opción por defecto', key)

    for key, value in options.parameterkeys.items():
        try:
            formatdict[key] = interpolate(value, anchor='%', formlist=filtergroups)
        except ValueError:
            messages.error('Hay variables de interpolación inválidas en la opción', key)
        except IndexError:
            messages.error('Hay variables de interpolación sin definir en la opción', key)

    for path in sysconf.parameterpaths:
        componentlist = pathsplit(path.format_map(formatdict))
        trunk = AbsPath(componentlist.pop(0))
        for component in componentlist:
            try:
                trunk.assertdir()
            except OSError as e:
                messages.excinfo(e, trunk)
                raise SystemExit
            if getformatkeys(component):
                messages.error('El componente', component, 'de la ruta', path, 'no es literal')
            trunk = trunk / component
        parameterpaths.append(trunk)

    imports = []
    exports = []

    for key in packagespec.inputfiles:
        if AbsPath(pathjoin(parentdir, (inputname, key))).isfile():
            imports.append(script.importfile(pathjoin(stagedir, (jobname, key)), pathjoin(settings.workdir, packagespec.filekeys[key])))

    for key in options.targetfiles:
        imports.append(script.importfile(pathjoin(stagedir, (jobname, packagespec.fileoptions[key])), pathjoin(settings.workdir, packagespec.filekeys[packagespec.fileoptions[key]])))

    for path in parameterpaths:
        if path.isfile():
            imports.append(script.importfile(path, pathjoin(settings.workdir, path.name)))
        elif path.isdir():
            imports.append(script.importdir(pathjoin(path), settings.workdir))
        else:
            messages.error('La ruta de parámetros', path, 'no existe')

    for key in packagespec.outputfiles:
        exports.append(script.exportfile(pathjoin(settings.workdir, packagespec.filekeys[key]), pathjoin(outdir, (jobname, key))))

    try:
        jobdir.mkdir()
    except FileExistsError:
        messages.failure('No se puede crear la carpeta', jobdir, 'porque ya existe un archivo con ese nombre')
        return

    jobscript = pathjoin(jobdir, 'script')

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash' + '\n')
        f.write(queuespec.jobname.format(jobname) + '\n')
        f.write(''.join(i + '\n' for i in script.header))
        f.write(''.join(i + '\n' for i in script.setup))
        f.write(''.join(script.setenv(i, j) + '\n' for i, j in script.envars))
        f.write(script.setenv('jobname', jobname) + '\n')
        f.write('for host in ${hostlist[*]}; do echo "<$host>"; done' + '\n')
        f.write(script.makedir(settings.workdir) + '\n')
        f.write(''.join(i + '\n' for i in imports))
        f.write(script.chdir(settings.workdir) + '\n')
        f.write(''.join(i + '\n' for i in packagespec.prescript))
        f.write(' '.join(script.main) + '\n')
        f.write(''.join(i + '\n' for i in packagespec.postscript))
        f.write(''.join(i + '\n' for i in exports))
        f.write(script.removedir(settings.workdir) + '\n')
        f.write(''.join(i + '\n' for i in sysconf.offscript))

    if options.debug.dryrun:
        messages.success('Se procesó el trabajo', q(jobname), 'y se generaron los archivos para el envío en', jobdir)
    else:
        try:
            sleep(sysconf.delay + options.common.delay + os.stat(paths.lock).st_mtime - time())
        except (ValueError, FileNotFoundError) as e:
            pass
        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            messages.failure('El gestor de trabajos reportó un error al enviar el trabajo', q(jobname), p(error))
            return
        else:
            messages.success('El trabajo', q(jobname), 'se correrá en', str(options.common.nproc), 'núcleo(s) en', names.cluster, 'con número', jobid)
            with open(pathjoin(jobdir, 'id'), 'w') as f:
                f.write(jobid)
            with open(paths.lock, 'a'):
                os.utime(paths.lock, None)

