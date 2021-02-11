#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

version = __import__('rick_db').get_version()

# read the contents of README.md
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    description = f.read()

setup(
    name='rick',
    version=version,
    author="Joao Pinheiro",
    author_email="",
    url="https://github.com/oddbit-project/rick_db",
    description='SQL database layer',
    license='MIT',
    long_description=description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    long_description_content_type='text/markdown',
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    extras_require={},
    install_requires=[],
    zip_safe=False,
    tests_require=[
        "flake8>=2.1.0",
        "tox>=1.7.0",
        "codecov>=2.0.0",
        "pytest-cov>=2.8.1",
    ],
)
