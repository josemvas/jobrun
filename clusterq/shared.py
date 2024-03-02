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
        self.__dict__['flags'] = set()
        self.__dict__['options'] = dict()
        self.__dict__['multoptions'] = dict()
    def gather(self, options):
        if isinstance(options, AttrDict):
            for key, value in options.items():
                if value is False:
                    pass
                elif value is True:
                    self.__dict__['flags'].add(key)
                elif isinstance(value, (int, float, str)):
                    self.__dict__['options'].update({key:value})
                elif isinstance(value, list):
                    self.__dict__['multoptions'].update({key:value})
                else:
                    raise ValueError()
    def __repr__(self):
        return repr(self.__dict__)

wrappers = (
    'openmpi',
    'intelmpi',
    'mpich',
)

config = SpecDict({
    'load': [],
    'source': [],
    'export': {},
    'versions': {},
    'defaults': {'parametervars': {}},
    'parameterpaths': [],
    'onscript': [],
    'offscript': [],
    'conflicts': {},
    'filekeys': {},
    'filevars': {},
    'fileoptions': {},
    'inputfiles': [],
    'outputfiles': [],
    'interpolable': [],
    'interpolationvars': [],
    'parametervars': [],
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
paths.lock = paths.home / '.clusterqlock'
