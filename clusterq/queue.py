import os
import re
import sys
from subprocess import Popen, PIPE
from .shared import queuespecs

def submitjob(jobscript):
    with open(jobscript, 'r') as fh:
        process = Popen(queuespecs.submitcmd, stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        return re.fullmatch(queuespecs.submitre, output).group(1)
    else:
        raise RuntimeError(error)
        
def getjobstate(jobid):
    process = Popen(queuespecs.statcmd + [jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        status = re.fullmatch(queuespecs.statre, output).group(1)
        if status not in queuespecs.ready_states:
            if status in queuespecs.queued_states:
                return 'El trabajo {name} no se envió porque hay otro trabajo en cola con número {id} que usa la misma carpeta de salida'
            else:
                return 'El trabajo "{name}" no se envió porque está en cola pero su estado es inválido: ' + status
    else:
        for regex in queuespecs.warn_errors:
            if re.fullmatch(regex, error):
                break
        else:
            return 'El trabajo "{name}" no se envió porque ocurrió un error al revisar su estado: ' + error
       
