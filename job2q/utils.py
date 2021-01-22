# -*- coding: utf-8 -*-
import os
import re
from . import colors

wordseps = (' ', '')
pathseps = (os.path.sep, '.')
boolstrs = {'True' : True, 'False' : False}

class IdentityList(list):
    def __init__(self, *args):
        list.__init__(self, args)
    def __contains__(self, other):
        return any(o is other for o in self)

class Bunch(dict):
    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)
    def __setattr__(self, item, value):
        self.__setitem__(item, value)

def o(key, value=None):
    if value is not None:
        return('--{}={}'.format(key.replace('_', '-'), value))
    else:
        return('--{}'.format(key.replace('_', '-')))
    
def p(string):
    return '({0})'.format(string)

def q(string):
    return '"{0}"'.format(string)

def Q(string):
    return "'{0}'".format(string)

def natural(string):
    return [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', string)]

def natsort(stringlist):
    return sorted(stringlist, key=natural)

def lowalnum(keystr):
    return ''.join(c.lower() for c in keystr if c.isalnum())

def deepjoin(a, i):
    return next(i).join(x if isinstance(x, str) else deepjoin(x, i) if hasattr(x, '__iter__') else str(x) for x in a if x)

def join_args(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), **kwargs)
    return wrapper

def join_allargs(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), ', '.join(key + ' ' + value for key, value in kwargs.items()))
    return wrapper

def catch_keyboard_interrupt(f):
    def wrapper(*args, **kwargs):
        try: return f(*args, **kwargs)
        except KeyboardInterrupt:
            raise SystemExit(colors.red + 'Interrumpido por el usuario' + colors.default)
    return wrapper

def override_function(cls):
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return getattr(cls, f.__name__)(*args, **kwargs)
            except AttributeError:
                return f(*args, **kwargs)
        return wrapper
    return decorator

def removeprefix(self, prefix):
    if self.startswith(prefix):
        return self[len(prefix):]
    else:
        return self[:]

def removesuffix(self, suffix):
    # suffix='' should not call self[:-0].
    if suffix and self.endswith(suffix):
        return self[:-len(suffix)]
    else:
        return self[:]

