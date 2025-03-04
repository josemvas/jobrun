import os
import string
import shutil
import fnmatch
from clinterface import messages, _

def file_except_info(exception, path):
    if isinstance(exception, IsADirectoryError):
         messages.failure(_('La ruta $path es un directorio', path=path))
    elif isinstance(exception, FileExistsError):
         messages.failure(_('El archivo $path ya existe', path=path))
    elif isinstance(exception, FileNotFoundError):
         messages.failure(_('El archivo $path no existe', path=path))
    elif isinstance(exception, OSError):
        messages.failure(_('Error de sistema'), str(exception))
    else:
        messages.error(exctype=type(exception).__name__, excmessage=str(exception))

def dir_except_info(exception, path):
    if isinstance(exception, NotADirectoryError):
         messages.failure(_('La ruta $path no es un directorio', path=path))
    elif isinstance(exception, FileExistsError):
         messages.failure(_('El directorio $path ya existe', path=path))
    elif isinstance(exception, FileNotFoundError):
         messages.failure(_('El directorio $path no existe', path=path))
    elif isinstance(exception, OSError):
        messages.failure(_('Error de sistema'), str(exception))
    else:
        messages.error(exctype=type(exception).__name__, excmessage=str(exception))

class NotAbsolutePath(Exception):
    pass

class AbsPath(str):
    def __new__(cls, path='/', parent=None):
        if not isinstance(path, str):
            raise TypeError('Path must be a string')
        if not path:
            raise ValueError('Path can not be empty')
        if parent is None:
            if not os.path.isabs(path):
                raise NotAbsolutePath
        elif not os.path.isabs(path):
            if not isinstance(parent, str):
                raise TypeError('Parent directory must be a string')
            if not os.path.isabs(parent):
                raise ValueError('Parent directory must be an absolute path')
            path = os.path.join(parent, path)
#        obj = str.__new__(cls, os.path.normpath(path))
        obj = str.__new__(cls, path)
        obj.parts = pathsplit(obj)
        obj.name = os.path.basename(obj)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    def __sub__(self, right):
        if not isinstance(right, str):
            print(type(right))
            raise TypeError('Right operand must be a string')
        if '/' in right:
            raise ValueError('Can not use a path as an extension')
        return AbsPath(self.name + '.' + right, parent=self.parent())
    def __truediv__(self, right):
        if not isinstance(right, str):
            raise TypeError('Right operand must be a string')
        if isinstance(right, AbsPath):
            raise ValueError('Can not join two absolute paths')
        return AbsPath(right, parent=self)
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
    def copyto(self, dest):
        shutil.copy(self, dest)
    def copyas(self, dest):
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
