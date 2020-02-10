# -*- coding: utf-8 -*-
import os
import shutil
from . import messages
from .utils import deepjoin, pathseps

class NotAbsolutePath(Exception):
    pass

class AbsPath(str):
    def __new__(cls, *args, **kwargs):
        path = os.path.join(*args)
        path = path.format(**kwargs)
        path = os.path.normpath(path)
        if not os.path.isabs(path):
            raise NotAbsolutePath(path, 'is not an absolute path')
        obj = str.__new__(cls, path)
        obj.name = os.path.basename(path)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    def parent(self):
        return AbsPath(os.path.dirname(self))
    def joinpath(self, *args, **kwargs):
        return AbsPath(self, *args, **kwargs)
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

