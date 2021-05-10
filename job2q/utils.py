import os
import re
import sys
import string
from . import colors

booldict = {
    'True' : True,
    'False' : False
}

class FormatKeyError(Exception):
    pass

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

class DefaultDict(dict):
    def __init__(self, default=None):
        self._keys = []
        self._default = default
    def __missing__(self, key):
        self._keys.append(key)
        if self._default is None:
            return '{' + key + '}'
        else:
            return self._default

class _(string.Template):
    def __str__(self):
        return(self.safe_substitute())
    def format(self, **keys):
        return self.safe_substitute(keys)

def interpolate(template, delimiter, keylist=[], keydict={}):
    class DictTemplate(string.Template):
        delim = delimiter
        idpattern = r'[a-z][a-z0-9]*'
    class ListTemplate(string.Template):
        delim = delimiter
        idpattern = r'[0-9]+'
    class DualTemplate(string.Template):
        delim = delimiter
        idpattern = r'([0-9]+|[a-z][a-z0-9]*)'
    if isinstance(keylist, (tuple, list)):
        if isinstance(keydict, dict):
            return DualTemplate(template).substitute(DefaultDict()).format('', *keylist, **keydict)
        elif keydict is None:
            return ListTemplate(template).substitute(DefaultDict()).format('', *keylist)
    elif keylist is None:
        if isinstance(keydict, dict):
            return DictTemplate(template).substitute(DefaultDict()).format(**keydict)
        elif keydict is None:
            return None
    raise TypeError()

def expandvars(template, keydict):
    try:
        return template.format(**keydict)
    except KeyError():
        raise FormatKeyError()

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
        return f(' '.join(args), ', '.join('{}={}'.format(k, v) for k, v in kwargs.items()))
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

def printoptions(options, defaults=[], level=0):
    for opt in sorted(options, key=natkey):
        if defaults and opt == defaults[0]:
            print(' '*level + opt + '  (default)')
        else:
            print(' '*level + opt)
        if isinstance(options, dict):
            printoptions(options[opt], defaults[1:], level + 1)

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

