# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys
import errno
import shutil
from builtins import str
from collections import Iterable
from itertools import repeat

from job2q.strings import fpsep

def q(string):
    if '"' in string and "'" in string: messages.runerr('El texto contiene comillas simples y dobles:', string )
    if '"' in string: return '"{0}"'.format(string.rstrip().replace('"', "'"))
    else: return '"{0}"'.format(string.rstrip())

def sq(string):
    return "'{0}'".format(string.rstrip())

def dq(string):
    return '"{0}"'.format(string.rstrip())

def makedirs(*args):
    for path in args:
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                messages.runerr('No se pudo crear el directorio', e)
def remove(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            messages.runerr('No se pudo eliminar el archivo:', e)

def rmdir(path):
    try:
        os.rmdir(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            messages.runerr('No se pudo eliminar el directorio:', e)

def copyfile(source, dest):
    try:
        shutil.copyfile(source, dest)
    except IOError as e:
        if e.errno == errno.ENOENT:
            messages.runerr('No existe el archivo de origen', source + ',', 'o el directorio de destino', os.path.dirname(dest))
        if e.errno == errno.EEXIST:
            messages.runerr('Ya existe el archivo de destino', dest)

def strjoin(*args, sep=repeat('')):
    return next(sep).join(i if isinstance(i, str) else strjoin(*i, sep=sep) if isinstance(i, Iterable) else str(i) for i in args if i)

def wordjoin(*args):
    return strjoin(*args, sep=repeat(' '))

def pathjoin(*args):
    return strjoin(*args, sep=iter(fpsep))
    #return os.path.join(*['.'.join(str(j) for j in i) if type(i) is list else str(i) for i in args])

def basename(path):
    return os.path.basename(path)

def pathexpand(path):
    return os.path.expanduser(os.path.expandvars(path))

