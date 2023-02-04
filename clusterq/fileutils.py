import os
import string
import shutil
import fnmatch
from clinterface import messages
from .utils import FormatDict, deepjoin

def file_except_info(exception, path):
    if isinstance(exception, IsADirectoryError):
         messages.failure('La ruta {} es un directorio'.format(path))
    elif isinstance(exception, FileExistsError):
         messages.failure('El archivo {} ya existe'.format(path))
    elif isinstance(exception, FileNotFoundError):
         messages.failure('El archivo {} no existe'.format(path))
    elif isinstance(exception, OSError):
         messages.failure(str(exception).format(path))
    else:
         messages.error(type(exception).__name__)

def dir_except_info(exception, path):
    if isinstance(exception, NotADirectoryError):
         messages.failure('La ruta {} no es un directorio'.format(path))
    elif isinstance(exception, FileExistsError):
         messages.failure('El directorio {} ya existe'.format(path))
    elif isinstance(exception, FileNotFoundError):
         messages.failure('El directorio {} no existe'.format(path))
    elif isinstance(exception, OSError):
         messages.failure(str(exception).format(path))
    else:
         messages.error(type(exception).__name__)

class NotAbsolutePath(Exception):
    pass

class AbsPath(str):
    def __new__(cls, path, cwd=None):
        if not isinstance(path, str):
            raise TypeError('Path must be a string')
        if not path:
            raise ValueError('Path can not be empty')
        try:
            path.format()
        except (IndexError, KeyError):
            raise ValueError('Path can not be a format string')
        if cwd is None:
            if not os.path.isabs(path):
                raise NotAbsolutePath
        elif not os.path.isabs(path):
            if not isinstance(cwd, str):
                raise TypeError('Working directory must be a string')
            if not os.path.isabs(cwd):
                raise ValueError('Working directory must be an absolute path')
            path = os.path.join(cwd, path)
        obj = str.__new__(cls, os.path.normpath(path))
        obj.parts = pathsplit(obj)
        obj.name = os.path.basename(obj)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    def __truediv__(self, right):
        if not isinstance(right, str):
            raise TypeError('Right operand must be a string')
        if os.path.isabs(right):
            raise ValueError('Can not join two absolute paths')
        return AbsPath(right, cwd=self)
    def append(self, *args):
        path = self
        for i in args:
            if not isinstance(i, str):
                raise TypeError('Right operand must be a string')
            if os.path.isabs(i):
                raise ValueError('Can not join two absolute paths')
            path = AbsPath(i, cwd=path)
        return path
    @property
    def parent(self):
        return AbsPath(os.path.dirname(self))
    def listdir(self):
        return os.listdir(self)
    def hasext(self, suffix):
        return self.suffix == suffix
    def exists(self):
        return os.path.exists(self)
    def remove(self):
        try: os.remove(self)
        except FileNotFoundError:
            pass
    def rmdir(self):
        try: os.rmdir(self)
        except FileNotFoundError:
            pass
    def mkdir(self):
        try: os.mkdir(self)
        except FileExistsError:
            if os.path.isdir(self):
                pass
            else:
                raise
    def chmod(self, mode):
        os.chmod(self, mode)
    def makedirs(self):
        try: os.makedirs(self)
        except FileExistsError:
            if os.path.isdir(self):
                pass
            else:
                raise
    def copyfile(self, dest):
        shutil.copyfile(self, dest)
    def symlink(self, dest):
        try:
            os.symlink(self, dest)
        except FileExistsError:
            os.remove(dest)
            os.symlink(self, dest)
    def readlink(self):
        return os.readlink(self)
    def glob(self, expr):
        return fnmatch.filter(os.listdir(self), expr)
    def isfile(self):
        return os.path.isfile(self)
    def isdir(self):
        return os.path.isdir(self)
    def islink(self):
        return os.path.islink(self)
    def assertfile(self):
        if os.path.exists(self):
            if not os.path.isfile(self):
                if os.path.isdir(self):
                    raise IsADirectoryError
                else:
                    raise OSError('{} no es un archivo regular')
        else:
            raise FileNotFoundError
    def assertdir(self):
        if os.path.exists(self):
            if os.path.isfile(self):
                raise NotADirectoryError
        else:
            raise FileNotFoundError

def pathjoin(*components):
    return deepjoin(components, [os.path.sep, '.'])

def pathsplit(path):
    if path:
        if path == os.path.sep:
            componentlist = [os.path.sep]
        elif path.startswith(os.path.sep):
            componentlist = [os.path.sep] + path[1:].split(os.path.sep)
        else:
            componentlist = path.split(os.path.sep)
        if '' in componentlist:
            raise Exception('Path has empty components')
        return componentlist
    else:
        return []

def dirbranches(trunk, componentlist, dirtree):
    try:
        trunk.assertdir()
    except Exception as e:
        file_except_info(e, trunk)
        raise SystemExit
    if componentlist:
        formatdict = FormatDict()
        component = componentlist.pop(0).format_map(formatdict)
        if formatdict.missing_keys:
            branches = trunk.glob(component.format_map(FormatDict('*')))
            for branch in branches:
                dirtree[branch] = {}
                dirbranches(trunk/branch, componentlist, dirtree[branch])
        else:
            dirbranches(trunk/component, componentlist, dirtree)
