Name:		python-fact_inventory
Version:	0.0.6
Release:	1%{?dist}

License:	AGPL-3.0-or-later

URL:		https://github.com/fermitools/python-fact_inventory
Source0:	%{url}/archive/%{version}/%{name}-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	redhat-rpm-config
BuildRequires:	ansible-core
BuildRequires:	sed

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
# Extract playbook documentation from gather.yml
sed -n '/===BEGIN_PLAYBOOK_DOC===/,/===END_PLAYBOOK_DOC===/p' gather.yml | \
  sed -e '/===.*===$/d' -e 's/^# //' -e 's/^#$//' > docs/gather.yml.txt

# Verify extraction succeeded (ensure delimiters were found)
if [ ! -s docs/gather.yml.txt ]; then
    echo "ERROR: Failed to extract documentation (delimiters not found in gather.yml)" >&2
    exit 1
fi


%install
install -m 0755 -d %{buildroot}%{_datarootdir}/fact-inventory-gather
install -m 0644 gather.yml %{buildroot}%{_datarootdir}/fact-inventory-gather/


%check
ansible-playbook --syntax-check gather.yml


%files -n fact-inventory-gather
%license LICENSE
%doc docs/gather.yml.txt
%{_datarootdir}/fact-inventory-gather/gather.yml

%changelog
* Fri Jul 31 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.6
- Move playbook to /usr/share following rpm review
- Add simple doc

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
