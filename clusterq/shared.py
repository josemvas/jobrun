from os import path
from pwd import getpwnam
from grp import getgrgid
from getpass import getuser 
from socket import gethostname
from .readspec import SpecDict
from .fileutils import AbsPath
from .utils import AttrDict

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

wrappers = (
    'openmpi',
    'intelmpi',
    'mpich',
)

configs = SpecDict({
    'load': [],
    'source': [],
    'export': {},
    'versions': {},
    'defaults': {'parameterkeys': {}},
    'parameterpaths': {},
    'onscript': [],
    'offscript': [],
})

iospecs = SpecDict({
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

names = AttrDict()
nodes = AttrDict()
paths = AttrDict()
environ = AttrDict()
options = AttrDict()
remoteargs = ArgGroups()
names.user = getuser()
names.host = gethostname()
names.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
paths.home = AbsPath(path.expanduser('~'))
paths.lock = paths.home / '.jobsubmit.lock'
