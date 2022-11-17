#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

# parse/exec version straight from file
# to avoid __init__.py and bootrsapping of unmet dependencies
version = {}
with open("rick_db/version.py") as fp:
    exec(fp.read(), version)

# read the contents of README.md
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    description = f.read()

setup(
    name='rick-db',
    version=version['__version__'],
    author="Joao Pinheiro",
    author_email="",
    url="https://github.com/oddbit-project/rick_db",
    description='SQL database layer',
    license='MIT',
    long_description=description,
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: SQL',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(),
    include_package_data=False,
    python_requires=">=3.8",
    extras_require={},
    install_requires=[
        "psycopg2>=2.9.2",
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'rickdb=rick_db.cli.manage:main',
        ],
    }
)
