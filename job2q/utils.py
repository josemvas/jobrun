# -*- coding: utf-8 -*-
import os
import re
import sys
from . import messages
from .decorators import join_positional_args, pathseps, wordseps, nothing

def makedirs(path):
    try: os.makedirs(path)
    except FileExistsError as e:
        pass

def remove(path):
    try: os.remove(path)
    except FileNotFoundError as e:
        pass

def rmdir(path):
    try: os.rmdir(path)
    except FileNotFoundError as e:
        pass

def hardlink(source, dest):
    try: os.link(source, dest)
    except FileExistsError as e:
        os.remove(dest)
        os.link(source, dest)
    except FileNotFoundError as e:
        pass

@join_positional_args(pathseps)
def pathjoin(path):
    return path

@join_positional_args(pathseps)
def isabspath(path):
    return os.path.isabs(os.path.expanduser(os.path.expandvars(path)))

@join_positional_args(pathseps)
def normalpath(path):
    return os.path.normpath(os.path.expanduser(os.path.expandvars(path)))

def realpath(path):
    return os.path.realpath(os.path.expanduser(os.path.expandvars(path)))

def p(string):
    return '({0})'.format(string)

def q(string):
    return '"{0}"'.format(string)

def sq(string):
    return "'{0}'".format(string)

def natsort(text):
    return [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', text)]

def alnum(string): 
    return ''.join(c for c in string if c.isalnum())
