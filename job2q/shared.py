# -*- coding: utf-8 -*-
import os
import re
from string import Template
from getpass import getuser 
from pwd import getpwnam
from grp import getgrgid
from . import messages
from .readspec import SpecBunch
from .utils import Bunch, p, q, natkey
from .fileutils import AbsPath, buildpath
from .parsing import BoolParser

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
        if options.common.base:
            basename = self.current
            rootdir = AbsPath(options.common.root)
        else:
            abspath = AbsPath(self.current, cwd=options.common.root)
            rootdir = abspath.parent()
            filename = abspath.name
            for key in jobspecs.infiles:
                if filename.endswith('.' + key):
                    basename = filename[:-len('.' + key)]
                    break
            else:
                messages.failure('La extensión del archivo de entrada', q(filename), 'no está asociada a', jobspecs.packagename)
                return next(self)
            #TODO: Move file checking to AbsPath class
            if not abspath.isfile():
                if not abspath.exists():
                    messages.failure('El archivo de entrada', abspath, 'no existe')
                elif abspath.isdir():
                    messages.failure('El archivo de entrada', abspath, 'es un directorio')
                else:
                    messages.failure('El archivo de entrada', abspath, 'no es un archivo regular')
                return next(self)
        filtermatch = self.filter.fullmatch(basename)
        #TODO: Make filtergroups available to other functions
        if filtermatch:
            filtergroups = filtermatch.groups()
        else:
            return next(self)
        filebools = {key: AbsPath(buildpath(rootdir, (basename, key))).isfile() or key in options.optionalfiles for key in jobspecs.filekeys}
        for conflict, message in jobspecs.conflicts.items():
            if BoolParser(conflict).evaluate(filebools):
                messages.error(message, p(basename))
                return next(self)
        return rootdir, basename


class OptDict:
    def __init__(self):
        self.__dict__['switch'] = set()
        self.__dict__['define'] = dict()
        self.__dict__['append'] = dict()
    def __setattr__(self, attr, attrval):
        self.__dict__[attr] = attrval
        if isinstance(attrval, Bunch):
            for key, value in attrval.items():
                if value is False:
                    pass
                elif value is True:
                    self.__dict__['switch'].add(key)
                elif isinstance(value, list):
                    self.__dict__['append'].update({key:value})
                else:
                    self.__dict__['define'].update({key:value})

names = Bunch()
names.user = getuser()
names.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name

options = OptDict()
hostspecs = SpecBunch()
jobspecs = SpecBunch()

