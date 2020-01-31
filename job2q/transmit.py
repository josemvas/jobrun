# -*- coding: utf-8 -*-
from os import execl, path
from getpass import getuser 
from subprocess import run, DEVNULL
from . import messages
from .utils import pathjoin
from .jobutils import details, jobconf, options, nextfile
from .decorators import catch_keyboard_interrupt

remotefiles = []

@catch_keyboard_interrupt
def upload():

    try:
        parentdir, filename, extension = nextfile()
    except AssertionError:
        return

    jobfiles = []
    remotefiles.append(pathjoin(filename, extension))
    for key in jobconf.filekeys:
        if path.isfile(pathjoin(parentdir, (filename, key))):
            jobfiles.append(pathjoin(parentdir, (filename, key)))
    run(['scp', *jobfiles, details.remotehost + ':' + '$REMOTEJOBS/{user}@{host}'.format(user=getuser(), host=details.clienthost)], stdout=DEVNULL)

@catch_keyboard_interrupt
def transmit():
    execl('ssh', __file__, '-t', details.remotehost, 'JOBCLIENT={user}@{host}'.format(user=getuser(), host=details.clienthost), details.alias, *('--{option}={value}'.format(option=option, value=options[option]) for option in options), *remotefiles)

