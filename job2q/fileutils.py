# -*- coding: utf-8 -*-
import os
import shutil
import string
from . import messages
from .utils import DefaultStr, deepjoin, printtree, getformatkeys

class NotAbsolutePath(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class PathKeyError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class EmptyDirectoryError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

class AbsPath(str):
    def __new__(cls, path, cwd=None):
        if not os.path.isabs(path):
            if isinstance(cwd, str) and os.path.isabs(cwd):
                path = os.path.join(cwd, path)
            else:
                raise NotAbsolutePath(path, 'is not an absolute path')
        path = os.path.normpath(path)
        obj = str.__new__(cls, path)
        obj.name = os.path.basename(path)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        obj.parts = iter(splitpath(obj))
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
    def isfile(self):
        return os.path.isfile(self)
    def isdir(self):
        return os.path.isdir(self)
    def linkto(self, *dest):
        symlink(self, os.path.join(*dest))
    def copyto(self, *dest):
        copyfile(self, os.path.join(*dest))
    def joinpath(self, path):
        return AbsPath(os.path.join(self, path))
    def setkeys(self, formatkeys):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if key is None:
                formatted += lit
            else:
                formatted += lit + formatkeys.get(key, '{' + key + '}')
        return AbsPath(formatted)
    def __floordiv__(self, right):
        if isinstance(right, AbsPath):
            raise Exception('Can not join two absolute paths')
        return AbsPath(formatpath(self, right))
    def validate(self):
        formatted = ''
        for lit, key, spec, _ in string.Formatter.parse(None, self):
            if key is None:
                formatted += lit
            else:
                raise PathKeyError(self, 'has undefined keys')
        return AbsPath(formatted)
#    def yieldparts(self):
#        for part in splitpath(self):
#            items = string.Formatter.parse(None, part)
#            first = next(items)
#            if first[1] is None:
#                yield first[0]
#            else:
#                try:
#                    second = next(items)
#                except:
#                    suffix = ''
#                else:
#                    if second[1] is None:
#                        suffix = second[0]
#                    else:
#                        raise PathKeyError(part, 'has parts with multiple keys')
#                yield first[0] + '{' + first[1] + '}' + suffix

#TODO Handle template exceptions
#TODO Check format of each component
def formatpath(*parts, **keys):
    path = deepjoin(parts, iter((os.path.sep, '.')))
    if keys:
        return path.format(**keys)
    else:
        return path

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

def getpartkey(part):
    formatkeys = getformatkeys(part)
    if formatkeys:
        if len(formatkeys) == 1:
            if part.format(**{formatkeys[0]: ''}):
                messages.error('La variable de interpolación no ocupa todo el componente', part)
            else:
                return formatkeys[0]
        else:
            messages.error('Hay más de una variable de interpolación en el componente', part)

def findbranches(parent, partlist, defaults, dirtree):
    part = next(partlist, None)
    if part:
        key = getpartkey(part)
        if key:
            choices = parent.listdir()
            default = defaults.get(key, None)
            for choice in choices:
                choice = DefaultStr(choice) if choice == default else str(choice)
                dirtree[choice] = {}
                findbranches(parent.joinpath(choice), partlist, defaults, dirtree[choice])
        else:
            findbranches(parent.joinpath(part), partlist, defaults, dirtree)

