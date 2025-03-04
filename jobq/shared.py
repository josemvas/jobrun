from os import path
from pwd import getpwnam
from grp import getgrgid
from getpass import getuser 
from socket import gethostname
from .utils import ConfDict
from .fileutils import AbsPath

config = ConfDict()
options = ConfDict()
parameterdict = {}
parameterpaths = []
interpolationdict = {}
script = ConfDict()
names = ConfDict()
nodes = ConfDict()
paths = ConfDict()
environ = ConfDict()
settings = ConfDict()
names.user = getuser()
names.host = gethostname()
paths.home = AbsPath(path.expanduser('~'))
paths.jobq = paths.home/'.jobq'
