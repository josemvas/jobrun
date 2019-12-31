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

consoleScript = '''
#!/opt/anaconda/bin/python
import sys
sys.path = {syspath}
from job2q import config
config.specdir = '{specdir}'
from job2q import getconf
while getconf.inputlist:
    try:
        if 'job2q.submit' in sys.modules:
            sleep(getconf.waitime)
            reload(job2q.submit)
        else:
            from job2q import submit
    except KeyboardInterrupt:
        dialogs.error('Cancelado por el usario')
    except RuntimeError:
        pass
'''

