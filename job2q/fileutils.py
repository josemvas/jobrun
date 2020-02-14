# -*- coding: utf-8 -*-
import os
import shutil
import string
from .utils import deepjoin, pathseps
from . import messages

class NotAbsolutePath(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class PathFormatError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class AbsPath(str):
    def __new__(cls, *args):
        path = os.path.join(*args)
        path = os.path.normpath(path)
        if not os.path.isabs(path):
            raise NotAbsolutePath(path, 'is not an absolute path')
        obj = str.__new__(cls, path)
        obj.name = os.path.basename(path)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    def keyexpand(self, keydict):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if not lit.startswith('/'):
                raise PathFormatError(self, 'has partial variable components')
            formatted += lit
            if key:
                try:
                    formatted += keydict[key]
                except KeyError:
                    if spec:
                         formatted += spec
                    else:
                         raise PathFormatError(self, 'has unresolved keys')
        return AbsPath(formatted)
    def setkeys(self, keydict):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if not lit.startswith('/'):
                raise PathFormatError(self, 'has partial variable components')
            formatted += lit
            if key is not None:
                if spec:
                    formatted += keydict.get(key, '{' + key + ':' + spec + '}')
                else:
                    formatted += keydict.get(key, '{' + key + '}')
        return AbsPath(formatted)
    def splitkeys(self):
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if not lit.startswith('/'):
                raise PathFormatError(self, 'has partial variable components')
            if key == '':
                raise PathFormatError('Path', self, 'has unresolved keys')
            yield lit[1:], key, spec
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
    def listdir(self):
            return os.listdir(self)

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

