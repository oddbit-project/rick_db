# Installation

The recommended instalation procedure is to use the available pip package. Make sure you have psycopg2 and setuptools
installed before proceeding.

## Required dependencies

RickDb requires the following dependencies:

- pytest
- psycopg2
- toml
- setuptools

Please note, most platforms have both psycopg2 and setuptools available as a separate, binary installed package.

Installing psycopg2 and setuptools in Ubuntu (>=18):
```shell
$ sudo apt install  python3-setuptools python3-psycopg2
```

## Installing from package

RickDb is available in [PyPi](https://pypi.org/project/rick-db/) as a package, an can easily be installed using pip:
```shell
$ pip install rick-db
```

## Installing from source

1. clone the repository to a folder:
```shell
$ git clone https://github.com/oddbit-project/rick_db.git
$ cd rick_db
rick_db$
```

2. install missing dependencies
```shell
rick_db$ pip install -r requirements.txt
```

3. run setuptools from the repository folder:
```shell
rick_db$ python3 setup.py install
```