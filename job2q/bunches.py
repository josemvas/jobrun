# -*- coding: utf-8 -*-
from os.path import expanduser
from socket import gethostname
from getpass import getuser 
from .specparse import SpecBunch
from .utils import Bunch

class OptBunch(Bunch):
    def __setattr__(self, item, value):
        try:
            self.__setitem__(item, OptBunch(vars(value)))
        except TypeError:
            self.__setitem__(item, value)

sysinfo = Bunch()
sysinfo.username = getuser()
# Python 3.5+ with pathlib
#sysinfo.userhome = Path.home()
sysinfo.userhome = expanduser('~')
sysinfo.hostname = gethostname()

envars = Bunch()
options = OptBunch()
jobspecs = SpecBunch()
argfiles = []

