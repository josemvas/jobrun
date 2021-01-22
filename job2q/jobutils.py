# -*- coding: utf-8 -*-
from os import getcwd
from . import messages
from .utils import natsort
from .fileutils import AbsPath, NotAbsolutePath, diritems

class InputFileException(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

def printchoices(choices, indent=1, default=None):
    for choice in natsort(choices):
        if choice == default:
            print(' '*2*indent + choice + ' '*2 + '[default]')
        else:
            print(' '*2*indent + choice)

def findparameters(rootpath, components, defaults, indent):
    component = next(components, None)
    if component:
        try:
            findparameters(rootpath.joinpath(component.format()), components, defaults, indent)
        except IndexError:
            choices = diritems(rootpath, component)
            try:
                default = component.format(*defaults)
            except IndexError:
                default = None
            printchoices(choices=choices, default=default, indent=indent)
            for choice in choices:
                findparameters(rootpath.joinpath(choice), components, defaults, indent + 1)
            
