import os
import re
import sys
from subprocess import Popen, PIPE
from .shared import config

def submitjob(jobscript):
    with open(jobscript, 'r') as fh:
        process = Popen(config.sbmtcmd, stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        return re.fullmatch(config.sbmtregex, output).group(1)
    else:
        raise RuntimeError(error)
        
def getjobstate(jobid):
    process = Popen(config.statcmd + [jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        status = re.fullmatch(config.statregex, output).group(1)
        if status not in config.ready_states:
            return 'El trabajo {name} no se envió porque ya hay otro trabajo corriendo con el mismo nombre'
    else:
        for regex in config.warn_errors:
            if re.fullmatch(regex, error):
                break
        else:
            return 'El trabajo "{name}" no se envió porque ocurrió un error al revisar su estado: ' + error
