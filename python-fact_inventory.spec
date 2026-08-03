Name:		python-fact_inventory
Version:	0.0.5
Release:	1%{?dist}

License:	AGPL-3.0-or-later

URL:		https://github.com/fermitools/python-fact_inventory
Source0:	%{url}/archive/%{version}/%{name}-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	redhat-rpm-config
BuildRequires:	ansible-packaging
BuildRequires:  ansible-packaging-tests

Summary:	System fact inventory collection and storage

%description
Fact inventory system for collecting, storing, and managing host facts
across infrastructure.


%package -n ansible-collection-fermilab-fact_inventory
Summary:	Fact inventory compatible Ansible role

%description -n ansible-collection-fermilab-fact_inventory
Provides a fact-inventory compatible Ansible agent role for
collecting system, package, and local facts from target hosts
and submitting them to the fact-inventory API.


%prep
%autosetup


%build

cd agent/ansible/fact_inventory
%ansible_collection_build



%install

cd agent/ansible/fact_inventory
%ansible_collection_install



%check
cd agent/ansible/fact_inventory
%ansible_test_unit


%files -n ansible-collection-fermilab-fact_inventory -f %{ansible_collection_filelist}
%license LICENSE
%doc agent/ansible/fact_inventory/README.md


%changelog
* Mon Aug 3 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.6
- Move to collection/role for ansible agent
- Add simple doc
- Make fact gathering a bit more flexible

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
