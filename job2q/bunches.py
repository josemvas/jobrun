# -*- coding: utf-8 -*-
from os.path import expanduser
from socket import gethostname
from getpass import getuser 
from pwd import getpwnam
from grp import getgrgid
from argparse import Namespace
from .specparse import SpecBunch
from .utils import Bunch
from .fileutils import AbsPath
from .chemistry import readxyz, readmol
from os import getcwd

class AttrDict(object):
    def __init__(self, init=None):
        if init is not None:
            self.__dict__.update(init)
        self.collection = {}
    def __setattr__(self, item, value):
        if isinstance(value, Namespace):
            self.__dict__[item] = Bunch(vars(value))
            self.__dict__['collection'].update(vars(value))
        else:
            self.__dict__[item] = value
    def __getattr__(self, item):
        return self.__dict__[item]
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
    def appendto(self, extlist, item):
        if item in self.__dict__:
            if isinstance(item, (list, tuple)):
                extlist.extend(self.__dict__[item])
            else:
                extlist.append(self.__dict__[item])
    def interpolation(self):
        if self.common.interpolate:
            if 'molfile' in self.common:
                self.parsemol()
                self.common.prefix.append(self.keywords.molfile.stem)
            elif 'suffix' not in self.common:
                messages.error('Para interpolar debe especificar un archivo de coordenadas o un sufijo de trabajo')
        elif 'molfile' in self.common or self.keywords:
            messages.error('Se especificaron coordenadas o variables de interpolación pero no se va a interpolar nada')
    def parsemol(self):
        molfile = AbsPath(self.common.molfile, cwdir=getcwd())
        molformat = '{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format
        if molfile.isfile():
            if molfile.hasext('.xyz'):
                for i, step in enumerate(readxyz(molfile), 1):
                    self.keywords['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
            elif molfile.hasext('.mol'):
                for i, step in enumerate(readmol(molfile), 1):
                    self.keywords['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
            else:
                messages.error('Solamente están soportados archivos de coordenadas en formato XYZ o MOL')
        elif molfile.isdir():
            messages.error('El archivo de coordenadas', molfile, 'es un directorio')
        elif molfile.exists():
            messages.error('El archivo de coordenadas', molfile, 'no es un archivo regular')
        else:
            messages.error('El archivo de coordenadas', molfile, 'no existe')
        self.keywords.molfile = molfile



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

