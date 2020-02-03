# -*- coding: utf-8 -*-
import os
import re
import sys

wordseps = (' ', '')
pathseps = (os.path.sep, '.')

def deepjoin(a, i):
    return next(i).join(x if isinstance(x, str) else deepjoin(x, i) if hasattr(x, '__iter__') else str(x) for x in a if x)

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

def pathjoin(*args):
    return deepjoin(args, iter(pathseps))

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
