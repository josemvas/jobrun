# -*- coding: utf-8 -*-
import os
import shutil
import string
from . import messages
from .utils import deepjoin, pathseps, natsort

class NotAbsolutePath(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class PathFormatError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class EmptyDirectoryError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class AbsPath(str):
    def __new__(cls, *args, defaultroot=None):
        path = os.path.join(*args)
        path = os.path.normpath(path)
        if not os.path.isabs(path):
            if isinstance(defaultroot, str) and os.path.isabs(defaultroot):
                path = os.path.join(defaultroot, path)
            else:
                raise NotAbsolutePath(path, 'is not an absolute path')
        obj = str.__new__(cls, path)
        obj.name = os.path.basename(path)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    def kexpand(self, keydict):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if lit.startswith('/'):
                if key is None:
                    formatted += lit
                else:
                    try:
                        formatted += lit + keydict[key]
                    except KeyError:
                        if spec:
                            formatted += lit + spec
                        else:
                            raise PathFormatError(self, 'has unresolved keys')
            else:
                raise PathFormatError(self, 'has partial variable components')
        return AbsPath(formatted)
    def setkeys(self, keydict):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if lit.startswith('/'):
                if key is None:
                    formatted += lit
                elif spec:
                    formatted += lit + keydict.get(key, '{' + key + ':' + spec + '}')
                else:
                    formatted += lit + keydict.get(key, '{' + key + '}')
            else:
                raise PathFormatError(self, 'has partial variable components')
        return AbsPath(formatted)
    def splitkeys(self, defaults):
        parts = []
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if lit.startswith('/'):
                if key is None:
                    if parts:
                        parts[-1][1] = lit[1:]
                    else:
                        raise PathFormatError(self, 'does not have selectable components')
                else:
                    try:
                        parts.append((lit[1:], '', defaults[int(key)]))
                    except IndexError:
                        parts.append((lit[1:], '', spec))
                    except ValueError:
                        raise PathFormatError(self, 'has invalid or unresolved keys')
            else:
                raise PathFormatError(self, 'has partial variable components')
        return parts
    def listdir(self):
        diritems = os.listdir(self)
        if diritems:
            return diritems
        else:
            raise EmptyDirectoryError(self, 'is empty')
    def parent(self):
        return AbsPath(os.path.dirname(self))
    def joinpath(self, *args):
        return AbsPath(self, *args)
    def hasext(self, suffix):
        return self.suffix == suffix
    def exists(self):
        return os.path.exists(self)
    def isfile(self):
        return os.path.isfile(self)
    def isdir(self):
        return os.path.isdir(self)

def diritems(abspath):
    try:
        return natsort(abspath.listdir())
    except FileNotFoundError:
        messages.cfgerror('El directorio', abspath, 'no existe')
    except NotADirectoryError:
        messages.cfgerror('La ruta', abspath, 'no es un directorio')
    except EmptyDirectoryError:
        messages.cfgerror('El directorio', abspath, 'está vacío')

def pathjoin(*args):
    return deepjoin(args, iter(pathseps))

def makedirs(path):
    try: os.makedirs(path)
    except FileExistsError:
        pass
    except PermissionError:
        messages.runerror('No se puede crear el directorio', path, 'porque no tiene permiso')

def remove(path):
    try: os.remove(path)
    except FileNotFoundError:
        pass
    except PermissionError:
        messages.runerror('No se puede eliminar el archivo', path, 'porque no tiene permiso')

def rmdir(path):
    try: os.rmdir(path)
    except FileNotFoundError:
        pass
    except PermissionError:
        messages.runerror('No se puede eliminar el directorio', path, 'porque no tiene permiso')

def copyfile(source, dest):
    try: shutil.copyfile(source, dest)
    except FileExistsError:
        os.remove(dest)
        shutil.copyfile(source, dest)
    except FileNotFoundError:
        messages.runerror('No se puede copiar el archivo', source, 'porque no existe')
    except PermissionError:
        messages.runerror('No se puede copiar el archivo', source, 'a', dest, 'porque no tiene permiso')

def hardlink(source, dest):
    try: os.link(source, dest)
    except FileExistsError:
        os.remove(dest)
        os.link(source, dest)
    except FileNotFoundError:
        messages.runerror('No se puede copiar el archivo', source, 'porque no existe')
    except PermissionError:
        messages.runerror('No se puede enlazar el archivo', source, 'a', dest, 'porque no tiene permiso')

