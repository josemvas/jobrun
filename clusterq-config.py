import sys
assert sys.version_info >= (3, 3)
from clusterq import console_scripts
try:
    console_scripts.clusterq_config()
except KeyboardInterrupt:
    print('No se completó la instalación')
