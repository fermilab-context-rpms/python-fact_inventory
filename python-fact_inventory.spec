Name:		python-fact_inventory
Version:	0.1.0
Release:	1%{?dist}
BuildArch:	noarch

License:	AGPL-3.0-or-later

URL:		https://github.com/fermitools/python-fact_inventory
Source0:	%{url}/archive/%{version}/%{name}-%{version}.tar.gz

BuildRequires:	redhat-rpm-config
BuildRequires:  sed

BuildRequires:	ansible-packaging
%if 0%{?rhel} > 8
BuildRequires:  ansible-packaging-tests
%endif

Summary:  System fact inventory collection and storage
%description
Fact inventory system for collecting, storing, and managing host facts
across infrastructure.


%package -n ansible-collection-fermilab-fact_inventory
Summary:  Fact inventory compatible Ansible role
%description -n ansible-collection-fermilab-fact_inventory
Provides a fact-inventory compatible Ansible client role for
collecting system, package, and local facts from target hosts
and submitting them to the fact-inventory API.


%prep
%autosetup


%build

cd client/ansible_collections/fermilab/fact_inventory
sed -i -e 's/^version: 0.0.0$/version: %{version}/' galaxy.yml
%ansible_collection_build


%install

cd client/ansible_collections/fermilab/fact_inventory
%ansible_collection_install


%check

cd client/ansible_collections/fermilab/fact_inventory
%if 0%{?rhel} > 8
%ansible_test_unit
%endif


%files -n ansible-collection-fermilab-fact_inventory -f %{ansible_collection_filelist}
%license LICENSE
%doc client/ansible_collections/fermilab/fact_inventory/README.md


%changelog
* Thu Aug 20 2026 Pat Riehecky <riehecky@fnal.gov> - 0.1.0
- Initial package
