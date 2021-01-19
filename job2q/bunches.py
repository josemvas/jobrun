# -*- coding: utf-8 -*-
from os import path
from getpass import getuser 
from pwd import getpwnam
from grp import getgrgid
from .utils import Bunch
from .specparse import SpecBunch

cluster = Bunch()
cluster.user = getuser()
cluster.home = path.expanduser('~')
cluster.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name

envars = Bunch()
options = Bunch()
jobspecs = SpecBunch()
keywords = {}
files = []

