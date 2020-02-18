# -*- coding: utf-8 -*-
import os
import re
from . import colors

class IdentityList(list):
    def __init__(self, *args):
        list.__init__(self, args)
    def __contains__(self, other):
        return any(o is other for o in self)

class Bunch(dict):
    def __getattr__(self, item):
        try: return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)
    def __setattr__(self, item, value):
            self.__setitem__(item, value)

def p(string):
    return '({0})'.format(string)

def q(string):
    return '"{0}"'.format(string)

def sq(string):
    return "'{0}'".format(string)

def natkey(string):
    return [ int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', string) ]

def natsort(stringlist):
    return sorted(stringlist, key=natkey)

def alnum(string): 
    return ''.join(c for c in string if c.isalnum())

def deepjoin(a, i):
    return next(i).join(x if isinstance(x, str) else deepjoin(x, i) if hasattr(x, '__iter__') else str(x) for x in a if x)

def join_arguments(seq):
    def decorator(f):
        def wrapper(*args, **kwargs):
            return f(deepjoin(args, iter(seq)), **kwargs)
        return wrapper
    return decorator

def catch_keyboard_interrupt(f):
    def wrapper(*args, **kwargs):
        try: return f(*args, **kwargs)
        except KeyboardInterrupt:
            raise SystemExit(colors.red + 'Cancelado por el usuario' + colors.default)
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

wordseps = (' ', '')
pathseps = (os.path.sep, '.')
boolstrs = {'True' : True, 'False' : False}

