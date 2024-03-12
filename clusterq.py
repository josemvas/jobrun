import sys
assert sys.version_info >= (3, 6)
from clusterq import console_scripts
sys.argv.append('--in-place')
try:
    console_scripts.clusterq()
except KeyboardInterrupt:
    print('No se completó la instalación')
