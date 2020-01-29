# -*- coding: utf-8 -*-
import sys
import os
from re import search
from subprocess import Popen, PIPE, STDOUT 

jobid = '%J'
jobname = '#BSUB -J "{0}"'.format
hosts = '#BSUB -m "{0}"'.format
ncore = '#BSUB -n "{0}"'.format
nhost = '#BSUB -R "span[hosts={0}]"'.format
queue = '#BSUB -q "{0}"'.format
stdout = '#BSUB -o "{0}"'.format
stderr = '#BSUB -e "{0}"'.format
label = '#BSUB -P "{0}"'.format

jobvars = {
    'jobid' : '$LSB_JOBID',
    'ncore' : '$(echo $LSB_HOSTS | wc -w)',
    'hosts' : '$(getent hosts $LSB_HOSTS | cut -d\  -f1 | uniq)',
}

mpilauncher = {
    'openmpi' : 'mpirun',
    'intelmpi' : 'mpirun',
    'mpich' : 'mpirun',
}

blocking_states = {
    'PEND': 'El trabajo "{jobname}" no se envió porque ya está encolado con jobid {jobid}',
    'RUN': 'El trabajo "{jobname}" no se envió porque ya está corriendo con jobid {jobid}',
    'PSUSP': 'El trabajo "{jobname}" no se envió porque está suspendido con jobid {jobid}',
    'USUSP': 'El trabajo "{jobname}" no se envió porque está suspendido con jobid {jobid}',
    'SSUSP': 'El trabajo "{jobname}" no se envió porque está suspendido con jobid {jobid}',
}

ready_states = (
    'DONE',
    'EXIT',
)

def submit(jobscript):
    with open(jobscript, 'r') as fh:
        p = Popen(('bsub'), stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = p.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if p.returncode == 0:
        return search(r'<([0-9]+)>', output).group(1)
    else:
        print('El sistema de colas no envió el trabajo porque ocurrió un error: ' + error)
        
def chkjob(jobid):
    p = Popen(('bjobs', '-ostat', '-noheader', jobid), stdout=PIPE, stderr=PIPE, close_fds=True)
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
        if error.endswith('is not found'):
            return None
        else:
            return 'El trabajo "{jobname}" no se envió porque ocurrió error al revisar su estado": ' + error
       
