import os
import re
import sys
from string import Template, Formatter
from collections import OrderedDict

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
        super().__getattr__(name)
    def __setattr__(self, name, value):
        if not name.startswith('_'):
            self[name] = value
        else:
            super().__setattr__(name, value)

# This class is used to interpolate format strings without raising key errors
# Missing keys are logged in the missing_keys attribute
# Default value can be set at initiation
class DefaultDict(dict):
    def __init__(self, default=None):
        self.missing_keys = []
        self.__default__ = default
    def __missing__(self, key):
        self.missing_keys.append(key)
        return self.__default__

class ConfTemplate(Template):
    delimiter = '%'
    idpattern = r'[a-z][a-z0-9]*'

class GroupTemplate(Template):
    delimiter = '%'
    idpattern = r'[0-9]+'

class PrefixTemplate(Template):
    delimiter = '%'
    idpattern = r'[a-z0-9]+'

class _(Template):
    def __str__(self):
        return(self.safe_substitute())

def template_substitute(template, keydict, anchor):
    class InputTemplate(Template):
        delimiter = anchor
        idpattern = r'[a-z0-9]+'
    return InputTemplate(template).substitute(keydict)

def template_parse(template_str, s):
    """Match s against the given format string, return dict of matches.

    We assume all of the arguments in format string are named keyword arguments (i.e. no {} or
    {:0.2f}). We also assume that all chars are allowed in each keyword argument, so separators
    need to be present which aren't present in the keyword arguments (i.e. '{one}{two}' won't work
    reliably as a format string but '{one}-{two}' will if the hyphen isn't used in {one} or {two}).

    We raise if the format string does not match s.

    Example:
    fs = '{test}-{flight}-{go}'
    s = fs.format('first', 'second', 'third')
    template_parse(fs, s) -> {'test': 'first', 'flight': 'second', 'go': 'third'}
    """

    # First split on any keyword arguments, note that the names of keyword arguments will be in the
    # 1st, 3rd, ... positions in this list
    tokens = re.split(r'%([_a-z][_a-z0-9]*)', template_str, flags=re.IGNORECASE)
    keywords = tokens[1::2]

    # Now replace keyword arguments with named groups matching them. We also escape between keyword
    # arguments so we support meta-characters there. Re-join tokens to form our regexp pattern
    tokens[1::2] = map(u'(?P<{}>.*)'.format, keywords)
    tokens[0::2] = map(re.escape, tokens[0::2])
    pattern = ''.join(tokens)

    # Use our pattern to match the given string, raise if it doesn't match
    matches = re.match(pattern, s)
    if not matches:
        raise Exception("Format string did not match")

    # Return a dict with all of our keywords and their values
    return {x: matches.group(x) for x in keywords}

def format_parse(fmtstr, text):
    regexp = ''
    for lit, name, spec, conv in Formatter().parse(fmtstr):
        if name:
            regexp += lit + '(?P<{}>[_a-z0-9]+)'.format(name)
    match = re.fullmatch(regexp, text, re.IGNORECASE)
    return match.groupdict()

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

def print_tree(options, defaults=[], level=0):
    for opt in sorted(options):
        if defaults and opt == defaults[0]:
            print(' '*level + opt + '  (default)')
        else:
            print(' '*level + opt)
        if isinstance(options, dict):
            print_tree(options[opt], defaults[1:], level + 1)
