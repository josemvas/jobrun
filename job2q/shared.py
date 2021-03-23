# -*- coding: utf-8 -*-
import os
from socket import gethostname
from getpass import getuser 
from pwd import getpwnam
from grp import getgrgid
from .readspec import SpecBunch
from .utils import Bunch, removesuffix, q
from .fileutils import AbsPath, buildpath
from .jobutils import readcoords
from .parsing import BoolParser

class NonMatchingFile(Exception):
    pass

class InputFileError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class ArgList:
    def __init__(self, args):
        self.current = None
        if 'sort' in options.common:
            if options.common.sort == 'natural':
                self.args = sort(args, key=natural)
            elif options.common.sort == 'reverse':
                self.args = sort(args, key=natural, reverse=True)
        else:
            self.args = args
    def __iter__(self):
        return self
    def __next__(self):
        try:
            self.current = self.args.pop(0)
        except IndexError:
            raise StopIteration
        if options.common.base:
            basename = self.current
            rootdir = AbsPath(options.common.root)
        else:
            abspath = AbsPath(self.current, cwd=options.common.root)
            #TODO: Move file checking to AbsPath class
            if not abspath.isfile():
                if not abspath.exists():
                    return InputFileError('El archivo de entrada', abspath, 'no existe')
                elif abspath.isdir():
                    return InputFileError('El archivo de entrada', abspath, 'es un directorio')
                else:
                    return InputFileError('El archivo de entrada', abspath, 'no es un archivo regular')
            rootdir = abspath.parent()
            filename = abspath.name
            for key in jobspecs.infiles:
                if filename.endswith('.' + key):
                    basename = removesuffix(filename, '.' + key)
                    break
            else:
                return InputFileError('La extensión del archivo de entrada', q(filename), 'no está asociada a', jobspecs.packagename)
        if 'filter' in options.common:
            if not re.match(options.common.filter, basename):
                return NonMatchingFile()
        #TODO: Check for optional files without linking first
        if 'filecheck' in jobspecs:
            if not BoolParser(jobspecs.filecheck).evaluate(
                {key:AbsPath(buildpath(rootdir, (basename, key))).isfile() or key in options.fileopts for key in jobspecs.filekeys}
            ):
                return InputFileError('El trabajo', q(basename), 'no se envió porque hacen faltan archivos de entrada o hay un conflicto entre ellos')
        return rootdir, basename

class OptDict:
    def __init__(self):
        self.__dict__['switch'] = set()
        self.__dict__['argument'] = dict()
    def __setattr__(self, attr, attrval):
        self.__dict__[attr] = attrval
        if isinstance(attrval, Bunch):
            for key, value in attrval.items():
                if value is True:
                    self.__dict__['switch'].add(key)
                elif value is not False:
                    self.__dict__['argument'].update({key:value})
    def interpolate(self):
        if self.common.interpolate:
            if 'mol' in self.common:
                prefix = []
                for i, path in enumerate(self.common.mol, 1):
                    path = AbsPath(path, cwd=options.common.root)
                    coords = readcoords(path)['coords']
                    self.keywords['mol' + str(i)] = '\n'.join('{0:<2s}  {1:10.4f}  {2:10.4f}  {3:10.4f}'.format(*atom) for atom in coords)
                    prefix.append(path.stem)
                if not 'prefix' in self.common:
                    self.common.prefix = ''.join(prefix)
            elif not 'prefix' in self.common and not 'suffix' in self.common:
                messages.error('Se debe especificar un prefijo o un sufijo para interpolar sin coordenadas')
        elif 'mol' in self.common or self.keywords:
            messages.error('Se especificaron variables de interpolación pero no se va a interpolar nada')

names = Bunch()
names.user = getuser()
names.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
names.host = gethostname()

environ = Bunch()
options = OptDict()
hostspecs = SpecBunch()
jobspecs = SpecBunch()

