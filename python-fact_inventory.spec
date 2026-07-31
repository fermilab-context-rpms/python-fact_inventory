Name:		python-fact_inventory
Version:	0.0.5
Release:	1%{?dist}

License:	AGPL-3.0-or-later

URL:		https://github.com/fermitools/python-fact_inventory
Source0:	%{url}/archive/%{version}/%{name}-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	redhat-rpm-config
BuildRequires:	ansible-core

Summary:	System fact inventory collection and storage

%description
Fact inventory system for collecting, storing, and managing host facts
across infrastructure.


%package -n fact-inventory-gather
Summary:	Fact inventory compatible Ansible agent
Requires:	ansible-core

%description -n fact-inventory-gather
Provides a fact-inventory compatible Ansible agent for
collecting system, package, and local facts from target hosts
and submitting them to the fact-inventory API.


%prep
%autosetup


%build


%install
install -m 0755 -d %{buildroot}%{_libexecdir}/fact-inventory-gather
install -m 0644 gather.yml %{buildroot}%{_libexecdir}/fact-inventory-gather/


%check
ansible-playbook --syntax-check gather.yml


%files -n fact-inventory-gather
%license LICENSE
%{_libexecdir}/fact-inventory-gather/gather.yml

%changelog
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
