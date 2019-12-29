# -*- coding: utf-8 -*-
from os import sep

# File path separators
fpsep =  sep + '.-'

lower = 'abcdefghijklmnopqrstuvwxyz'
upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
digit = '0123456789'
other = '._-'

XmlListTags = (
    'profile',
    'parameters',
    'inputfiles',
    'outputfiles',
    'positionargs',
    'initscript',
    'offscript',
    'prescript',
    'postscript',
)

XmlDictTags = (
    'versions',
    'fileexts',
    'filevars',
    'optionargs',
) 

XmlListChildren = {
    'export' : 'export',
    'source' : 'source',
    'load' : 'module load',
}

scriptTags = {
    'initscript',
    'offscript',
    'prescript',
    'postscript',
)
    

pyscript = '''
#!{python}
import sys
sys.path = {syspath}
from job2q import main
main.run('{hostspecs}', '{jobspecs}')
'''

