# -*- coding: utf-8 -*-
from os import getcwd
from . import messages
from .utils import natsort
from .readmol import readxyz, readmol
from .fileutils import AbsPath, NotAbsolutePath, diritems

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
            
def readcoords(molfile):
    if molfile.isfile():
        if molfile.hasext('.xyz'):
            return(readxyz(molfile))
        elif molfile.hasext('.mol'):
            return(readmol(molfile))
        else:
            messages.error('Solamente están soportados archivos de coordenadas en formato XYZ o MOL')
    elif molfile.isdir():
        messages.error('El archivo de coordenadas', molfile, 'es un directorio')
    elif molfile.exists():
        messages.error('El archivo de coordenadas', molfile, 'no es un archivo regular')
    else:
        messages.error('El archivo de coordenadas', molfile, 'no existe')

