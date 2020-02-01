# -*- coding: utf-8 -*-
from os import execv, path
from subprocess import run, DEVNULL
from . import messages
from .utils import pathjoin
from .config import jobconf, options, nextfile, alias, username, master, remote
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
    run(['scp'] + jobfiles + [remote + ':' + '$REMOTEJOBS/{user}@{host}'.format(user=username, host=master)], stdout=DEVNULL)

@catch_keyboard_interrupt
def transmit():
    execv('ssh', [__file__, '-t', remote, 'REMOTECLIENT={user}@{host}'.format(user=username, host=master), alias] + ['--{opt}={val}'.format(opt=opt, val=options[opt]) for opt in options] + remotefiles)

