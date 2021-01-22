# -*- coding: utf-8 -*-
from os.path import expanduser
from socket import gethostname
from getpass import getuser 
from pwd import getpwnam
from grp import getgrgid
from .specparse import SpecBunch
from .utils import Bunch

class OptBunch(Bunch):
    def __setattr__(self, item, value):
        try:
            self.__setitem__(item, OptBunch(vars(value)))
        except TypeError:
            self.__setitem__(item, value)

class AttrDict(object):
    def __init__(self, init=None):
        if init is not None:
            self.__dict__.update(init)
    def __setattr__(self, item, value):
        try:
            self.__setitem__(item, OptBunch(vars(value)))
        except TypeError:
            self.__setitem__(item, value)
    def __getitem__(self, key):
        return self.__dict__[key]
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    def __delitem__(self, key):
        del self.__dict__[key]
    def __contains__(self, key):
        return key in self.__dict__
    def __len__(self):
        return len(self.__dict__)
    def __repr__(self):
        return repr(self.__dict__)

sysinfo = Bunch()
sysinfo.user = getuser()
sysinfo.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
# Python 3.5+ with pathlib
#sysinfo.home = Path.home()
sysinfo.home = expanduser('~')
sysinfo.hostname = gethostname()

envars = Bunch()
options = AttrDict()
jobspecs = SpecBunch()
argfiles = []

