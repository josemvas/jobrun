# -*- coding: utf-8 -*-
from os import sep

# File path separators
fpsep =  sep + '.-'

lower = 'abcdefghijklmnopqrstuvwxyz'
upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
digit = '0123456789'
other = '._-'

listTags = (
    'profile',
    'inputfiles',
    'outputfiles',
    'positionargs',
    'parameters',
    'prescript',
    'postscript',
    'initscript',
    'offscript',
)

dictTags = (
    'fileexts',
    'filevars',
    'optionargs',
    'versions',
) 

listChildren = {
    'export' : 'export',
    'source' : 'source',
    'load' : 'module load',
}

pyscript='''#!{python}
import sys
sys.path = {syspath}
from job2q import main
main.run('{hostspecs}', '{jobspecs}')
'''
