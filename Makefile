# Copyright 2015-2018 Chicharreros (https://launchpad.net/~chicharreros)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  http://launchpad.net/magicicada-protocol

ENV = $(CURDIR)/.env
SRC_DIR = $(CURDIR)/ubuntuone
PATH := $(ENV)/bin:$(PATH)
PYTHON = $(ENV)/bin/python
PYTHONPATH := $(ENV)/lib/python2.7:$(ENV)/lib/python2.7/site-packages:$(SRC_DIR):$(PYTHONPATH)

# use protobuf cpp
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=cpp
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=2

export PATH
export PYTHONPATH

$(ENV): $(ENV)/bin/activate

# only runs when requirements.txt or requirements-devel.txt changes
$(ENV)/bin/activate: requirements.txt requirements-devel.txt
	test -d $(ENV) || virtualenv $(ENV)
	$(ENV)/bin/pip install -Ur requirements.txt
	$(ENV)/bin/pip install -Ur requirements-devel.txt
	touch $(ENV)/bin/activate

bootstrap: build

build: $(ENV)
	$(PYTHON) setup.py build

bdist: build
	$(PYTHON) setup.py bdist_wheel

upload: bdist
	$(ENV)/bin/twine upload dist/*.whl

test: lint
	SSL_CERTIFICATES_DIR=ubuntuone/storageprotocol/tests/certs PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python $(ENV)/bin/trial ubuntuone

clean:
	$(PYTHON) setup.py clean
	find -name '*.pyc' -delete
	rm -rf build dist sdist _trial_temp ubuntuone_storageprotocol.egg-info

lint: $(ENV)
	$(ENV)/bin/flake8 --filename='*.py' --exclude='$(ENV),*_pb2.py,build'

.PHONY: build bdist upload test lint
