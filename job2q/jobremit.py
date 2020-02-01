# -*- coding: utf-8 -*-
from os import execv, path
from subprocess import call, DEVNULL
from . import messages
from .utils import pathjoin
from .decorators import catch_keyboard_interrupt
from .jobparse import info, jobspecs, options
from .jobdigest import nextfile

remotefiles = []

class Identity(object):
    def __init__(self, ob):
        self.ob = ob
    def __eq__(self, other):
        return other is self.ob

@catch_keyboard_interrupt
def upload():

    try:
        parentdir, filename, extension = nextfile()
    except AssertionError:
        return

    jobfiles = []
    remotefiles.append(pathjoin('$REMOTESHARE/{user}@{host}'.format(user=info.user, host=info.master), [filename, extension]))
    for key in jobspecs.filekeys:
        if path.isfile(pathjoin(parentdir, (filename, key))):
            jobfiles.append(pathjoin(parentdir, (filename, key)))
    call(['rsync'] + jobfiles + [info.remote + ':' + '$REMOTESHARE/{user}@{host}/'.format(user=info.user, host=info.master)])

@catch_keyboard_interrupt
def remit():
    execv('/usr/bin/ssh', [__file__, '-t', info.remote, 'REMOTECLIENT={user}@{host}'.format(user=info.user, host=info.master), info.alias] + ['--{opt}={val}'.format(opt=opt, val=val) for opt, val in options.items() if Identity(val) not in (None, True, False)] + ['--{opt}'.format(opt=opt) for opt in options if options[opt] is True] + remotefiles)

