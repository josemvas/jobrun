import sys
assert sys.version_info >= (3, 6)
from clusterq import console_scripts
try:
    console_scripts.clusterq_setup()
except KeyboardInterrupt:
    print('No se completó la instalación')
