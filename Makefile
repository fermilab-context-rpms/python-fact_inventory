current_dir:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
version:=$(shell git describe --tags --abbrev=0 2>/dev/null || grep -m 1 'version = ' pyproject.toml | sed 's/.*version = "//' | sed 's/".*//')
name:=fact-inventory

_default:
	@echo "Perhaps you want:"
	@echo "make sources   - Create source tarball for koji"
	@echo "make srpm      - Build source RPM locally"
	@echo "make rpm       - Build binary RPM locally"

sources:
	@echo "Creating source tarball for koji"
	@tmpdir=$$(mktemp -d); \
	set -e; \
	git archive --format=tar --prefix=$(name)-$(version)/ HEAD > "$$tmpdir/src.tar"; \
	gzip --best -c "$$tmpdir/src.tar" > "$(current_dir)/$(name)-$(version).tar.gz"; \
	rm -rf "$$tmpdir"

srpm: sources
	@echo "Building source RPM"
	rpmbuild -bs --define '_sourcedir $(current_dir)' --define '_srcrpmdir $(current_dir)/SRPMS' $(name).spec

rpm: sources
	@echo "Building binary RPM"
	rpmbuild -bb --define '_rpmdir $(current_dir)/RPMS' --define '_builddir $(current_dir)/BUILD' --define '_sourcedir $(current_dir)' $(name).spec

.PHONY: _default sources srpm rpm
