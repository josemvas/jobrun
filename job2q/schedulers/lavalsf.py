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
        stdout = Popen(['bsub'], stdin=fh, stdout=PIPE, stderr=STDOUT, close_fds=True).communicate()[0]
    try: return search('<([0-9]+)>', stdout.decode(sys.stdout.encoding).strip()).group(1)
    except AttributeError as e:
        raise Exception('El sistema de colas no envió el trabajo porque ocurrió un error: ' + '"{0}"'.format(stdout.decode(sys.stdout.encoding).strip()))
        
def checkjob(jobid):
    stdout = Popen(['bjobs', '-ostat', '-noheader', jobid], stdout=PIPE, stderr=PIPE, close_fds=True).communicate()[0]
    return stdout.decode(sys.stdout.encoding).rstrip()
       

jobstates = {
    'PEND': 'ya está encolado',
    'RUN': 'ya está corriendo',
    'SUSP': 'está detenido',
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

mpiwrapper = {
    'openmpi' : 'openmpi-mpirun',
    'intelmpi' : 'impi-mpirun',
    'mpich' : 'mpich-mpirun',
}

environment = [
    'ncpu=$(echo $LSB_HOSTS | wc -w)',
    'iplist=$(getent hosts $LSB_HOSTS | cut -d\  -f1 | uniq)',
]

