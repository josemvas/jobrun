# -*- coding: utf-8 -*-

import sys
assert sys.version_info >= (2, 7)

from setuptools import setup
from setuptools import find_packages

setup(
    name="job2q",
    version="0.0.1",
    author="José Manuel Vásquez",
    author_email="manuelvsqz@gmail.com",
    description="Submit any job to any queue",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    url="https://github.com/cronofugo/job2q",
    packages=find_packages(),
    package_data={
        "job2q": [
            "exec.py.str",
            "database/platform/*/hostspecs.xml",
            "database/generic/*/jobspecs.xml",
            "database/platform/*/*/jobspecs.xml",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=2.7",
    install_requires=[
        "future",
        "termcolor",
        "pyparsing",
        "bullet",
    ],
    entry_points={
        "console_scripts": [
            "job2q-setup=job2q.main:setup",
        ],
    },
)
