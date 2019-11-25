#!/opt/anaconda/bin/python
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jobToQueue",
    version="0.0.1",
    author="José Manuel Vásquez",
    author_email="manuelvsqz@gmail.com",
    description="A wrapper to submit jobs to OpenLava, Platform LSF or SLURM clusters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://example.com",
    packages=setuptools.find_packages(),
    package_data={
        "jobToQueue": [
            "database/platform/*/hostspecs.xml",
            "database/platform/*/*/syspecs.xml",
            "database/generic/*/jobspecs.xml",
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
        "bullet;python_version>='3.2'",
    ],
    entry_points={
        "console_scripts": [
            "j2q-setup=jobToQueue.main:setup",
        ],
    },
)
