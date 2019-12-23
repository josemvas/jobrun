# -*- coding: utf-8 -*-

import sys
assert sys.version_info >= (2, 7)
from setuptools import setup, find_packages

setup(
    name="job2q",
    version="0.0.1",
    description="A python package to readily submit jobs to Linux clusters",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    keywords = "cli cluster jobs",
    author="cronofugo",
    url="https://github.com/cronofugo/python-job2q",
    packages=find_packages(),
    #python_requires=">=2.7",
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: POSIX :: Linux",
    ],
    install_requires=[
        "future",
        "termcolor",
        "pyparsing",
    ],
    package_data={
        "job2q": [
            "strings/exec.py.str",
            "database/platform/*/hostspecs.xml",
            "database/generic/*/jobspecs.xml",
            "database/platform/*/*/jobspecs.xml",
        ],
    },
    entry_points={
        "console_scripts": [
            "job2q-setup=job2q.main:setup",
        ],
    },
)
