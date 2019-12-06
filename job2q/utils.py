# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import errno
import shutil
import inspect
from job2q.classes import ec
from termcolor import colored
from past.builtins import basestring


# Python 2 and 3
def textform(*args, **kwargs):
    sep = kwargs.pop('sep', ' ')
    end = kwargs.pop('end', '\n')
    indent = kwargs.pop('indent', 0)
    line = [ ]
    for arg in args:
        if type(arg) is list: line.append(sep.join(arg))
        elif arg: line.append(arg)
    return ' '*indent + sep.join(line) + end
# Python 3 only
#def textform(*args, sep=' ', end='\n', indent=0):
#    line = [ ]
#    for arg in args:
#        if type(arg) is list: line.append(sep.join(arg))
#        elif type(arg) is str: line.append(arg)
#    return ' '*indent + sep.join(line) + end


def q(string):
    if '"' in string and "'" in string: post('El texto contiene comillas simples y dobles:', string , kind=ec.runerr)
    if '"' in string: return '"{}"'.format(string.rstrip().replace('"', "'"))
    else: return '"{}"'.format(string.rstrip())


def dq(string):
    return '"{}"'.format(string.rstrip())


def makedirs(*args):
    for path in args:
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                post('No se pudo crear el directorio', e, kind=ec.runerr)

def remove(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            post('No se pudo eliminar el archivo:', e, kind=ec.runerr)


def rmdir(path):
    try:
        os.rmdir(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            post('No se pudo eliminar el directorio:', e, kind=ec.runerr)


def copyfile(source, dest):
    try:
        shutil.copyfile(source, dest)
    except IOError as e:
        if e.errno == errno.ENOENT:
            post('No existe el archivo de origen', source + ',', 'o el directorio de destino', os.path.dirname(dest), kind=ec.runerr)
        if e.errno == errno.EEXIST:
            post('Ya existe el archivo de destino', dest, kind=ec.runerr)


def pathjoin(*components):
    return os.path.join(*[ '.'.join(x) if type(x) is list else x for x in components ])


def basename(path):
    return os.path.basename(path)


def pathexpand(path):
    return os.path.expanduser(os.path.expandvars(path))


def catch_keyboard_interrupt(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KeyboardInterrupt:
            sys.exit(colored('Cancelado por el usuario', 'red'))
    return wrapper


def join_positional_args(fn):
    def wrapper(*args, **kwargs):
        prompt = ' '.join([i if isinstance(i, basestring) else str(i) for i in args])
        return fn(prompt=prompt, **kwargs)
    return wrapper


def decorate_class_methods(decorator):
    def decorate(cls):
        for name, fn in inspect.getmembers(cls, inspect.isroutine):
            setattr(cls, name, decorator(fn))
        return cls
    return decorate


def override_class_methods(module):
    def override(cls):
        for name, fn in inspect.getmembers(cls, inspect.isroutine):
            try: setattr(cls, name, getattr(module, name))
            except Exception as e: print('Exception:', e)
        return cls
    return override


