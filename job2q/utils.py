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

from job2q.messages import messages

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
        try: os.makedirs(path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else: raise

def remove(path):
    try: os.remove(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else: raise

def rmdir(path):
    try: os.rmdir(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else: raise

def copyfile(source, dest):
    try: shutil.copyfile(source, dest)
    except IOError as e:
        if e.errno == errno.ENOENT:
            if not os.path.isfile(source):
                messages.runerr('No existe el archivo de origen', source)
            else: raise
        if e.errno == errno.EEXIST:
            raise

def hardlink(source, dest):
    try: os.link(source, dest)
    except IOError as e:
        if e.errno == errno.ENOENT:
            if not os.path.isfile(source):
                messages.runerr('No existe el archivo de origen', source)
            else: raise
        if e.errno == errno.EEXIST:
            os.remove(dest)
            os.link(source, dest)

def strjoin(*args, sep='', gen=repeat):
    def rejoin(*args, sepgen):
        return next(sepgen).join(i if isinstance(i, str) else rejoin(*i, sepgen=sepgen) if isinstance(i, Iterable) else str(i) for i in args if i)
    return rejoin(*args, sepgen=gen(sep))

def wordjoin(*args):
    return strjoin(*args, sep=' ')

def linejoin(*args):
    return strjoin(strjoin(*args, sep='\n'), '\n')

def pathjoin(*args):
    return strjoin(*args, sep=os.sep+'.-', gen=iter)
    #return os.path.join(*['.'.join(str(j) for j in i) if type(i) is list else str(i) for i in args])

def pathexpand(path):
    return os.path.expanduser(os.path.expandvars(path))

