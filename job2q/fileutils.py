# -*- coding: utf-8 -*-
import os
import shutil
import string
from . import messages
from .utils import DictTemplate, TestKeyDict, deepjoin

class NotAbsolutePath(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class AbsPath(str):
    def __new__(cls, path, cwd=None):
        if not isinstance(path, str):
            raise Exception('Path must be a string')
        if cwd is None:
            if not os.path.isabs(path):
                raise NotAbsolutePath()
        elif not os.path.isabs(path):
            if not isinstance(cwd, str):
                raise Exception('Root must be a string')
            if not os.path.isabs(cwd):
                raise Exception('Root must be an absolute path')
            path = os.path.join(cwd, path)
        obj = str.__new__(cls, os.path.normpath(path))
        obj.parts = splitpath(obj)
        obj.name = os.path.basename(obj)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    @property
    def parent(self):
        return AbsPath(os.path.dirname(self))
    def listdir(self):
        return os.listdir(self)
    def hasext(self, suffix):
        return self.suffix == suffix
    def exists(self):
        return os.path.exists(self)
    def mkdir(self):
        mkdir(self)
    def makedirs(self):
        makedirs(self)
    def linkto(self, *dest):
        symlink(self, os.path.join(*dest))
    def copyto(self, *dest):
        copyfile(self, os.path.join(*dest))
    def __truediv__(self, right):
        if os.path.isabs(right):
            raise Exception('Can not join two absolute paths')
        return AbsPath(right, cwd=self)
    def isfile(self):
        if os.path.exists(self):
            if os.path.isfile(self):
                return True
            if os.path.isdir(self):
                self.failreason = 'La ruta {} es un directorio'.format(self)
            else:
                self.failreason = 'La ruta {} no es un archivo regular'.format(self)
        else:
            self.failreason = 'El archivo {} no existe'.format(self)
        return False
    def isdir(self):
        return os.path.isdir(self)
        if os.path.exists(self):
            if os.path.isdir(self):
                return True
            if os.path.isfile(self):
                self.failreason = 'La ruta {} es un archivo'.format(self)
            else:
                self.failreason = 'La ruta {} no es un directorio'.format(self)
        else:
            self.failreason = 'El directorio {} no existe'.format(self)
        return False

def mkdir(path):
    try: os.mkdir(path)
    except FileExistsError:
        if os.path.isdir(path):
            pass
        else:
            raise
    except FileNotFoundError:
        messages.error('No se puede crear el directorio', path, 'porque la ruta no existe')
    except PermissionError:
        messages.error('No se puede crear el directorio', path, 'porque no tiene permiso de escribir en esta ruta')

def makedirs(path):
    try: os.makedirs(path)
    except FileExistsError:
        if os.path.isdir(path):
            pass
        else:
            raise
    except PermissionError:
        messages.error('No se puede crear el directorio', path, 'porque no tiene permiso de escribir en esta ruta')

def remove(path):
    try: os.remove(path)
    except FileNotFoundError:
        pass
    except PermissionError:
        messages.error('No se puede eliminar el archivo', path, 'porque no tiene permiso')

def rmdir(path):
    try: os.rmdir(path)
    except FileNotFoundError:
        pass
    except PermissionError:
        messages.error('No se puede eliminar el directorio', path, 'porque no tiene permiso')

def copyfile(source, dest):
    try: shutil.copyfile(source, dest)
    except FileExistsError:
        os.remove(dest)
        shutil.copyfile(source, dest)
    except FileNotFoundError:
        messages.error('No se puede copiar el archivo', source, 'porque no existe')
    except PermissionError:
        messages.error('No se puede copiar el archivo', source, 'a', dest, 'porque no tiene permiso')

def link(source, dest):
    try: os.link(source, dest)
    except FileExistsError:
        os.remove(dest)
        os.link(source, dest)
    except FileNotFoundError:
        messages.error('No se puede copiar el archivo', source, 'porque no existe')
    except PermissionError:
        messages.error('No se puede enlazar el archivo', source, 'a', dest, 'porque no tiene permiso')

def symlink(source, dest):
    try: os.symlink(source, dest)
    except FileExistsError:
        os.remove(dest)
        os.symlink(source, dest)
    except FileNotFoundError:
        messages.error('No se puede copiar el archivo', source, 'porque no existe')
    except PermissionError:
        messages.error('No se puede enlazar el archivo', source, 'a', dest, 'porque no tiene permiso')

# Custom rmtree to only delete files modified after date
def rmtree(path, date):
    def delete_newer(node, date, delete):
        if os.path.getmtime(node) > date:
            try: delete(node)
            except OSError as e: print(e)
    for parent, dirs, files in os.walk(path, topdown=False):
        for f in files:
            delete_newer(os.path.join(parent, f), date, os.remove)
        for d in dirs:
            delete_newer(os.path.join(parent, d), date, os.rmdir)
    delete_newer(path, date, os.rmdir)

def componentkey(component):
    d = TestKeyDict()
    literal = DictTemplate(component).substitute(d)
    if d._key and literal:
        messages.error('La variable de interpolación debe ocupar todo el componente')
    return d._key

#TODO Include the defults in parts parameter as tuples
def dirbranches(trunk, parts, dirtree):
    if parts:
        stem = parts.pop(0)
        if componentkey(stem):
            branches = trunk.listdir()
            for branch in branches:
                dirtree[branch] = {}
                dirbranches(trunk/branch, parts, dirtree[branch])
        else:
            dirbranches(trunk/stem, parts, dirtree)

def pathjoin(*components, keys={}):
    try:
        return deepjoin(components, [os.path.sep, '.']).format(**keys)
    except KeyError as e:
        messages.error('Hay variables de interpolación sin definir en la ruta', var=e.args[0])

def splitpath(path):
    if path:
        if path == os.path.sep:
            parts = [os.path.sep]
        elif path.startswith(os.path.sep):
            parts = [os.path.sep] + path[1:].split(os.path.sep)
        else:
            parts = path.split(os.path.sep)
        if '' in parts:
            raise Exception('Path has empty parts')
        return parts
    else:
        return []

