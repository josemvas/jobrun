import re
import pyjson5 as json5
from clinterface import messages, _
from string import Template, Formatter

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

class MergeDict(AttrDict):
    def __init__(self, argdict):
        super().__init__()
        self.merge(argdict)
    def merge(self, other):
        for key, value in other.items():
            # Merge existing entry or add a new one
            if key in self and hasattr(self[key], 'merge'):
                self[key].merge(value)
            else:
                if isinstance(value, dict):
                    self[key] = MergeDict(value)
                elif isinstance(value, list):
                    self[key] = MergeList(value)
                else:
                    self[key] = value

class MergeList(list):
    def __init__(self, arglist):
        super().__init__()
        self.merge(arglist)
    def merge(self, other):
        for elem in other:
            if isinstance(elem, dict):
                self.append(MergeDict(elem))
            elif isinstance(elem, list):
                self.append(MergeList(elem))
            else:
                self.append(elem)

class GlobDict(dict):
    def __missing__(self, key):
        return '*'

class LogDict(dict):
# Missing keys are logged in the logged_keys attribute
    def __init__(self):
        self.logged_keys = []
    def __missing__(self, key):
        self.logged_keys.append(key)

class IdentityList(list):
    def __init__(self, *args):
        list.__init__(self, args)
    def __contains__(self, other):
        return any(o is other for o in self)

class ConfigTemplate(Template):
    delimiter = '&'
    idpattern = r'[a-z][a-z0-9_]*'

class FilterGroupTemplate(Template):
    delimiter = '%'
    idpattern = r'[a-z][a-z0-9_]*'

class InterpolationTemplate(Template):
    delimiter = '$'
    idpattern = r'[a-z][a-z0-9_]*'

class FormatKeyError(Exception):
    pass

def readspec(file):
    with open(file, 'r') as f:
        try:
            return json5.load(f)
        except ValueError as e:
            messages.error('El archivo $file contiene JSON inválido', str(e), file=f.name)

def natural_sorted(*args, **kwargs):
    if 'key' not in kwargs:
        kwargs['key'] = lambda x: [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', x)]
    return sorted(*args, **kwargs)

def option(key, value=None):
    if value is None:
        return('--{}'.format(key.replace('_', '-')))
    else:
        return('--{}="{}"'.format(key.replace('_', '-'), value))
    
def shq(string):
    if re.fullmatch(r'[a-z0-9_./-]+', string, flags=re.IGNORECASE):
        return string
    else:
        return f"'{string}'"

def print_tree(options, level=0):
    for opt in sorted(options):
        print(' '*level + opt)
        if isinstance(options, dict):
            print_tree(options[opt], defaults[1:], level + 1)

def catch_keyboard_interrupt(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except KeyboardInterrupt:
            messages.error(_('Interrumpido por el usuario'))
    return wrapper

def deep_join(nestedlist, nextseparators, pastseparators=[]):
# For example deep_join(['dir1', 'dir2', ['name', 'ext']], ['/', '.'])
# will return dir1/dir2/name.ext
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

def template_parse(template_str, s):
    """Match s against the given format string, return dict of matches.
    We assume all of the arguments in format string are named keyword arguments (i.e. no {} or
    {:0.2f}). We also assume that all chars are allowed in each keyword argument, so separators
    need to be present which aren't present in the keyword arguments (i.e. '{one}{two}' won't work
    reliably as a format string but '{one}-{two}' will if the hyphen isn't used in {one} or {two}).
    We raise if the format string does not match s. Example:
    fs = '{test}-{flight}-{go}'
    s = fs.format('first', 'second', 'third')
    template_parse(fs, s) -> {'test': 'first', 'flight': 'second', 'go': 'third'}
    """
    # First split on any keyword arguments, note that the names of keyword arguments will be in the
    # 1st, 3rd, ... positions in this list
    tokens = re.split(r'\$([a-z][a-z0-9_]*)', template_str, flags=re.IGNORECASE)
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
