# Installation

The recommended installation procedure is to use the available pip package.

## Required dependencies

RickDb requires the following dependencies:

- psycopg2
- toml
- setuptools

For ClickHouse support, install the optional `clickhouse-connect` dependency:

- clickhouse-connect

Please note, most platforms have both psycopg2 and setuptools available as a separate, binary installed package.

Installing psycopg2 and setuptools in Ubuntu:
```shell
$ sudo apt install python3-setuptools python3-psycopg2
```

## Installing from package

RickDb is available in [PyPi](https://pypi.org/project/rick-db/) as a package, and can easily be installed using pip:
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

2. install the package:
```shell
rick_db$ pip install .
```
