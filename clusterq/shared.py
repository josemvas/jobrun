import os
import re
from pwd import getpwnam
from grp import getgrgid
from getpass import getuser 
from socket import gethostname
from string import Template
from .readspec import SpecDict
from .utils import AttrDict, p, q, natsorted as sorted
from .fileutils import AbsPath, pathjoin
from . import messages

class ArgList:
    def __init__(self, args):
        self.current = None
        if options.arguments.sort:
            self.args = sorted(args)
        elif options.arguments.sort_reverse:
            self.args = sorted(args, reverse=True)
        else:
            self.args = args
        if 'filter' in options.arguments:
            self.filter = re.compile(options.arguments.filter)
        else:
            self.filter = re.compile('.+')
    def __iter__(self):
        return self
    def __next__(self):
        try:
            self.current = self.args.pop(0)
        except IndexError:
            raise StopIteration
        if options.common.jobargs:
            parentdir = AbsPath(options.common.cwd)
            for key in progspecs.inputfiles:
                if AbsPath(pathjoin(parentdir, (self.current, key))).isfile():
                    inputname = self.current
                    break
            else:
                messages.failure('No hay archivos de entrada de', progspecs.progname, 'asociados al trabajo', self.current)
                return next(self)
        else:
            path = AbsPath(self.current, cwd=options.common.cwd)
            parentdir = path.parent
            for key in progspecs.inputfiles:
                if path.name.endswith('.' + key):
                    inputname = path.name[:-len('.' + key)]
                    break
            else:
                messages.failure('La extensión del archivo de entrada', q(path.name), 'no está asociada a', progspecs.progname)
                return next(self)
            try:
                path.assertfile()
            except OSError as e:
                messages.excinfo(e, path)
                return next(self)
        matching = self.filter.fullmatch(inputname)
        if matching:
            return parentdir, inputname, matching.groups()
        else:
            return next(self)

class ArgGroups:
    def __init__(self):
        self.__dict__['switches'] = set()
        self.__dict__['constants'] = dict()
        self.__dict__['lists'] = dict()
    def gather(self, options):
        if isinstance(options, AttrDict):
            for key, value in options.items():
                if value is False:
                    pass
                elif value is True:
                    self.__dict__['switches'].add(key)
                elif isinstance(value, list):
                    self.__dict__['lists'].update({key:value})
                else:
                    self.__dict__['constants'].update({key:value})
    def __repr__(self):
        return repr(self.__dict__)

names = AttrDict()
nodes = AttrDict()
paths = AttrDict()
environ = AttrDict()
options = AttrDict()
options.parsed = AttrDict()

sysconf = SpecDict({
    'load': [],
    'source': [],
    'export': {},
    'versions': {},
    'defaults': {'parameterkeys': {}},
    'parameterpaths': {},
    'onscript': [],
    'offscript': [],
})

progspecs = SpecDict({
    'conflicts': {},
    'filekeys': {},
    'filevars': {},
    'fileoptions': {},
    'inputfiles': [],
    'outputfiles': [],
    'interpolable': [],
    'parametersets': [],
    'parameterkeys': [],
    'optargs': [],
    'posargs': [],
    'prescript': [],
    'postscript': [],
})

queuespecs = SpecDict()
remoteargs = ArgGroups()
names.user = getuser()
names.host = gethostname()
names.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
paths.home = AbsPath(os.path.expanduser('~'))
paths.lock = paths.home / '.jobsubmit.lock'

