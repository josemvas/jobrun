# -*- coding: utf-8 -*-
from os import getcwd
from . import messages
from .utils import natsort
from .fileutils import AbsPath, NotAbsolutePath, diritems
from .chemistry import readxyzfile, readmolfile

class NonMatchingFile(Exception):
    pass

class InputFileError(Exception):
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
            findparameters(rootpath.pathjoin(component.format()), components, defaults, indent)
        except IndexError:
            choices = diritems(rootpath, component)
            try:
                default = component.format(*defaults)
            except IndexError:
                default = None
            printchoices(choices=choices, default=default, indent=indent)
            for choice in choices:
                findparameters(rootpath.pathjoin(choice), components, defaults, indent + 1)
            
def readcoords(coordfile, keywords):
    coordfile = AbsPath(coordfile, cwdir=getcwd())
    molformat = '{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format
    if coordfile.isfile():
        if coordfile.hasext('.xyz'):
            for i, step in enumerate(readxyzfile(coordfile), 1):
                keywords['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
        elif coordfile.hasext('.mol'):
            for i, step in enumerate(readmolfile(coordfile), 1):
                keywords['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
        else:
            messages.opterror('Solamente están soportados archivos de coordenadas en formato XYZ o MOL')
    elif coordfile.isdir():
        messages.opterror('El archivo de coordenadas', coordfile, 'es un directorio')
    elif coordfile.exists():
        messages.opterror('El archivo de coordenadas', coordfile, 'no es un archivo regular')
    else:
        messages.opterror('El archivo de coordenadas', coordfile, 'no existe')
    keywords['file'] = coordfile
    return coordfile.stem

