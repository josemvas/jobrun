# -*- coding: utf-8 -*-
from os import getcwd
from os.path import expanduser
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
        if options.common.sort:
            self.args = sort(args, key=natural)
        elif options.common.sort_reverse:
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
            parentdir = AbsPath(options.common.cwd)
        else:
            abspath = AbsPath(self.current, cwd=options.common.cwd)
            #TODO: Move file checking to AbsPath class
            if not abspath.isfile():
                if not abspath.exists():
                    return InputFileError('El archivo de entrada', abspath, 'no existe')
                elif abspath.isdir():
                    return InputFileError('El archivo de entrada', abspath, 'es un directorio')
                else:
                    return InputFileError('El archivo de entrada', abspath, 'no es un archivo regular')
            parentdir = abspath.parent()
            filename = abspath.name
            for key in jobspecs.inputfiles:
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
                {key:AbsPath(buildpath(parentdir, (basename, key))).isfile() or key in options.fileopts for key in jobspecs.filekeys}
            ):
                return InputFileError('El trabajo', q(basename), 'no se envió porque hacen faltan archivos de entrada o hay un conflicto entre ellos')
        return parentdir, basename

class OptDict:
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
    def interpolate(self):
        if 'molinterpolate' in self.common:
            prefix = []
            for i, path in enumerate(self.common.molinterpolate, 1):
                path = AbsPath(path, cwd=options.common.cwd)
                coords = readcoords(path)['coords']
                self.keywords['mol' + str(i)] = '\n'.join('{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format(*atom) for atom in coords)
                prefix.append(path.stem)
            if 'interpolate' in self.common:
                interpolation.suffix = self.common.interpolate
            else:
                interpolation.prefix = ''.join(prefix)
        elif 'interpolate' in self.common:
            interpolation.suffix = self.common.interpolate
        elif self.keywords:
            messages.error('Se especificaron variables de interpolación pero no se va a interpolar nada')

sysinfo = Bunch()
sysinfo.user = getuser()
sysinfo.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
# Python 3.5+ with pathlib
#sysinfo.home = Path.home()
sysinfo.home = expanduser('~')
sysinfo.hostname = gethostname()

environ = Bunch()
options = OptDict()
hostspecs = SpecBunch()
jobspecs = SpecBunch()
interpolation = Bunch()

