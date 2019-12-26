# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
from socket import gethostname, gethostbyname
from tempfile import NamedTemporaryFile

from job2q.parsing import parsebool
from job2q.utils import strjoin, wordjoin, pathjoin, q, dq, copyfile, remove, makedirs
from job2q.dialogs import messages, dialogs

def queuejob(sysconf, jobconf, options, scheduler, inputfile):

    jobcontrol = [ ]
    exportfiles = [ ]
    importfiles = [ ]
    redirections = [ ]
    environment = [ ]
    arguments = [ ]
    filebool = { }

    for ext in jobconf.inputfiles:
        try: jobconf.fileexts[ext]
        except KeyError: messages.cfgerr('La extensión de archivo de salida', ext, 'no fue definida')

    for ext in jobconf.outputfiles:
        try: jobconf.fileexts[ext]
        except KeyError: messages.cfgerr('La extensión de archivo de salida', ext, 'no fue definida')

    filename = os.path.basename(inputfile)
    master = gethostbyname(gethostname())
    localdir = os.path.abspath(os.path.dirname(inputfile))
    version = ''.join(c for c in options.version if c.isalnum()).lower()
    version = jobconf.versionprefix + version if 'versionprefix' in jobconf else 'v' + version
    versionlist = [ ''.join(c for c in version if c.isalnum()).lower() for version in jobconf.get('versionlist', []) ]
    iosuffix = { ext : version + '.' + ext for ext in jobconf.fileexts }

    for ext in jobconf.inputfiles:
        if filename.endswith('.' + ext):
            basename = filename[:-len('.' + ext)]
            break

    try: basename
    except NameError:
        messages.error('Se esperaba un archivo de entrada de', jobconf.title)
        return

    for ext in jobconf.fileexts:
        filebool[ext] = os.path.isfile(pathjoin(localdir, (basename, ext)))

    if 'filecheck' in jobconf:
        if not parsebool(jobconf.filecheck, filebool):
            messages.error('No existen algunos de los archivos de entrada requeridos')
            return

    if 'fileclash' in jobconf:
        if parsebool(jobconf.fileclash, filebool):
            messages.error('Hay un conflicto entre algunos de los archivos de entrada')
            return

    jobname = basename

    if 'versionprefix' in jobconf:
        if basename.endswith('.' + jobconf.versionprefix):
            jobname = basename[:-len('.' + jobconf.versionprefix)]
        else:
            for key in versionlist:
                if basename.endswith('.' + jobconf.versionprefix + key):
                    jobname = basename[:-len('.' + jobconf.versionprefix + key)]
                    break
    else:
        for key in versionlist:
            if basename.endswith('.v' + key):
                jobname = basename[:-len('.v' + key)]
                break

    if jobconf.outputdir is True:
        outputdir = pathjoin(localdir, jobname)
    else: outputdir = localdir

    for var in jobconf.get('filevars', []):
        environment.append(var + '=' + jobconf.fileexts[jobconf.filevars[var]])

    environment.extend(sysconf.get('init', []))
    environment.extend(scheduler.environment)

    environment.append("shopt -s nullglob extglob")
    environment.append("workdir=" + options.scratch + "/" + scheduler.jobidvar)
    environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    environment.append("jobram=$(($ncpu*$totalram/$(nproc --all)))")

    #TODO: Test if parameter directory exists in the filesystem

    jobcontrol.append(scheduler.jobname.format(jobname))
    jobcontrol.append(scheduler.label.format(jobconf.title))
    jobcontrol.append(scheduler.queue.format(options.queue))

    if options.exechost is not None: 
        jobcontrol.append(scheduler.host.format(options.exechost))

    if sysconf.storage == 'pooled':
         jobcontrol.append(scheduler.stdout.format(pathjoin(options.scratch, (scheduler.jobid, 'out'))))
         jobcontrol.append(scheduler.stderr.format(pathjoin(options.scratch, (scheduler.jobid, 'err'))))
    elif sysconf.storage == 'shared':
         jobcontrol.append(scheduler.stdout.format(pathjoin(outputdir, (scheduler.jobid, 'out'))))
         jobcontrol.append(scheduler.stderr.format(pathjoin(outputdir, (scheduler.jobid, 'err'))))
    else:
         messages.cfgerr(sysconf.storage + ' no es un tipo de almacenamiento soportado por este script')

    jobcommand = jobconf.program.executable

    #TODO: MPI support for Slurm
    if jobconf.runtype == 'serial':
        jobcontrol.append(scheduler.ncpu.format(1))
    elif jobconf.runtype == 'openmp':
        jobcontrol.append(scheduler.ncpu.format(options.ncpu))
        jobcontrol.append(scheduler.span.format(1))
        environment.append('export OMP_NUM_THREADS=' + str(options.ncpu))
    elif jobconf.runtype in ['openmpi','intelmpi','mpich']:
        jobcontrol.append(scheduler.ncpu.format(options.ncpu))
        if options.nodes is not None:
            jobcontrol.append(scheduler.span.format(options.nodes))
        if jobconf.mpiwrapper is True:
            jobcommand = scheduler.mpiwrapper[jobconf.runtype] + ' ' + jobcommand
    else: messages.cfgerr('El tipo de paralelización ' + jobconf.runtype + ' no es válido')

    for ext in jobconf.inputfiles:
        importfiles.append(wordjoin('ssh', master, 'scp', q(q(pathjoin(outputdir, (jobname, iosuffix[ext])))), \
           '$ip:' + q(q(pathjoin('$workdir', jobconf.fileexts[ext])))))

    for ext in jobconf.inputfiles + jobconf.outputfiles:
        exportfiles.append(wordjoin('scp', q(pathjoin('$workdir', jobconf.fileexts[ext])), \
            master + ':' + q(q(pathjoin(outputdir, (jobname, iosuffix[ext]))))))

    for parset in jobconf.parsets:
        if not os.path.isabs(parset):
            parset = pathjoin(localdir, parset)
        if os.path.isdir(parset):
            parset = pathjoin(parset, '.')
        importfiles.append(wordjoin('ssh', master, 'scp -r', q(q(parset)), '$ip:' + q(q('$workdir'))))

    for profile in jobconf.setdefault('profile', []) + jobconf.program.setdefault('profile', []):
        environment.append(profile)

    if 'stdin' in jobconf:
        try: redirections.append('0<' + ' ' + jobconf.fileexts[jobconf.stdin])
        except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stdin + '" en el tag <stdin> no fue definido.')
    if 'stdout' in jobconf:
        try: redirections.append('1>' + ' ' + jobconf.fileexts[jobconf.stdout])
        except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stdout + '" en el tag <stdout> no fue definido.')
    if 'stderr' in jobconf:
        try: redirections.append('2>' + ' ' + jobconf.fileexts[jobconf.stderr])
        except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stderr + '" en el tag <stderr> no fue definido.')

    if 'positionargs' in jobconf:
        for item in jobconf.positionargs:
            for ext in item.split('|'):
                if filebool[ext]:
                    arguments.append(jobconf.fileexts[ext])
                    break

    if 'optionargs' in jobconf:
        for opt in jobconf.optionargs:
            ext = jobconf.optionargs[opt]
            arguments.append('-' + opt + ' ' + jobconf.fileexts[ext])

    jobdir = pathjoin(outputdir, ['', jobname, version])

    try: os.mkdir(jobdir)
    except OSError:
        if os.path.isdir(outputdir):
            if os.path.isdir(jobdir):
                try:
                    lastjob = max(os.listdir(jobdir), key=int)
                except ValueError:
                    pass
                else:
                    jobstate = scheduler.checkjob(lastjob)
                    if jobstate in scheduler.jobstates:
                        messages.error('El trabajo', q(jobname), 'no se envió porque', scheduler.jobstates[jobstate], '(jobid {0})'.format(lastjob))
                        return
            elif os.path.exists(jobdir):
                remove(jobdir)
                makedirs(jobdir)
            if not set(os.listdir(outputdir)).isdisjoint(pathjoin((jobname, iosuffix[ext])) for ext in jobconf.outputfiles):
                if options.defaultanswer is None:
                    options.defaultanswer = dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas (si/no)?')
                if options.defaultanswer is False:
                    messages.error('El trabajo', q(jobname), 'no se envió por solicitud del usuario')
                    return
            for ext in jobconf.inputfiles + jobconf.outputfiles:
                remove(pathjoin(outputdir, (jobname, iosuffix[ext])))
        elif os.path.exists(outputdir):
            messages.error('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(outputdir)
            makedirs(jobdir)

    try:
        #TODO: Avoid writing unnecessary newlines or spaces
        t = NamedTemporaryFile(mode='w+t', delete=False)
        t.write(strjoin(i + '\n' for i in jobcontrol))
        t.write(strjoin(i + '\n' for i in environment))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + wordjoin('ssh', master, 'ssh $ip mkdir -m 700', q(q('$workdir'))) + '\n')
        t.write(strjoin(' ' * 2 + i + '\n' for i in importfiles))
        t.write('done' + '\n')
        t.write('cd "$workdir"' + '\n')
        t.write(strjoin(i.repr + '\n' for i in jobconf.prescript if 'iff' not in i or filebool[i.iff]))
        t.write(wordjoin(jobcommand, arguments, redirections) + '\n')
        t.write(strjoin(i + '\n' for i in exportfiles))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + 'ssh $ip rm -f "\'$workdir\'/*"' + '\n')
        t.write(' ' * 2 + 'ssh $ip rmdir "\'$workdir\'"' + '\n')
        t.write('done' + '\n')
        if 'offscript' in sysconf:
            for command in sysconf.offscript:
                if command.ifv in os.environ:
                    t.write(wordjoin('ssh', master, dq(command.repr.format(jobname=jobname, packagename=jobconf.title))) + '\n')
    finally:
        t.close()

    for ext in jobconf.inputfiles:
        if os.path.isfile(pathjoin(localdir, (basename, ext))):
            copyfile(pathjoin(localdir, (basename, ext)), pathjoin(outputdir, (jobname, iosuffix[ext])))

    try: jobid = scheduler.submit(t.name)
    except RuntimeError as e:
        messages.error('El sistema de colas rechazó el trabajo', q(jobname), 'con el mensaje', q(e.args[0]))
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(options.ncpu), 'núcleo(s) de CPU con el jobid', jobid)
        copyfile(t.name, pathjoin(jobdir, jobid))
        remove(t.name)

