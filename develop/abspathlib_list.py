import os
from clinterface.messages import *
from .i18n import _

def file_except_info(exception, path):
    if isinstance(exception, IsADirectoryError):
        print_failure(_('La ruta $path es un directorio'), path=path)
    elif isinstance(exception, FileExistsError):
        print_failure(_('El archivo $path ya existe'), path=path)
    elif isinstance(exception, FileNotFoundError):
        print_failure(_('El archivo $path no existe'), path=path)
    elif isinstance(exception, OSError):
        print_failure(_('Error de sistema: $exception'), exception=str(exception))
    else:
        print_error_and_exit(_('$exceptype: $exception'), exceptype=type(exception).__name__, exception=str(exception))

def dir_except_info(exception, path):
    if isinstance(exception, NotADirectoryError):
        print_failure(_('La ruta $path no es un directorio'), path=path)
    elif isinstance(exception, FileExistsError):
        print_failure(_('El directorio $path ya existe'), path=path)
    elif isinstance(exception, FileNotFoundError):
        print_failure(_('El directorio $path no existe'), path=path)
    elif isinstance(exception, OSError):
        print_failure(_('Error de sistema: $exception'), exception=str(exception))
    else:
        print_error_and_exit(_('$exceptype: $exception'), exceptype=type(exception).__name__, exception=str(exception))

class NotAbsolutePathError(Exception):
    pass

class AbsPath(list):
    def __init__(cls, path=None, relto=None):
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
        if relto is None:
            if not path.is_absolute():
                raise NotAbsolutePathError
            super().__init__(path.parts[1:]))
        else:
            if path.is_absolute():
                raise AbsolutePathError
            super().__init__(relto.parts[1:]))
            self.extend(path.parts)
    def __str__(self):
        os.path.sep + os.path.sep.join(self)
    def __mod__(self, other):
        if not isinstance(other, str):
            raise TypeError('Right operand must be a string')
        if os.path.sep in other:
            raise ValueError('Can not use a path as an extension')
        return AbsPath(self.name + '.' + other, relto=self.parent())
    def __truediv__(self, other):
        if not isinstance(other, str):
            raise TypeError('Right operand must be a string')
        if isinstance(other, AbsPath):
            raise ValueError('Can not join two absolute paths')
        return AbsPath(other, relto=self)
    def parent(self):
        return AbsPath(self[:-1])
    def name(self):
        return self[-1]
    def listdir(self):
        return os.listdir(self)
    def exists(self):
        return os.path.exists(self)
    def is_file(self):
        return os.path.isfile(self)
    def is_dir(self):
        return os.path.isdir(self)
    def is_symlink(self):
        return os.path.islink(self)
    def unlink(self):
        os.unlink(self)
    def rmdir(self):
        os.rmdir(self)
    def mkdir(self):
        os.mkdir(self)
    def readlink(self):
        return os.readlink(self)
    def symlink_to(self, dest):
        os.symlink_to(self, dest)
    def chmod(self, mode):
        os.chmod(self, mode)

