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
    def __new__(cls, *args, cwdir=None):
        path = os.path.join(*args)
        if splitpath(path) != [ j for i in args for j in splitpath(i) ]:
            raise PathFormatError('Conflicting path components in', *args)
        path = os.path.normpath(os.path.expanduser(path))
        if not os.path.isabs(path):
            if isinstance(cwdir, str) and os.path.isabs(cwdir):
                path = os.path.join(cwdir, path)
            else:
                raise NotAbsolutePath(path, 'is not an absolute path')
        obj = str.__new__(cls, path)
        obj.name = os.path.basename(path)
        obj.stem, obj.extension = os.path.splitext(obj.name)
        return obj
    def setkeys(self, keydict):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if key is None:
                formatted += lit
            elif spec:
                formatted += lit + keydict.get(key, '{' + key + ':' + spec + '}')
            else:
                formatted += lit + keydict.get(key, '{' + key + '}')
        return AbsPath(formatted)
    def validate(self):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if key is None:
                formatted += lit
            else:
                raise PathFormatError(self, 'has undefined keys')
        return AbsPath(formatted)
    def populate(self):
        for component in splitpath(self):
            yield ''.join(splitcomponent(component))
    def listdir(self):
        return os.listdir(self)
    def parent(self):
        return AbsPath(os.path.dirname(self))
    def hasext(self, extension):
        return self.extension == extension
    def exists(self):
        return os.path.exists(self)
    def isfile(self):
        return os.path.isfile(self)
    def isdir(self):
        return os.path.isdir(self)
    def linkto(self, *dest):
        symlink(self, os.path.join(*dest))
    def copyto(self, *dest):
        copyfile(self, os.path.join(*dest))
    def joinpath(self, *args):
        return AbsPath(self, *args)

def splitcomponent(component):
    parts = string.Formatter.parse(None, component)
    first = next(parts)
    if first[1] is None:
        return first[0],
    else:
        try:
            int(first[1])
        except ValueError:
            raise PathFormatError(self, 'has unresolved non integer keys')
        try:
            second = next(parts)
        except:
            suffix = ''
        else:
            if second[1] is None:
                suffix = second[0]
            else:
                raise PathFormatError(self, 'has components with multiple keys')
        return first[0], '{' + first[1] + '}', suffix

def diritems(abspath, component):
    try:
        dirlist = abspath.listdir()
    except FileNotFoundError:
        messages.error('El directorio', abspath, 'no existe')
    except NotADirectoryError:
        messages.error('La ruta', abspath, 'no es un directorio')
    prefix, _, suffix = splitcomponent(component)
    dirlist = [ i for i in dirlist if i.startswith(prefix) and i.endswith(suffix) ]
    if dirlist:
        return natsort(dirlist)
    else:
        messages.error('El directorio', abspath, 'está vacío o no coincide con la búsqueda')

def buildpath(*args):
    return deepjoin(args, iter(pathseps))

def splitpath(path):
    if path:
        path = os.path.normpath(path)
        if path == os.path.sep:
            return [os.path.sep]
        if path.startswith(os.path.sep):
            return [os.path.sep] + path[1:].split(os.path.sep)
        else:
            return path.split(os.path.sep)
    else:
        return []

def mkdir(path):
    try: os.mkdir(path)
    except FileExistsError:
        pass
    except FileNotFoundError:
        messages.error('No se puede crear el directorio', path, 'porque la ruta no existe')
    except PermissionError:
        messages.error('No se puede crear el directorio', path, 'porque no tiene permiso')

def makedirs(path):
    try: os.makedirs(path)
    except FileExistsError:
        pass
    except PermissionError:
        messages.error('No se puede crear el directorio', path, 'porque no tiene permiso')

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

