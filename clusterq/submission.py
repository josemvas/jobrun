import os, sys, time
#from tkdialogs import messages, prompts
from clinterface import messages, prompts, _
from subprocess import CalledProcessError, call, check_output
from .queue import submitjob, getjobstatus
from .shared import ArgGroups, names, paths, config, options, environ, settings, status, script, parameterdict, interpolationdict, parameterpaths
from .utils import ConfigTemplate, FilterGroupTemplate, InterpolationTemplate, option
from .initialization import initialize
from .fileutils import AbsPath

selector = prompts.Selector()
completer = prompts.Completer()
completer.set_truthy_options(['si', 'yes'])
completer.set_falsy_options(['no'])

def submit(workdir, inputname, filtergroups):

    if not status.initialized:
        initialize()

    if 'prefix' in settings:
        jobname = f'{settings.prefix}.{inputname}'
    elif 'suffix' in settings:
        jobname = f'{inputname}.{settings.suffix}'
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
            srcpath = workdir/inputname*key
            destpath = stagedir/jobname*key
            if srcpath.isfile():
                if 'interpolable' in config and key in config.interpolable:
                    with open(srcpath, 'r') as f:
                        contents = f.read()
                        if options.interpolate:
                            try:
                                interpolatedfiles[destpath] = InterpolationTemplate(contents).substitute(interpolationdict)
                            except ValueError:
                                messages.failure(_('El archivo $file contiene variables de interpolación inválidas', file=srcpath), f'key={e.args[0]}')
                                return
                            except KeyError as e:
                                messages.failure(_('El archivo $file contiene variables de interpolación indefinidas', file=srcpath), f'key={e.args[0]}')
                                return
                        else:
                            try:
                                interpolatedfiles[destpath] = InterpolationTemplate(contents).substitute({})
                            except ValueError:
                                pass
                            except KeyError as e:
                                completer.set_message(_('Parece que hay variables de interpolación en el archivo $file ¿desea continuar sin interpolar?', file=srcpath))
                                if completer.binary_choice():
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
                    messages.failure(InterpolationTemplate(jobstatus).substitute(name=jobname, path=outdir))
                    return
            except FileNotFoundError:
                pass
        if not set(outdir.listdir()).isdisjoint(f'{jobname}.{key}' for key in config.outputfiles):
            completer.set_message(_('Si corre este cálculo los archivos de salida existentes en el directorio $outdir serán sobreescritos, ¿desea continuar de todas formas?', outdir=outdir))
            if options.common.no or (not options.common.yes and not completer.binary_choice()):
                messages.failure(_('Cancelado por el usuario'))
                return
        if workdir != outdir:
            for ext in config.inputfiles:
                (outdir/jobname*ext).remove()
        for ext in config.outputfiles:
            (outdir/jobname*ext).remove()
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
        targetfile.symlink(stagedir/jobname*config.fileopts[key])

    ############ Remote execution ###########

    if options.remote.host:
        remote_args = ArgGroups()
        reloutdir = os.path.relpath(outdir, paths.home)
        remote_tmpdir = paths.remotedir/names.user*names.host/'tmp'
        remote_outdir = paths.remotedir/names.user*names.host/'out'
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
            if (outdir/jobname*key).isfile():
                filelist.append(paths.home/'.'/reloutdir/jobname*key)
        arglist = ['ssh', '-qt', '-S', paths.socket, options.remote.host]
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
                check_output(['ssh', '-S', paths.socket, options.remote.host, f"mkdir -p '{remote_tmpdir}' '{remote_outdir}'"])
                check_output([f'rsync', '-e', "ssh -S '{paths.socket}'", '-qRLtz'] + filelist + [f'{options.remote.host}:{remote_tmpdir}'])
                check_output([f'rsync', '-e', "ssh -S '{paths.socket}'", '-qRLtz', '-f', '-! */'] + filelist + [f'{options.remote.host}:{remote_outdir}'])
            except CalledProcessError as e:
                messages.error(_('Error al copiar los archivos al servidor $host', host=options.remote.host), e.output.decode(sys.stdout.encoding).strip())
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
        trunk = AbsPath()
        for part in AbsPath(path).parts:
            trunk.assertdir()
            trunk = trunk/part
        parameterpaths.append(trunk)

    imports = []
    exports = []

    for key in config.inputfiles:
        if (workdir/inputname*key).isfile():
            imports.append(script.importfile(stagedir/jobname*key, settings.execdir/config.filekeys[key]))

    for key in options.targetfiles:
        imports.append(script.importfile(stagedir/jobname*config.fileopts[key], settings.execdir/config.filekeys[config.fileopts[key]]))

    for path in parameterpaths:
        if path.isfile():
            imports.append(script.importfile(path, settings.execdir/path.name))
        elif path.isdir():
            imports.append(script.importdir(path, settings.execdir))
        else:
            messages.error(_('La ruta de parámetros $path no existe', path=path))

    for key in config.outputfiles:
        exports.append(script.exportfile(settings.execdir/config.filekeys[key], outdir/jobname*key))

    try:
        jobdir.mkdir()
    except FileExistsError:
        messages.failure(_('No se puede crear la carpeta $jobdir porque ya existe un archivo con ese nombre', jobdir=jobdir))
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
        messages.success(_('Se procesó el trabajo "$jobname" y se generaron los archivos para el envío en el directorio $jobdir', jobname=jobname, jobdir=jobdir))
    else:
        try:
            time.sleep(options.local.delay + os.stat(paths.lock).st_mtime - time.time())
        except (ValueError, FileNotFoundError) as e:
            pass
        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            messages.failure(_('El gestor de trabajos reportó el siguiente error al enviar el trabajo $jobname: $error', jobname=jobname, error=error))
            return
        else:
            messages.success(_('El trabajo "$jobname" se correrá en $nproc núcleo(s) en $clustername con el número $jobid', jobname=jobname, nproc=options.common.nproc, clustername=names.cluster, jobid=jobid))
            with open(jobdir/'id', 'w') as f:
                f.write(jobid)
            with open(paths.lock, 'a'):
                os.utime(paths.lock, None)
