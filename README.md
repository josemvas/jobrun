ClusterQ
========

About
-----

**ClusterQ** is a extensible python library and command line tool to submit simulation jobs to HPC clusters. It is compatible with PBS, LSF and Slurm and currently supports the following simulation packages:

* Autodock
* deMon2k
* DFTB+
* Gaussian
* ORCA
* VASP

Installation
------------

Clone the repository:

```
git clone https://github.com/josemvas/clusterq.git
```

then enter the clusterq directory and install system wide with pip:

```
pip3 install .
```

For single user installations add the `--user` option.

Setup
-----

Run:

```
clusterq setup
```

and follow the instructions printed on the screen. For system wide installations the config and bin directories will typically be /usr/local/etc/clusterq and /etc/bin respectively, for single user installations they will be ~/.local/etc/clusterq and ~/.local/bin.

Upgrade
-------

Enter the clusterq directory and update the repository:

```
git pull
```

and upgrade system wide with pip:

```
pip install --upgrade .
```

For single user installations add the `--user` option.
