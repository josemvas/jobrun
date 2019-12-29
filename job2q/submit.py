# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
from socket import gethostname, gethostbyname
from tempfile import NamedTemporaryFile

from job2q.parsing import parsebool
from job2q.dialogs import messages, dialogs
from job2q.utils import wordjoin, linejoin, pathjoin, q, dq, copyfile, remove, makedirs
from strings import scriptTags
#from job2q.config import sysconf, queueconf, jobconf, userconf

def queuejob(sysconf, jobconf, userconf, queueconf, inputfile):
    jobcontrol = [ ]
    exportfiles = [ ]
    importfiles = [ ]
    redirections = [ ]
    environment = [ ]
    arguments = [ ]
    
    for ext in jobconf.inputfiles:
        try: jobconf.fileexts[ext]
        except KeyError: messages.cfgerr('La extensión de archivo de salida', ext, 'no fue definida')
    
    for ext in jobconf.outputfiles:
        try: jobconf.fileexts[ext]
        except KeyError: messages.cfgerr('La extensión de archivo de salida', ext, 'no fue definida')
    
    filename = os.path.basename(inputfile)
    master = gethostbyname(gethostname())
    localdir = os.path.abspath(os.path.dirname(inputfile))
    version = ''.join(c for c in userconf.version if c.isalnum()).lower()
    version = jobconf.versionprefix + version if 'versionprefix' in jobconf else 'v' + version
    versions = (''.join(c for c in version if c.isalnum()).lower() for version in jobconf.versions)
    iosuffix = { ext : version + '.' + ext for ext in jobconf.fileexts }
    
    for ext in jobconf.inputfiles:
        if filename.endswith('.' + ext):
            basename = filename[:-len('.' + ext)]
            break
    
    try: basename
    except NameError:
        messages.error('Se esperaba un archivo de entrada de', jobconf.title)
        return
    
    jobenviron['var'] = os.environ
    jobenviron['file'] = (i for i in jobconf.fileexts if os.path.isfile(pathjoin(localdir, (basename, i))))

    for script in scriptTags:
        for line in jobconf[script]:
            for attr in line:
                if attr in jobenviron:
                    item.testres = line[attr] in jobenviron[attr]
                else messages.cfgerr(attr, 'no es un atributo válido de', script)

    filebools = (True if i in jobenviron['file'] else False for i in jobconf.fileexts)

    if 'filecheck' in jobconf:
        if not parsebool(jobconf.filecheck, filebools):
            messages.error('No existen algunos de los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobconf:
        if parsebool(jobconf.fileclash, filebools):
            messages.error('Hay un conflicto entre algunos de los archivos de entrada')
            return
    
    #TODO: Get jobname in a better way
    jobname = basename
    
    if 'versionprefix' in jobconf:
        if basename.endswith('.' + jobconf.versionprefix):
            jobname = basename[:-len('.' + jobconf.versionprefix)]
        else:
            for key in versions:
                if basename.endswith('.' + jobconf.versionprefix + key):
                    jobname = basename[:-len('.' + jobconf.versionprefix + key)]
                    break
    else:
        for key in versions:
            if basename.endswith('.v' + key):
                jobname = basename[:-len('.v' + key)]
                break
    
    if jobconf.outputdir is True:
        outputdir = pathjoin(localdir, jobname)
    else: outputdir = localdir
    
    for var in jobconf.filevars:
        environment.append(var + '=' + jobconf.fileexts[jobconf.filevars[var]])
    
    environment.extend(sysconf.initscript)
    environment.extend(queueconf.environment)
    environment.append("shopt -s nullglob extglob")
    environment.append("workdir=" + pathjoin(userconf.scratch, queueconf.jobidvar))
    environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    environment.append("jobram=$(($ncpu*$totalram/$(nproc --all)))")
    environment.append("progname=" + jobconf.title)
    environment.append("jobname=" + jobname)
    
    #TODO: Test if parameter directory exists in the filesystem
    
    jobcontrol.append(queueconf.jobname.format(jobname))
    jobcontrol.append(queueconf.label.format(jobconf.title))
    jobcontrol.append(queueconf.queue.format(userconf.queue))
    
    if userconf.exechost is not None: 
        jobcontrol.append(queueconf.host.format(userconf.exechost))
    
    if sysconf.storage == 'pooled':
         jobcontrol.append(queueconf.stdout.format(pathjoin(userconf.scratch, (queueconf.jobid, 'out'))))
         jobcontrol.append(queueconf.stderr.format(pathjoin(userconf.scratch, (queueconf.jobid, 'err'))))
    elif sysconf.storage == 'shared':
         jobcontrol.append(queueconf.stdout.format(pathjoin(outputdir, (queueconf.jobid, 'out'))))
         jobcontrol.append(queueconf.stderr.format(pathjoin(outputdir, (queueconf.jobid, 'err'))))
    else:
         messages.cfgerr(sysconf.storage + ' no es un tipo de almacenamiento soportado por este script')
    
    jobcommand = jobconf.program.executable
    
    #TODO: MPI support for Slurm
    if jobconf.runtype == 'serial':
        jobcontrol.append(queueconf.ncpu.format(1))
    elif jobconf.runtype == 'openmp':
        jobcontrol.append(queueconf.ncpu.format(userconf.ncpu))
        jobcontrol.append(queueconf.span.format(1))
        environment.append('export OMP_NUM_THREADS=' + str(userconf.ncpu))
    elif jobconf.runtype in ['openmpi','intelmpi','mpich']:
        jobcontrol.append(queueconf.ncpu.format(userconf.ncpu))
        if userconf.nodes is not None:
            jobcontrol.append(queueconf.span.format(userconf.nodes))
        if jobconf.mpiwrapper is True:
            jobcommand = queueconf.mpiwrapper[jobconf.runtype] + ' ' + jobcommand
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
                if ext in jobenviron['file']:
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
                    jobstate = queueconf.checkjob(lastjob)
                    if jobstate in queueconf.jobstates:
                        messages.error('El trabajo', q(jobname), 'no se envió porque', queueconf.jobstates[jobstate], '(jobid {0})'.format(lastjob))
                        return
            elif os.path.exists(jobdir):
                remove(jobdir)
                makedirs(jobdir)
            if not set(os.listdir(outputdir)).isdisjoint(pathjoin((jobname, iosuffix[ext])) for ext in jobconf.outputfiles):
                if userconf.defaultanswer is None:
                    userconf.defaultanswer = dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas (si/no)?')
                if userconf.defaultanswer is False:
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
        t.write(linejoin(i for i in jobcontrol))
        t.write(linejoin(str(i) for i in sysconf.initscript if i))
        t.write(linejoin(i for i in environment))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + wordjoin('ssh', master, 'ssh $ip mkdir -m 700 "\'$workdir\'"') + '\n')
        t.write(linejoin(' ' * 2 + i for i in importfiles))
        t.write('done' + '\n')
        t.write('cd "$workdir"' + '\n')
        t.write(linejoin(str(i) for i in jobconf.prescript if i))
        t.write(wordjoin(jobcommand, arguments, redirections) + '\n')
        t.write(linejoin(str(i) for i in jobconf.postscript if i))
        t.write(linejoin(i for i in exportfiles))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + 'ssh $ip rm -f "\'$workdir\'/*"' + '\n')
        t.write(' ' * 2 + 'ssh $ip rmdir "\'$workdir\'"' + '\n')
        t.write('done' + '\n')
        t.write(linejoin(wordjoin('ssh', master, dq(str(i))) for i in sysconf.offscript if i))
    finally:
        t.close()
    
    for ext in jobconf.inputfiles:
        if os.path.isfile(pathjoin(localdir, (basename, ext))):
            copyfile(pathjoin(localdir, (basename, ext)), pathjoin(outputdir, (jobname, iosuffix[ext])))
    
    try: jobid = queueconf.submit(t.name)
    except RuntimeError as e:
        messages.error('El sistema de colas rechazó el trabajo', q(jobname), 'con el mensaje', q(e.args[0]))
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(userconf.ncpu), 'núcleo(s) de CPU con el jobid', jobid)
        copyfile(t.name, pathjoin(jobdir, jobid))
        remove(t.name)
    
