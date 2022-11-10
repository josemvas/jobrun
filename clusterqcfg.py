import sys
assert sys.version_info >= (3, 4)
from clusterq import console
try:
    console.configure()
except KeyboardInterrupt:
    print('No se completó la instalación')
