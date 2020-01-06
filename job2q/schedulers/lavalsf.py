# -*- coding: utf-8 -*-
#TODO: Catch errors with CalledProcessError

from __future__ import unicode_literals
from __future__ import print_function

import sys
import os
from re import search
from subprocess import Popen, PIPE, STDOUT 

def submit(jobscript):
    with open(jobscript, 'r') as fh:
        p = Popen(['bsub'], stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = p.communicate()
    if p.returncode == 0:
        return search('<([0-9]+)>', output.decode(sys.stdout.encoding).strip()).group(1)
    else:
        raise Exception('El sistema de colas no envió el trabajo porque ocurrió un error: "{0}"'.format(error.decode(sys.stdout.encoding).strip()))
        
def checkjob(jobid):
    p = Popen(['bjobs', '-ostat', '-noheader', jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = p.communicate()
    if p.returncode == 0:
        return output.decode(sys.stdout.encoding).strip()
    else:
        print('Ocurrión un error al revisar el estado del trabajo: "{0}"'.format(error.decode(sys.stdout.encoding).strip()))
        return 'UNKNOWN'
       

jobstates = {
    'UNKNOWN': 'El trabajo {jobname} no se envió porque no se sabe si ya está corriendo', 
    'PEND': 'El trabajo {jobname} no se envió porque ya está encolado con jobid {jobid}',
    'RUN': 'El trabajo {jobname} no se envió porque ya está corriendo con jobid {jobid}',
    'SUSP': 'El trabajo {jobname} no se envió porque está detenido con jobid {jobid}',
}

jobid = '%J'
jobidvar = '$LSB_JOBID'
jobname = "#BSUB -J '{0}'"
host = "#BSUB -m '{0}'"
span = "#BSUB -R 'span[hosts={0}]'"
queue = "#BSUB -q '{0}'"
ncpu = "#BSUB -n '{0}'"
label = "#BSUB -P '{0}'"
stdout = "#BSUB -o '{0}'"
stderr = "#BSUB -e '{0}'"

mpirun = {
    'openmpi' : 'openmpi-mpirun',
    'intelmpi' : 'impi-mpirun',
    'mpich' : 'mpich-mpirun',
}

environment = [
    'ncpu=$(echo $LSB_HOSTS | wc -w)',
    'iplist=$(getent hosts $LSB_HOSTS | cut -d\  -f1 | uniq)',
]

