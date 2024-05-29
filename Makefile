# Copyright 2016-2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

PYTHON2:=$(shell command -v python2 --version 2> /dev/null)
PYTHON3:=$(shell command -v python3 --version 2> /dev/null)
SHELL:=/bin/bash
VERSION:=1.1.7
BASENAME=ec2rl-$(VERSION)

ifdef PYTHON3
	PYTHON:=python3
	COVERAGE:=coverage3
else ifdef PYTHON2
	PYTHON:=python2
	COVERAGE:=coverage2
else
	$(error "Did not find required python3 or python2 executable!")
	exit 1
endif

python: prep pythonbase
	@echo "Creating ec2rl.tgz..."
	tar -czf ec2rl.tgz --exclude="python" -C /tmp $(BASENAME)
	sha256sum ec2rl.tgz > ec2rl.tgz.sha256
	cp ec2rl.tgz /tmp/$(BASENAME)/ec2rl.tgz
	@echo "Done!"

bundledpython: prep pythonbase
	@cp -ap python /tmp/$(BASENAME)
	@echo "Creating ec2rl-bundled.tgz..."
	tar -czf ec2rl-bundled.tgz -C /tmp $(BASENAME)
	sha256sum ec2rl-bundled.tgz > ec2rl-bundled.tgz.sha256
	@echo "Done!"

pythonandbundled: python bundledpython
pythonandbundlednightly: nightly nightlybundledpython
pythonandbundledandrpm: python bundledpython rpm
pythonandbundlednightlyandrpm: nightly nightlybundledpython nightlyrpm

pythonbase:
	@cd "$$(dirname "$(readlink -f "$0")")" || exit 1
	@mkdir /tmp/$(BASENAME)
	@cp -ap ec2rl /tmp/$(BASENAME)
	@cp -ap ec2rl.py /tmp/$(BASENAME)
	@cp -ap ec2rlcore /tmp/$(BASENAME)
	@cp -ap lib /tmp/$(BASENAME)
	@cp -ap mod.d /tmp/$(BASENAME)
	@cp -ap post.d /tmp/$(BASENAME)
	@cp -ap pre.d /tmp/$(BASENAME)
	@cp -ap docs /tmp/$(BASENAME)
	@cp -ap example_configs /tmp/$(BASENAME)
	@cp -ap example_modules /tmp/$(BASENAME)
	@cp -ap ssmdocs /tmp/$(BASENAME)
	@cp -ap functions.bash /tmp/$(BASENAME)
	@cp -ap README.md /tmp/$(BASENAME)
	@cp -ap requirements.txt /tmp/$(BASENAME)
	@cp -ap LICENSE /tmp/$(BASENAME)
	@cp -ap NOTICE /tmp/$(BASENAME)

nightly: python
	mv ec2rl.tgz ec2rl-nightly.tgz
	mv ec2rl.tgz.sha256 ec2rl-nightly.tgz.sha256
	sed -i 's/ec2rl.tgz/ec2rl-nightly.tgz/' ec2rl-nightly.tgz.sha256
	cp ec2rl-nightly.tgz /tmp/$(BASENAME)/ec2rl-nightly.tgz


nightlybundledpython: bundledpython
	mv ec2rl-bundled.tgz ec2rl-bundled-nightly.tgz
	mv ec2rl-bundled.tgz.sha256 ec2rl-bundled-nightly.tgz.sha256
	sed -i 's/ec2rl-bundled.tgz/ec2rl-bundled-nightly.tgz/' ec2rl-bundled-nightly.tgz.sha256

menuconfig:
	@cd "$$(dirname "$(readlink -f "$0")")" || exit 1
	@if [ -d ec2rlcore/__pycache__/ ] ; then		\
		rm -rf ec2rlcore/__pycache__/;				\
	fi;												\
	if [ -e debug.log ] ; then						\
		rm debug.log;								\
	fi;												\
	./ec2rl menu-config --debug

prep:
	rm -rf bin
	rm -rf dist
	rm -rf build
	rm -rf rpmbuild/noarch
	rm -f rpmbuild/*.rpm
	rm -f ec2rl.spec
	rm -rf /tmp/$(BASENAME)

clean: prep
	rm -f ec2rl.tgz
	rm -f ec2rl.tgz.sha256
	rm -f ec2rl-bundled.tgz
	rm -f ec2rl-bundled.tgz.sha256
	rm -f ec2rl-nightly.tgz
	rm -f ec2rl-nightly.tgz.sha256
	rm -f ec2rl-bundled-nightly.tgz
	rm -f ec2rl-bundled-nightly.tgz.sha256

rpm: prep python
	@cd "$$(dirname "$(readlink -f "$0")")" || exit 1
	@echo "Building RPM..."
	mkdir -p ~/rpmbuild/SOURCES
	mv /tmp/$(BASENAME)/ec2rl.tgz ~/rpmbuild/SOURCES/ec2rl.tgz
	@rpmbuild -bb --clean --quiet rpmbuild/ec2rl.spec
	mv rpmbuild/noarch/ec2rl-*.noarch.rpm ec2rl.rpm
	sha256sum ec2rl.rpm > ec2rl.rpm.sha256
	@rm -rf rpmbuild/noarch/
	@echo "Done!"

nightlyrpm: prep python
	@cd "$$(dirname "$(readlink -f "$0")")" || exit 1
	@echo "Building RPM..."
	mv /tmp/$(BASENAME)/ec2rl-nightly.tgz ec2rl-nightly-$(VERSION).tgz
	@rpmbuild -bb --clean --quiet rpmbuild/ec2rl-nightly.spec
	mv rpmbuild/noarch/ec2rl-*.noarch.rpm ec2rl-nightly.rpm
	sha256sum ec2rl-nightly.rpm > ec2rl-nightly.rpm.sha256
	@rm -rf rpmbuild/noarch/
	@echo "Done!"

.PHONY: test
test:
	$(COVERAGE) run --source=ec2rlcore --branch -m unittest discover
	$(COVERAGE) report -m

yaml2py:
	$(PYTHON) tools/moduletests/yaml2py.py; \

test_modules_unit:
	@cd tools; \
	$(PYTHON) run_module_unit_tests.py; \

test_modules_functional:
	@cd tools; \
	$(PYTHON) run_module_functional_tests.py; \
