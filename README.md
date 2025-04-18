About
-----
**Jobrun** is a configurable tool to run simulation jobs in HPC clusters. It is compatible with PBS, LSF and Slurm and currently supports the following simulation software:

* DFTB+
* Gaussian
* deMon2k
* ORCA
* VASP

Install
-------
Install from GitHub with pip
```
pip3 install --user git+https://github.com/josemvas/jobrun.git
```

Configure
---------
After installing run
```
jobrun-cfg setup
```
and follow the instructions printed on the screen.

Upgrade
-------
Upgrade from GitHub with pip
```
pip3 install --user --upgrade git+https://github.com/josemvas/jobrun.git
```

Notes
-----
For system wide installation drop the `--user` option.
