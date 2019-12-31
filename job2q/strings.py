# -*- coding: utf-8 -*-

xmlScriptTags = [
    'initscript',
    'offscript',
    'prescript',
    'postscript',
]
    
xmlListTags = [
    'profile',
    'parameters',
    'inputfiles',
    'outputfiles',
    'positionargs',
    'initscript',
    'offscript',
    'prescript',
    'postscript',
]

xmlDictTags = [
    'defaults',
    'fileexts',
    'filevars',
    'optionargs',
    'versions',
] 

xmlTextTags = [
    'storage',
    'scheduler',
    'title',
    'runtype',
    'mpiwrapper',
    'outputdir',
    'versionprefix',
    'filecheck',
    'fileclash',
    'queue',
    'scratch',
    'waitime',
    'executable',
    'version',
    'stdout',
    'stderr',
]

xmlProfileChildren = {
    'export' : 'export',
    'source' : 'source',
    'load' : 'module load',
}

consoleScript = '''
#!{python}
import sys
sys.path = {syspath}
from job2q import main, config
config.specdir = '{specdir}'
main.run()
'''

