# -*- coding: utf-8 -*-
import os
import shutil
import string
from . import messages
from .utils import DefaultItem, deepjoin, pathseps, natsort, printree, getformatkeys

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
                raise PathKeyError(self, 'has undefined keys')
        return AbsPath(formatted)
    def yieldcomponents(self):
        for component in splitpath(self):
            parts = string.Formatter.parse(None, component)
            first = next(parts)
            if first[1] is None:
                yield first[0]
            else:
                try:
                    second = next(parts)
                except:
                    suffix = ''
                else:
                    if second[1] is None:
                        suffix = second[0]
                    else:
                        raise PathKeyError(component, 'has components with multiple keys')
                yield first[0] + '{' + first[1] + '}' + suffix
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
    def joinpath(self, path):
        return AbsPath(os.path.join(self, path))

def buildpath(*args):
    path = deepjoin(args, iter(pathseps))
#    if splitpath(path) != [j for i in args for j in splitpath(i)]:
#        raise PathKeyError('Conflicting path components in', *args)
    return path

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

# Custom rmtree to only delete files modified after date
def rmtree(path, date):
    def delete_newer(node, date, delete):
        if os.path.getmtime(node) > date:
            try: delete(node)
            except OSError as e: print(e)
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            delete_newer(os.path.join(root, f), date, os.remove)
        for d in dirs:
            delete_newer(os.path.join(root, d), date, os.rmdir)
    delete_newer(path, date, os.rmdir)

def dirbranches(rootpath, components, defaults, tree):
    component = next(components, None)
    if component:
        formatkeys = getformatkeys(component)
        if formatkeys:
            choices = rootpath.listdir()
            default = defaults.get(formatkeys[0], None)
            for choice in choices:
                key = DefaultItem(choice, default)
                tree[key] = {}
                dirbranches(rootpath.joinpath(choice), components, defaults, tree[key])
        else:
            dirbranches(rootpath.joinpath(component), components, defaults, tree)

