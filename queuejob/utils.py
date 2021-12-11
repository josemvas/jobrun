import os
import re
import sys
import string
from collections import OrderedDict

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

# This class is used to access dict values specifying keys as attributes
class AttrDict(OrderedDict):
    def __getattr__(self, name):
        if not name.startswith('_'):
            return self[name]
        super(AttrDict, self).__getattr__(name)
    def __setattr__(self, name, value):
        if not name.startswith('_'):
            self[name] = value
        else:
            super(AttrDict, self).__setattr__(name, value)

# This class is used to interpolate format strings with default values for missing keys
class DefaultDict(dict):
    def __init__(self, default):
        self._default = default
    def __missing__(self, key):
        return self._default

# This class is used to interpolate format strings without raising key errors
# Missing keys are logged in the missing_keys attribute
class FormatDict(dict):
    def __init__(self, known={}):
        self.missing_keys = []
        self.update(known)
    def __missing__(self, key):
        self.missing_keys.append(key)
        return '{' + key + '}'

class _(string.Template):
    def __str__(self):
        return(self.safe_substitute())

def interpolate(template, anchor, keylist=[], keydict={}):
    class DictTemplate(string.Template):
        delimiter = anchor
        idpattern = r'[a-z][a-z0-9]*'
    class ListTemplate(string.Template):
        delimiter = anchor
        idpattern = r'[0-9]+'
    class DualTemplate(string.Template):
        delimiter = anchor
        idpattern = r'([0-9]+|[a-z][a-z0-9]*)'
    if isinstance(keylist, (tuple, list)):
        if isinstance(keydict, dict):
            return DualTemplate(template).substitute(FormatDict()).format('', *keylist, **keydict)
        elif keydict is None:
            return ListTemplate(template).substitute(FormatDict()).format('', *keylist)
    elif keylist is None:
        if isinstance(keydict, dict):
            return DictTemplate(template).substitute(FormatDict()).format(**keydict)
        elif keydict is None:
            return None
    raise TypeError()

def deepjoin(nestedlist, nextseparators, pastseparators=[]):
    itemlist = []
    separator = nextseparators.pop(0)
    for item in nestedlist:
        if isinstance(item, (list, tuple)):
            itemlist.append(deepjoin(item, nextseparators, pastseparators + [separator]))
        elif isinstance(item, str):
            for delim in pastseparators:
                if delim in item:
                    raise ValueError('Components can not contain higher level separators')
            itemlist.append(item)
        else:
            raise TypeError('Components must be strings')
    return separator.join(itemlist)

def join_args(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), **kwargs)
    return wrapper

def join_args_and_kwargs(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), ', '.join('{}={}'.format(k, v) for k, v in kwargs.items()))
    return wrapper

def catch_keyboard_interrupt(message):
    def decorator(f):
        def wrapper(*args, **kwargs):
            try: return f(*args, **kwargs)
            except KeyboardInterrupt:
                raise SystemExit(message)
        return wrapper

def natsorted(*args, **kwargs):
    if 'key' not in kwargs:
        kwargs['key'] = lambda x: [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', x)]
    return sorted(*args, **kwargs)

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

