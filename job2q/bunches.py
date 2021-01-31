# -*- coding: utf-8 -*-
from os.path import expanduser
from socket import gethostname
from getpass import getuser 
from pwd import getpwnam
from grp import getgrgid
from .specparse import SpecBunch
from .utils import Bunch
from .fileutils import AbsPath
from .chemistry import readxyz, readmol
from os import getcwd

class AttrDict(object):
    def __init__(self):
        self.__dict__['boolean'] = set()
        self.__dict__['constant'] = dict()
    def __setattr__(self, attr, attrval):
        self.__dict__[attr] = attrval
        if isinstance(attrval, Bunch):
            for key, value in attrval.items():
                if value is True:
                    self.__dict__['boolean'].add(key)
                elif value is not False:
                    self.__dict__['constant'].update({key:value})
    def appendto(self, extlist, item):
        if item in self.__dict__:
            if isinstance(item, (list, tuple)):
                extlist.extend(self.__dict__[item])
            else:
                extlist.append(self.__dict__[item])

class Interpolation():
    def __init__(self, options):
        if options.common.interpolate:
            self.molfile = getattr(self.common, 'molfile', None)
            self.prefix = self.common.prefix
            self.interpolate()
        elif 'molfile' in self.common or self.keywords:
            messages.error('Se especificaron variables o coordenadas de interpolación pero no se especificó la opción -i|--interpolate')
        else:
            self.interpolation = None
    def interpolate(self):
        if self.molfile:
            self.parsemol()
            self.prefix.append(self.molfile.stem)
        elif not self.prefix:
            messages.error('Para interpolar debe especificar un archivo de coordenadas o un prefijo de trabajo')
    def parsemol(self):
        molfile = AbsPath(self.molfile, cwdir=getcwd())
        molformat = '{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format
        if molfile.isfile():
            if molfile.hasext('.xyz'):
                for i, step in enumerate(readxyz(molfile), 1):
                    self['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
            elif molfile.hasext('.mol'):
                for i, step in enumerate(readmol(molfile), 1):
                    self['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
            else:
                messages.error('Solamente están soportados archivos de coordenadas en formato XYZ o MOL')
        elif molfile.isdir():
            messages.error('El archivo de coordenadas', molfile, 'es un directorio')
        elif molfile.exists():
            messages.error('El archivo de coordenadas', molfile, 'no es un archivo regular')
        else:
            messages.error('El archivo de coordenadas', molfile, 'no existe')
        self.molfile = molfile


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
options.fileargs = []

