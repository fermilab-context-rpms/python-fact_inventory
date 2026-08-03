Name:		python-fact_inventory
Version:	0.0.6
Release:	2%{?dist}
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
Provides a fact-inventory compatible Ansible agent role for
collecting system, package, and local facts from target hosts
and submitting them to the fact-inventory API.


%prep
%autosetup


%build

cd agent/ansible_collections/fermilab/fact_inventory
sed -i -e 's/VERSION/%{version}/' galaxy.yml
%ansible_collection_build


%install

cd agent/ansible_collections/fermilab/fact_inventory
%ansible_collection_install


%check

cd agent/ansible_collections/fermilab/fact_inventory
%if 0%{?rhel} > 8
%ansible_test_unit
%endif


%files -n ansible-collection-fermilab-fact_inventory -f %{ansible_collection_filelist}
%license LICENSE
%doc agent/ansible_collections/fermilab/fact_inventory/README.md


%changelog
* Mon Aug 3 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.6-2
- Fix package name

* Mon Aug 3 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.6-1
- Move to collection/role for ansible agent

* Fri Jul 31 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.5
- Make audit log 0600 by default

* Fri Jul 31 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.4
- Simplify structure of audit log file

* Fri Jul 31 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.3
- Allow skipping of audit log directory

* Thu Jul 30 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.2
- Improve audit log from gather.yml

* Mon Jul 27 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.1
- Initial package
