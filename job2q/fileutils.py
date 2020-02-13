# -*- coding: utf-8 -*-
import os
import shutil
import string
from .utils import deepjoin, pathseps
from . import messages

class NotAbsolutePath(Exception):
    pass

class AbsPath(str):
    def __new__(cls, *args):
        path = os.path.join(*args)
        path = os.path.normpath(path)
        if not os.path.isabs(path):
            raise NotAbsolutePath(path + ' is not an absolute path')
        obj = str.__new__(cls, path)
        obj.name = os.path.basename(path)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    def resolvekeys(self, **kwargs):
        formatted = ''
        for literal, key, default, _ in string.Formatter.parse(None, self):
            formatted += literal
            if key:
                try:
                    formatted += kwargs[key]
                except KeyError:
                    if default:
                         formatted += default
                    else:
                         raise ValueError(self + ' has unresolved keys')
        return AbsPath(formatted)
    def splitkeys(self, **kwargs):
        for literal, key, default, _ in string.Formatter.parse(None, self):
            if literal.startswith('/') and literal.endswith('/'):
                literal = literal[1:]
            else:
                raise ValueError(self + ' has partial variable components')
            yield key, default, literal
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

