# -*- coding: utf-8 -*-
import sys
import os
from re import search
from subprocess import Popen, PIPE, STDOUT 

jobid = '%J'
hosts = "#BSUB -m '{0}'"
queue = "#BSUB -q '{0}'"
ncore = "#BSUB -n '{0}'"
label = "#BSUB -P '{0}'"
stdout = "#BSUB -o '{0}'"
stderr = "#BSUB -e '{0}'"
jobidvar = '$LSB_JOBID'
jobname = "#BSUB -J '{0}'"
singlehost = "#BSUB -R 'span[hosts=1]'"

mpirun = {
    'openmpi' : 'openmpi-mpirun',
    'intelmpi' : 'impi-mpirun',
    'mpich' : 'mpich-mpirun',
}

environment = (
    'ncore=$(echo $LSB_HOSTS | wc -w)',
    'iplist=$(getent hosts $LSB_HOSTS | cut -d\  -f1 | uniq)',
)

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
    output = output.decode('utf-8').strip()
    error = error.decode('utf-8').strip()
    if p.returncode == 0:
        return search(r'<([0-9]+)>', output).group(1)
    else:
        print('El sistema de colas no envió el trabajo porque ocurrió un error: ' + error)
        
def chkjob(jobid):
    p = Popen(('bjobs', '-ostat', '-noheader', jobid), stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = p.communicate()
    output = output.decode('utf-8').strip()
    error = error.decode('utf-8').strip()
    if p.returncode == 0:
        if output in blocking_states:
            return blocking_states[output]
        elif output in ready_states:
            return False
        else:
            return 'El trabajo "{jobname}" no se envió porque su estado no está registrado": ' + output.strip()
    else:
        if error.endswith('is not found'):
            return False
        else:
            return 'El trabajo "{jobname}" no se envió porque ocurrió error al revisar su estado": ' + error
       

