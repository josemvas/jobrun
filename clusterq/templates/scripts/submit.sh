#!/bin/sh
export PYTHONPATH=$moduledir
export CONFIGPATH=$$(dirname "$$(readlink -f "$$0")")
export LD_LIBRARY_PATH=$libpath

if test -L "$$0"; then
    exec $python -m clusterq.main "$$(basename "$$0")" "$$@"
else
    exec $python -m clusterq.main "$$@"
fi
