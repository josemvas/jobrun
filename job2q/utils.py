# -*- coding: utf-8 -*-
import os
import re
import sys
import string
from . import colors

booldict = {
    'True' : True,
    'False' : False
}

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

class TestKeyDict(dict):
    def __init__(self):
        self._key = None
    def __getitem__(self, key):
        if self._key:
            raise KeyError('Too many keys')
        self._key = key
        return ''

class FormatKeyDict(dict):
    def __getitem__(self, key):
        return '{' + key + '}'

class DictTemplate(string.Template):
    delimiter = '%'
    idpattern = r'[a-z][a-z0-9]*'

class ListTemplate(string.Template):
    delimiter = '%'
    idpattern = r'[0-9]+'

class DualTemplate(string.Template):
    delimiter = '%'
    idpattern = r'[a-z0-9]+'

class _(string.Template):
    def __str__(self):
        return(self.safe_substitute())
    def format(self, **keys):
        return self.safe_substitute(keys)

def getformatkeys(formatstr):
    return [i[1] for i in string.Formatter().parse(formatstr) if i[1] is not None]

def interpolate(template, keylist=[], keydict={}):
    if isinstance(keylist, (tuple, list)):
        if isinstance(keydict, dict):
            return DualTemplate(template).substitute(FormatKeyDict()).format(*keylist, **keydict)
        elif keydict is None:
            return ListTemplate(template).substitute(FormatKeyDict()).format(*keylist)
    elif keylist is None:
        if isinstance(keydict, dict):
            return DictTemplate(template).substitute(FormatKeyDict()).format(**keydict)
        elif keydict is None:
            return None
    raise TypeError()

def deepjoin(nestedlist, nextdelimiters, pastdelimiters=[]):
    itemlist = []
    delimiter = nextdelimiters.pop(0)
    for item in nestedlist:
        if isinstance(item, (list, tuple)):
            itemlist.append(deepjoin(item, nextdelimiters, pastdelimiters + [delimiter]))
        elif isinstance(item, str):
            for delim in pastdelimiters:
                if delim in item:
                    raise ValueError('Components can not contain higher level delimiters')
            itemlist.append(item)
        else:
            raise TypeError('Components must be strings')
    return delimiter.join(itemlist)

def join_args(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), **kwargs)
    return wrapper

def join_args_and_kwargs(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), ', '.join('{}: {}'.format(k, v) for k, v in kwargs.items()))
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

def natkey(string):
    return [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', string)]

def lowalnum(keystr):
    return ''.join(c.lower() for c in keystr if c.isalnum())

def o(key, value=None):
    if value is not None:
        return('--{}={}'.format(key.replace('_', '-'), value))
    else:
        return('--{}'.format(key.replace('_', '-')))
    
def p(string):
    return '({})'.format(string)

def q(string):
    return '"{}"'.format(string)

def Q(string):
    return "'{}'".format(string)

