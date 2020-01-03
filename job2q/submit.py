# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from errno import ENOENT
from os import path, environ, listdir
from socket import gethostname, gethostbyname
from tempfile import NamedTemporaryFile
from shutil import copyfile
from time import sleep

from job2q import dialogs
from job2q import messages
from job2q.utils import wordjoin, linejoin, pathjoin, remove, makedirs, expandall, loalnum, p, q, qq
from job2q.parsing import parsebool
from job2q.getconf import jobconf, sysconf, optconf
from job2q.spectags import scriptTags, MPILibs
from job2q.decorators import catch_keyboard_interrupt
from job2q.exceptions import * 

@catch_keyboard_interrupt
def wait():
    sleep(optconf.waitime)

@catch_keyboard_interrupt
def submit():

    jobcontrol = []
    jobenviron = {}
    exportfiles = []
    importfiles = []
    redirections = []
    environment = []
    parameters = []
    arguments = []
    
    filepath = path.abspath(inputlist.pop(0))
    basename = path.basename(filepath)
    master = gethostbyname(gethostname())
    
    if not path.exists(filepath):
        messages.failure('El archivo de entrada', filepath, 'no existe')
        return

    filename = None
    if path.isdir(filepath):
        localdir = filepath
        useoutputdir = False
        for item in listdir(filepath):
            for ext in jobconf.inputfiles:
                if item == pathjoin((basename, jobconf.packagekey, ext)):
                    filename = item[:-len(ext)-1]
                    break
        if filename is None:
            messages.failure('Este trabajo no se envió porque el directorio', filepath, 'no contiene archivos de entrada asociados a ', jobconf.packagename)
            return
    else:
        localdir = path.dirname(filepath)
        useoutputdir = jobconf.outputdir
        for ext in jobconf.inputfiles:
            if basename.endswith('.' + ext):
                filename = basename[:-len(ext)-1]
                break
        if filename is None:
            messages.failure('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobconf.packagename)
            return
    
    jobenviron['var'] = environ
    jobenviron['file'] = [ i for i in jobconf.fileexts if path.isfile(pathjoin(localdir, (filename, i))) ]
    
    for script in scriptTags:
        if script in jobconf:
            for line in jobconf[script]:
                for attr in line:
                    if attr in jobenviron:
                        line.boolean = line[attr] in jobenviron[attr]
                    else:
                        messages.cfgerr(q(attr), 'no es un atributo válido de', script)
    
    filebools = { i : True if i in jobenviron['file'] else False for i in jobconf.fileexts }
    
    if 'filecheck' in jobconf:
        if not parsebool(jobconf.filecheck, filebools):
            messages.failure('Falta(n) alguno(s) de los archivos de entrada requeridos')
            return
    
    if 'fileclash' in jobconf:
        if parsebool(jobconf.fileclash, filebools):
            messages.failure('Hay un conflicto entre algunos de los archivos de entrada')
            return
    
    if jobconf.versions:
        if optconf.version is None:
            if 'version' in jobconf.defaults:
                optconf.version = jobconf.defaults.version
            else:
                choices = list(jobconf.versions)
                optconf.version = dialogs.optone('Seleccione una versión', choices=choices)
        try: jobconf.program = jobconf.versions[optconf.version]
        except KeyError as e: messages.opterr('La versión seleccionada', str(e.args[0]), 'es inválida')
        except TypeError: messages.cfgerr('La lista de versiones está mal definida')
        try: executable = jobconf.program.executable
        except AttributeError: messages.cfgerr('No se indicó el ejecutable para la versión', optconf.version)
        executable = expandall(executable) if '/' in executable else executable
    else: messages.cfgerr('<versions> No se especificó ninguna versión del programa')
    
    versionprefix = jobconf.packagekey if 'packagekey' in jobconf else 'v'
    version = versionprefix + loalnum(optconf.version)
    
    #TODO: Is there an easier way to get jobname?
    jobname = filename[:-len(jobconf.packagekey)-1] if 'packagekey' in jobconf and filename.endswith('.' + jobconf.packagekey) else filename
    normalname = pathjoin((jobname, jobconf.packagekey))
    versioname = pathjoin((jobname, version))

    if useoutputdir:
        outputdir = pathjoin(localdir, jobname)
    else:
        outputdir = localdir

    jobdir = pathjoin(outputdir, ('.' + jobname, version))
    
    #TODO: Implement default parameter sets
    for key in jobconf.parameters:
        pardir = expandall(jobconf.parameters[key])
        parset = getattr(optconf, key)
        try: choices = listdir(pardir)
        except FileNotFoundError as e:
            if e.errno == ENOENT:
                messages.cfgerr('El directorio de parámetros', pardir, 'no existe')
        if path.realpath(pardir) == path.realpath(localdir):
            choices = list(set(choices) - set(pathjoin((filename, i)) for i in jobconf.fileexts) - set([jobname]))
        if not choices:
            messages.cfgerr('El directorio de parámetros', pardir, 'está vacío')
        if parset is None:
            if key in jobconf.defaults.parameters:
                parset = jobconf.defaults.parameters[key]
            else:
                parset = dialogs.optone('Seleccione un conjunto de parámetros', p(key), choices=choices)
        if path.exists(path.join(pardir, parset)):
            parameters.append(path.join(pardir, parset))
        else:
            messages.opterr('El directorio de parámetros', path.join(pardir, parset), 'no existe')

    for var in jobconf.filevars:
        environment.append(var + '=' + jobconf.fileexts[jobconf.filevars[var]])
    environment.extend(jobconf.initscript)
    environment.extend(sysconf.environment)
    environment.append("shopt -s nullglob extglob")
    environment.append("workdir=" + pathjoin(optconf.scratch, sysconf.jobidvar))
    environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
    environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
    environment.append("jobram=$(($ncpu*$totalram/$(nproc --all)))")
    environment.append("progname=" + jobconf.packagename)
    environment.append("jobname=" + jobname)
    
    #TODO: Test if parameter directory exists in the filesystem
    
    jobcontrol.append(sysconf.jobname.format(jobname))
    jobcontrol.append(sysconf.label.format(jobconf.packagename))
    jobcontrol.append(sysconf.queue.format(optconf.queue))
    
    if optconf.exechost is not None: 
        jobcontrol.append(sysconf.host.format(optconf.exechost))
    
    if jobconf.storage == 'pooled':
         jobcontrol.append(sysconf.stdout.format(pathjoin(optconf.scratch, (sysconf.jobid, 'out'))))
         jobcontrol.append(sysconf.stderr.format(pathjoin(optconf.scratch, (sysconf.jobid, 'err'))))
    elif jobconf.storage == 'shared':
         jobcontrol.append(sysconf.stdout.format(pathjoin(outputdir, (sysconf.jobid, 'out'))))
         jobcontrol.append(sysconf.stderr.format(pathjoin(outputdir, (sysconf.jobid, 'err'))))
    else:
         messages.cfgerr(jobconf.storage + ' no es un tipo de almacenamiento soportado por este script')
    
    #TODO: MPI support for Slurm
    if jobconf.parallelization.lower() == 'None':
        jobcontrol.append(sysconf.ncpu.format(1))
    elif jobconf.parallelization.lower() == 'openmp':
        jobcontrol.append(sysconf.ncpu.format(optconf.ncpu))
        jobcontrol.append(sysconf.span.format(1))
        environment.append('export OMP_NUM_THREADS=' + str(optconf.ncpu))
    elif jobconf.parallelization.lower() in MPILibs:
        jobcontrol.append(sysconf.ncpu.format(optconf.ncpu))
        if optconf.nodes is not None:
            jobcontrol.append(sysconf.span.format(optconf.nodes))
        if jobconf.mpiwrapper is True:
            executable = sysconf.mpiwrapper[jobconf.parallelization] + ' ' + executable
    else: messages.cfgerr('El tipo de paralelización ' + jobconf.parallelization + ' no es válido')
    
    for ext in jobconf.inputfiles:
        importfiles.append(wordjoin('ssh', master, 'scp', qq(pathjoin(outputdir, (normalname, ext))), \
           '$ip:' + qq(pathjoin('$workdir', jobconf.fileexts[ext]))))
    
    for ext in jobconf.outputfiles:
        exportfiles.append(wordjoin('scp', q(pathjoin('$workdir', jobconf.fileexts[ext])), \
            master + ':' + qq(pathjoin(outputdir, (versioname, ext)))))
    
    for parset in parameters:
        if not path.isabs(parset):
            parset = pathjoin(localdir, parset)
        if path.isdir(parset):
            parset = pathjoin(parset, '.')
        importfiles.append(wordjoin('ssh', master, 'scp -r', qq(parset), '$ip:' + qq('$workdir')))
    
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
    
    if path.isdir(outputdir):
        if path.isdir(jobdir):
            try:
                lastjob = max(listdir(jobdir), key=int)
            except ValueError:
                pass
            else:
                jobstate = sysconf.checkjob(lastjob)
                if jobstate in sysconf.jobstates:
                    messages.failure('El trabajo', q(jobname), 'no se envió porque', sysconf.jobstates[jobstate], '(jobid {0})'.format(lastjob))
                    return
        elif path.exists(jobdir):
            messages.failure('No se puede crear la carpeta', jobdir, 'porque hay un archivo con ese mismo nombre')
            return
        else:
            makedirs(jobdir)
        if not set(listdir(outputdir)).isdisjoint(pathjoin((versioname, ext)) for ext in jobconf.outputfiles):
            if optconf.defaultanswer is None:
                optconf.defaultanswer = dialogs.yesno('Si corre este cálculo los archivos de salida existentes en el directorio', outputdir,'serán sobreescritos, ¿desea continuar de todas formas (si/no)?')
            if optconf.defaultanswer is False:
                messages.failure('El trabajo', q(jobname), 'no se envió por solicitud del usuario')
                return
        for ext in jobconf.outputfiles:
            remove(pathjoin(outputdir, (versioname, ext)))
        if localdir != outputdir:
            for ext in jobconf.inputfiles:
                remove(pathjoin(outputdir, (normalname, ext)))
    elif path.exists(outputdir):
        messages.failure('No se puede crear la carpeta', outputdir, 'porque hay un archivo con ese mismo nombre')
        return
    else:
        makedirs(outputdir)
        makedirs(jobdir)
    
    if localdir != outputdir or filename != normalname:
        for ext in jobconf.inputfiles:
            if path.isfile(pathjoin(localdir, (filename, ext))):
                copyfile(pathjoin(localdir, (filename, ext)), pathjoin(outputdir, (normalname, ext)))
    
    try:
        #TODO: Avoid writing unnecessary newlines or spaces
        t = NamedTemporaryFile(mode='w+t', delete=False)
        t.write(linejoin(i for i in jobcontrol))
        t.write(linejoin(str(i) for i in jobconf.initscript if i))
        t.write(linejoin([i for i in environment]))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + wordjoin('ssh', master, 'ssh $ip mkdir -m 700 "\'$workdir\'"') + '\n')
        t.write(linejoin(' ' * 2 + i for i in importfiles))
        t.write('done' + '\n')
        t.write('cd "$workdir"' + '\n')
        t.write(linejoin(str(i) for i in jobconf.prescript if i))
        t.write(wordjoin(executable, arguments, redirections) + '\n')
        t.write(linejoin(str(i) for i in jobconf.postscript if i))
        t.write(linejoin(i for i in exportfiles))
        t.write('for ip in ${iplist[*]}; do' + '\n')
        t.write(' ' * 2 + 'ssh $ip rm -f "\'$workdir\'/*"' + '\n')
        t.write(' ' * 2 + 'ssh $ip rmdir "\'$workdir\'"' + '\n')
        t.write('done' + '\n')
        t.write(linejoin(wordjoin('ssh', master, q(str(i))) for i in jobconf.offscript if i))
    finally:
        t.close()
    
    try: jobid = sysconf.submit(t.name)
    except RuntimeError as e:
        messages.failure('El sistema de colas rechazó el trabajo', q(jobname), 'con el mensaje', q(e.args[0]))
    else:
        messages.success('El trabajo', q(jobname), 'se correrá en', str(optconf.ncpu), 'núcleo(s) de CPU con el jobid', jobid)
        copyfile(t.name, pathjoin(jobdir, jobid))
        remove(t.name)
    
inputlist = optconf.inputlist

if __name__ == '__main__':
    submit()

