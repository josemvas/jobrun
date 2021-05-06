# -*- coding: utf-8 -*-
import os
import re
import sys
from subprocess import Popen, PIPE
from .shared import clusterspecs, jobspecs

def jobsubmit(jobscript):
    with open(jobscript, 'r') as fh:
        process = Popen(clusterspecs.submitcmd, stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        return re.fullmatch(clusterspecs.submitre, output).group(1)
    else:
        raise RuntimeError(error)
        
def jobstat(jobid):
    process = Popen(clusterspecs.statcmd + [jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        status = re.fullmatch(clusterspecs.statre, output).group(1)
        if status not in clusterspecs.ready_states:
            if status in clusterspecs.queued_states:
                return clusterspecs.queued_states[status]
            else:
                return 'El trabajo "{name}" no se envió porque está en cola pero su estado es inválido: ' + status
    else:
        for regex in clusterspecs.warn_errors:
            if re.fullmatch(regex, error):
                break
        else:
            return 'El trabajo "{name}" no se envió porque ocurrió un error al revisar su estado: ' + error
       
