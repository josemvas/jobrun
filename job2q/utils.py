# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys
import errno
import shutil

# Python 2 and 3
def textform(*args, **kwargs):
# Python 3 optional arguments
#def textform(*args, sep=' ', end='\n', indent=0):
    sep = kwargs.pop('sep', ' ')
    end = kwargs.pop('end', '\n')
    indent = kwargs.pop('indent', 0)
    line = [ ]
    for arg in args:
        if type(arg) is list: line.append(sep.join(arg))
        elif arg: line.append(arg)
    return ' '*indent + sep.join(line) + end

def q(string):
    if '"' in string and "'" in string: notices.runerr('El texto contiene comillas simples y dobles:', string )
    if '"' in string: return '"{0}"'.format(string.rstrip().replace('"', "'"))
    else: return '"{0}"'.format(string.rstrip())

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
                notices.runerr('No se pudo crear el directorio', e)
def remove(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            notices.runerr('No se pudo eliminar el archivo:', e)

def rmdir(path):
    try:
        os.rmdir(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            notices.runerr('No se pudo eliminar el directorio:', e)

def copyfile(source, dest):
    try:
        shutil.copyfile(source, dest)
    except IOError as e:
        if e.errno == errno.ENOENT:
            notices.runerr('No existe el archivo de origen', source + ',', 'o el directorio de destino', os.path.dirname(dest))
        if e.errno == errno.EEXIST:
            notices.runerr('Ya existe el archivo de destino', dest)

def pathjoin(*components):
    return os.path.join(*[ '.'.join(x) if type(x) is list else x for x in components ])

def basename(path):
    return os.path.basename(path)

def pathexpand(path):
    return os.path.expanduser(os.path.expandvars(path))

