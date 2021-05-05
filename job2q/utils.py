# -*- coding: utf-8 -*-
import os
import re
import sys
import string
from . import colors

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

class _(string.Template):
    def __str__(self):
        return(self.safe_substitute())
    def format(self, **keys):
        return self.safe_substitute(keys)

class DefaultStr(str):
    pass

def substitute(template, delim='%', keylist=[], keydict={}):
    class A(string.Template):
        delimiter = delim
        idpattern = r'[a-z][_a-z0-9]*'
    class B(string.Template):
        delimiter = delim
        idpattern = r'[1-9]'
    try:
        return A(template).substitute(keydict)
    except ValueError:
        return B(template).substitute({str(i):v for i,v in enumerate(keylist, 1)})

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

def natkey(string):
    return [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', string)]

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

def printtree(tree, level=0):
    if isinstance(tree, (list, dict)):
        for branch in natsort(tree):
            if isinstance(branch, DefaultStr):
                print(' '*2*level + branch + ' '*3 + '(default)')
            elif isinstance(branch, str):
                print(' '*2*level + branch)
            else:
                raise SystemExit(colors.red + 'Tree elements must be str or DefaultStr type' + colors.default)
            printtree(branch, level + 1)

def getformatkeys(formatstr):
    return [i[1] for i in string.Formatter().parse(formatstr) if i[1] is not None]
