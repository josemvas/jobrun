# -*- coding: utf-8 -*-
import os
import re
import sys
from subprocess import Popen, PIPE
from .shared import hostspecs, jobspecs

def jobsubmit(jobscript):
    with open(jobscript, 'r') as fh:
        process = Popen(hostspecs.submitcmd, stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        return re.fullmatch(hostspecs.submitre, output).group(1)
    else:
        raise RuntimeError(error)
        
def jobstat(jobid):
    process = Popen(hostspecs.statcmd + [jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        status = re.fullmatch(hostspecs.statre, output).group(1)
        if status not in hostspecs.ready_states:
            if status in hostspecs.queued_states:
                return hostspecs.queued_states[status]
            else:
                return 'El trabajo "{name}" no se envió porque está en cola pero su estado es inválido: ' + status
    else:
        if error not in [i.format(id=jobid) for i in hostspecs.warn_errors]:
            return 'El trabajo "{name}" no se envió porque ocurrió un error al revisar su estado: ' + error
       
