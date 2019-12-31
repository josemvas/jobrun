# -*- coding: utf-8 -*-

specdir = None

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

