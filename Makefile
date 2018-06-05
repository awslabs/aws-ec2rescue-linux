# Copyright 2016-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
VERSION:=1.1.3
BASENAME=ec2rl-$(VERSION)

ifdef PYTHON3
	PYTHON:=python3
	COVERAGE:=coverage3
else ifdef PYTHON2
	PYTHON:=python2
	COVERAGE:=coverage2
else:
	$(error "Did not find required python3 or python2 executable!")
	exit 1
endif

python: prep
	@cd "$$(dirname "$(readlink -f "$0")")" || exit 1
	rm -f $(BASENAME).tgz
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
	@echo "Creating ec2rl.tgz..."
	@tar -czf ec2rl.tgz -C /tmp $(BASENAME)
	@sha256sum ec2rl.tgz > ec2rl.tgz.sha256
	@rm -rf /tmp/$(BASENAME)
	@echo "Done!"

binary: prep
	@cd "$$(dirname "$(readlink -f "$0")")" || exit 1
	rm -f ec2rl-binary.tgz
	$(PYTHON) make_bin_modules.py
	@pyinstaller -y \
	-p lib \
	--add-data "functions.bash:." \
	--add-data "LICENSE:." \
	--add-data "NOTICE:." \
	--add-data "README.md:." \
	--add-data "ec2rlcore/help.yaml:ec2rlcore/" \
	--add-data "bin:bin" \
	--add-data "docs:docs" \
	--add-data "example_configs:example_configs" \
	--add-data "example_modules:example_modules" \
	--add-data "ssmdocs:ssmdocs" \
	--add-data "pre.d:pre.d" \
	--add-data "mod.d:mod.d" \
	--add-data "post.d:post.d" \
	--add-data "lib/requests/cacert.pem:requests" \
	--hidden-import botocore \
	ec2rl.py

	$(PYTHON) make_symlinks.py

	@# Build the one-directory binary tarball
	mv dist/ec2rl dist/$(BASENAME)
	@echo "Creating ec2rl-binary.tgz ..."
	@tar -czf ec2rl-binary.tgz -C dist $(BASENAME)
	@sha256sum ec2rl-binary.tgz > ec2rl-binary.tgz.sha256
	@echo "Done!"


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
	rm -rf dist
	rm -rf build
	rm -rf rpmbuild/noarch
	rm -f rpmbuild/*.rpm
	rm -f ec2rl.spec
	rm -rf /tmp/ec2rl
	rm -rf /tmp/$(BASENAME)

clean: prep
	rm -f ec2rl.tgz
	rm -f ec2rl.tgz.sha256
	rm -f ec2rl-binary.tgz
	rm -f ec2rl-binary.tgz.sha256

all: python binary

rpm: prep python
	@cd "$$(dirname "$(readlink -f "$0")")" || exit 1
	@echo "Building RPM..."
	@rpmbuild -bb --clean --quiet rpmbuild/ec2rl.spec
	mv rpmbuild/noarch/$(BASENAME)-*.noarch.rpm rpmbuild/
	@rm -rf rpmbuild/noarch/
	@echo "Done!"

.PHONY: test
test:
	$(COVERAGE) run --source=ec2rlcore --branch -m unittest discover
	$(COVERAGE) report -m

test_modules_unit:
	@cd tools; \
	$(PYTHON) run_module_unit_tests.py; \

test_modules_functional:
	@cd tools; \
	$(PYTHON) run_module_functional_tests.py; \
