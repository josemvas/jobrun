# -*- coding: utf-8 -*-
import sys
import os
from re import search
from subprocess import Popen, PIPE

jobformat = {
    'jobname' : '#SBATCH -J "{}"'.format,
    'label' : '#SBATCH --comment="{}"'.format,
    'hosts' : '#SBATCH -w "{}"'.format,
    'ncore' : '#SBATCH -n "{}"'.format,
    'nhost' : '#SBATCH -N "{}"'.format,
    'queue' : '#SBATCH -p "{}"'.format,
    'stdoutput' : '#SBATCH -o "{}/%A.out"'.format,
    'stderr' : '#SBATCH -e "{}/%A.err"'.format,
}

jobenvars = {
    'jobid' : '$SLURM_JOB_ID',
    'ncore' : '$SLURM_NTASKS',
    'hosts' : '$(getent hosts $SLURM_JOB_NODELIST | cut -d\  -f1 | uniq)',
}

mpilauncher = {
    'openmpi' : 'mpirun',
    'intelmpi' : 'mpirun',
    'mpich' : 'mpirun',
}

blocking_states = {
    'PENDING': 'El trabajo "{jobname}" no se envió porque ya está en cola con jobid {jobid}',
    'RUNNING': 'El trabajo "{jobname}" no se envió porque ya está corriendo con jobid {jobid}',
    'SUSPENDED': 'El trabajo "{jobname}" no se envió porque está suspendido con jobid {jobid}',
    'STOPPED': 'El trabajo "{jobname}" no se envió porque está detenido con jobid {jobid}',
    'CONFIGURING': 'El trabajo "{jobname}" no se envió porque está a punto de iniciar con jobid {jobid}',
    'COMPLETING': 'El trabajo "{jobname}" no se envió porque está a punto de terminar con jobid {jobid}',
    'SIGNALING': 'El trabajo "{jobname}" no se envió porque se está cancelando con jobid {jobid}',
    'RESV_DEL_HOLD': 'El trabajo "{jobname}" no se envió porque está detenido en cola con jobid {jobid}',
    'REQUEUE_HOLD': 'El trabajo "{jobname}" no se envió porque ya está en cola con jobid {jobid}',
    'REQUEUED': 'El trabajo "{jobname}" no se envió porque ya está en cola con jobid {jobid}',
}

ready_states = (
    'COMPLETED',
    'CANCELLED',
    'PREEMPTED',
    'DEADLINE',
    'TIMEOUT',
    'FAILED',
    'BOOT_FAIL',
    'NODE_FAIL',
    'OUT_OF_MEMORY',
)

def queuejob(jobscript):
    with open(jobscript, 'r') as fh:
        p = Popen(['sbatch'], stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = p.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if p.returncode == 0:
        return search(r' ([0-9]+)$', output).group(1)
    else:
        print('El sistema de colas no envió el trabajo porque ocurrió un error:\n' + error)
        
def checkjob(jobid):
    p = Popen(['squeue', '--noheader', '-o%T', '-j', jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = p.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if p.returncode == 0:
        if output in blocking_states:
            return blocking_states[output].format
        elif output in ready_states:
            return None
        else:
            return 'El trabajo "{jobname}" no se envió porque su estado no está registrado": ' + output.strip()
    else:
        return 'El trabajo "{jobname}" no se envió porque ocurrió error al revisar su estado": ' + error
       
