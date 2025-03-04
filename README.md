JobQ
====

About
-----
**JobQ** is a configurable tool to submit simulation jobs to HPC clusters. It is compatible with PBS, LSF and Slurm and currently supports the following simulation software:

* DFTB+
* Gaussian
* deMon2k
* ORCA
* VASP

Install
-------
Install from GitHub with pip
```
pip3 install --user git+https://github.com/josemvas/jobq.git
```

Configure
---------
After installing run
```
jobq-config setup
```
and follow the instructions printed on the screen.

Upgrade
-------
Upgrade from GitHub with pip
```
pip3 install --user --upgrade git+https://github.com/josemvas/jobq.git
```

Notes
-----
For system wide installation drop the `--user` option.
