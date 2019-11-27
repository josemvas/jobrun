# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import sys
import os
from re import search
from subprocess import Popen, PIPE, STDOUT 
from termcolor import colored

#TODO: Catch errors with CalledProcessError
def submit(jobscript):
    with open(jobscript, 'r') as fh:
        stdout = Popen(['bsub'], stdin=fh, stdout=PIPE, stderr=STDOUT, close_fds=True).communicate()[0]
    try: return search('<([0-9]+)>', stdout.decode(sys.stdout.encoding).strip()).group(1)
    except AttributeError as e: sys.exit(colored('El sistema de colas no envió el trabajo porque ocurrió un error: ' + '"{}"'.format(stdout.decode(sys.stdout.encoding).strip()), 'red'))
        
#TODO: Catch errors with CalledProcessError
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
jobname = "#BSUB -J '{}'"
host = "#BSUB -m '{}'"
span = "#BSUB -R 'span[hosts={}]'"
queue = "#BSUB -q '{}'"
ncpu = "#BSUB -n '{}'"
label = "#BSUB -P '{}'"
stdout = "#BSUB -o '{}'"
stderr = "#BSUB -e '{}'"

mpiwrapper = {
    'openmpi' : 'openmpi-mpirun',
    'intelmpi' : 'impi-mpirun',
    'mpich' : 'mpich-mpirun',
}

environment = [
    'ncpu=$(echo $LSB_HOSTS | wc -w)',
    'iplist=$(getent hosts $LSB_HOSTS | cut -d\  -f1 | uniq)',
]

