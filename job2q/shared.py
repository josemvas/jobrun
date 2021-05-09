# -*- coding: utf-8 -*-
import os
import re
from pwd import getpwnam
from grp import getgrgid
from string import Template
from getpass import getuser 
from socket import gethostname
from .readspec import SpecBunch
from .utils import Bunch, p, q, natkey
from .fileutils import AbsPath, pathjoin
from . import messages

class ArgList:
    def __init__(self, args):
        self.current = None
        if 'sort' in options.common:
            if options.common.sort == 'natural':
                self.args = sorted(args, key=natkey)
            elif options.common.sort == 'reverse':
                self.args = sorted(args, key=natkey, reverse=True)
        else:
            self.args = args
        if 'filter' in options.common:
            self.filter = re.compile(options.common.filter)
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
                if AbsPath(pathjoin(parentdir, (self.current, progspecs.shortname, key))).isfile():
                    inputname = pathjoin((self.current, progspecs.shortname))
                    break
            else:
                for key in progspecs.inputfiles:
                    if AbsPath(pathjoin(parentdir, (self.current, key))).isfile():
                        inputname = self.current
                        break
                else:
                    messages.failure('No hay archivos de entrada de', progspecs.longname, 'asociados al trabajo', self.current)
                    return next(self)
        else:
            path = AbsPath(self.current, cwd=options.common.cwd)
            parentdir = path.parent
            for key in progspecs.inputfiles:
                if path.name.endswith('.' + key):
                    inputname = path.name[:-len('.' + key)]
                    break
            else:
                messages.failure('La extensión del archivo de entrada', q(path.name), 'no está asociada a', progspecs.longname)
                return next(self)
            if not path.isfile():
                messages.failure(path.failreason)
                return next(self)
        filtermatch = self.filter.fullmatch(inputname)
        if filtermatch:
            self.groups = filtermatch.groups()
            return parentdir, inputname
        else:
            return next(self)

class ArgGroups:
    def __init__(self):
        self.__dict__['switches'] = set()
        self.__dict__['constants'] = dict()
        self.__dict__['lists'] = dict()
    def gather(self, options):
        if isinstance(options, Bunch):
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

names = Bunch()
paths = Bunch()
environ = Bunch()
options = Bunch()
sysconf = SpecBunch()
progspecs = SpecBunch()
queuespecs = SpecBunch()
remoteargs = ArgGroups()

names.user = getuser()
names.host = gethostname()
names.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
paths.home = os.path.expanduser('~')

