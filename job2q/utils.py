# -*- coding: utf-8 -*-
import os
import re
import sys
from collections import Iterable
from itertools import repeat
from . import messages

home = os.path.expanduser('~')

def makedirs(path):
    try: os.makedirs(path)
    except FileExistsError as e:
        pass

def remove(path):
    try: os.remove(path)
    except FileNotFoundError as e:
        pass

def rmdir(path):
    try: os.rmdir(path)
    except FileNotFoundError as e:
        pass

def hardlink(source, dest):
    try: os.link(source, dest)
    except FileExistsError as e:
        os.remove(dest)
        os.link(source, dest)
    except FileNotFoundError as e:
        pass

def contractuser(path):
    if path == home:
        return '~'
    elif path.startswith(home + os.sep):
        return '~' + path[len(home):]
    return path

def realpath(path):
    return os.path.realpath(os.path.expanduser(os.path.expandvars(path)))

def iterjoin(*args, sepgen):
    return next(sepgen).join(i if isinstance(i, str) else iterjoin(*i, sepgen=sepgen) if isinstance(i, Iterable) else str(i) for i in args if i)

def wordjoin(*args):
    return iterjoin(*args, sepgen=repeat(' '))

def linejoin(*args):
    lines = iterjoin(*args, sepgen=repeat('\n'))
    return lines + '\n' if lines else ''

def pathjoin(*args):
    return iterjoin(*args, sepgen=iter(os.path.sep + '.-'))

def p(string):
    return '({0})'.format(string)

def q(string):
    return '"{0}"'.format(string)

def qq(string):
    return '"\'{0}\'"'.format(string)

def natsort(text):
    return [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', text)]

def alnum(string): 
    return ''.join(c for c in string if c.isalnum())
