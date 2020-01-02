# -*- coding: utf-8 -*-

xmlScriptTags = [
    'initscript',
    'offscript',
    'prescript',
    'postscript',
]
    
xmlListTags = [
    'profile',
    'inputfiles',
    'outputfiles',
    'positionargs',
]

xmlDictTags = [
    'defaults',
    'fileexts',
    'filevars',
    'optionargs',
    'parameters',
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

