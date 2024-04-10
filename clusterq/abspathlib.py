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

class AbsPath(list):
    def __init__(cls, path=None, parent=None):
        if path is None:
            path = PurePath('/')
        elif isinstance(path, str):
            if not path:
                raise ValueError
            if os.path.sep*2 in part:
                raise ValueError
            path = PurePath(path)
        elif isinstance(path, list):
            if not path:
                raise ValueError
            for part in path:
                if not isinstance(part, str):
                    raise TypeError
                if not part:
                    raise ValueError
                if os.path.sep in part:
                    raise ValueError
            path = PurePath(*path)
        elif isinstance(path, PurePath):
            pass
        else:
            raise TypeError
        if parent is None:
            if not path.is_absolute():
                raise NotAbsolutePathError
            super().__init__(path.parts[1:]))
        else:
            if path.is_absolute():
                raise AbsolutePathError
            super().__init__(parent.parts[1:]))
            self.extend(path.parts)
    def __str__(self):
        os.path.sep + os.path.sep.join(self)
    def __mul__(self, other):
        if not isinstance(other, str):
            raise TypeError('Right operand must be a string')
        if os.path.sep in other:
            raise ValueError('Can not use a path as an extension')
        return AbsPath(self.name + '.' + other, parent=self.parent())
    def __truediv__(self, other):
        if not isinstance(other, str):
            raise TypeError('Right operand must be a string')
        if isinstance(other, AbsPath):
            raise ValueError('Can not join two absolute paths')
        return AbsPath(other, parent=self)
    def parent(self):
        return AbsPath(self[:-1])
    def name(self):
        return self[-1]
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
