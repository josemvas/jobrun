# -*- coding: utf-8 -*-
import os
import re
import sys
from subprocess import Popen, PIPE
from .shared import hostspecs, jobspecs

def submitjob(jobscript):
    with open(jobscript, 'r') as fh:
        process = Popen(hostspecs.submitcmd, stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        return re.search(hostspecs.idregex, output).group(1)
    else:
        raise RuntimeError(error)
        
def checkjob(jobid):
    process = Popen(hostspecs.statcmd + [jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        if output not in hostspecs.ready_states:
            if output in hostspecs.queued_states:
                return hostspecs.queued_states[output]
            else:
                return 'El trabajo "{name}" no se envió porque se obtuvo un valor inesperado al revisar su estado: ' + output.strip()
    else:
        if error not in [i.format(id=jobid) for i in hostspecs.warn_errors]:
            return 'El trabajo "{name}" no se envió porque ocurrió un error al revisar su estado: ' + error
       
