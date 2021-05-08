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

class FormatDict(dict):
    def __init__(self):
        self._key = None
    def __getitem__(self, key):
        if self._key:
            raise KeyError('Too many keys')
        self._key = key
        return ''

class AlphaTpl(string.Template):
    delimiter = '%'
    idpattern = r'[a-z]*'

class NumTpl(string.Template):
    delimiter = '%'
    idpattern = r'[1-9]'

def substitute(template, keylist=[], keydict={}):
    try:
        return AlphaTpl(template).substitute(keydict)
    except ValueError:
        return NumTpl(template).substitute({str(i):v for i,v in enumerate(keylist, 1)})

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

def deepjoin(nestedlist, nextdelimiters, pastdelimiters=[]):
    itemlist = []
    delimiter = nextdelimiters.pop(0)
    for item in nestedlist:
        if isinstance(item, (list, tuple)):
            itemlist.append(deepjoin(item, nextdelimiters, pastdelimiters + [delimiter]))
        elif isinstance(item, str):
            for delim in pastdelimiters:
                if delim in item:
                    raise ValueError('Components can not contain upper delimiters')
            itemlist.append(item)
        else:
            raise TypeError('Components must be strings')
    return delimiter.join(itemlist)

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

def printree(tree, level=0):
    if isinstance(tree, dict):
        for branch in sorted(tree, key=natkey):
            print(' '*level + branch)
            printree(tree[branch], level + 1)

def getformatkeys(formatstr):
    return [i[1] for i in string.Formatter().parse(formatstr) if i[1] is not None]
