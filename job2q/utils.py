# -*- coding: utf-8 -*-
import os
import re
import sys
from collections import Iterable
from itertools import repeat
from . import messages
from .decorators import join_path_components

homedir = os.path.expanduser('~')

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

def collapseuser(path):
    if path == homedir:
        return '~'
    elif path.startswith(homedir + os.sep):
        return '~' + path[len(homedir):]
    return path

@join_path_components
def isabspath(path):
    return os.path.isabs(os.path.expanduser(os.path.expandvars(path)))

@join_path_components
def normalpath(path):
    return os.path.normpath(os.path.expanduser(os.path.expandvars(path)))

def realpath(path):
    return os.path.realpath(os.path.expanduser(os.path.expandvars(path)))

def deepjoin(*args, sepgen):
    return next(sepgen).join(i if isinstance(i, str) else deepjoin(*i, sepgen=sepgen) if isinstance(i, Iterable) else str(i) for i in args if i)

def wordjoin(*args):
    return deepjoin(*args, sepgen=repeat(' '))

def barejoin(*args):
    return deepjoin(*args, sepgen=repeat(''))

def pathjoin(*args):
    return deepjoin(*args, sepgen=iter(os.path.sep + '.-'))

def p(string):
    return '({0})'.format(string)

def q(string):
    return '"{0}"'.format(string)

def sq(string):
    return "'{0}'".format(string)

def natsort(text):
    return [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', text)]

def alnum(string): 
    return ''.join(c for c in string if c.isalnum())
