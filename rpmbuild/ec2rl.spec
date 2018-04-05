%define debug_package %{nil}

Name:           ec2rl
Version:	    1.1.2
Release:        1
Summary:        Automatic diagnostic tool for Linux

Group:          Diagnostics
License:        Apache 2
URL:            https://github.com/awslabs/aws-ec2rescue-linux
BuildArch:	    noarch
Source:         ec2rl.tgz
BuildRoot:	    %{_tmppath}/%name-root-%(%{__id_u} -n)

%description
A framework and collection of modules for diagnosing and resolving issues and collecting data.

%define _rpmdir %(pwd)/rpmbuild/
%define _sourcedir %(pwd)

%prep

%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/share/ec2rl
mkdir -p %{buildroot}/usr/bin
cp -R * %{buildroot}/usr/share/ec2rl/

%clean

%post
ln -s /usr/share/ec2rl/ec2rl /usr/bin/ec2rl

%postun
rm -rf /usr/bin/ec2rl

%files
/usr/share/ec2rl

%dir

%changelog
* Thur April 05 2018 Sean Poynter <seanpoyn@amazon.com - 1.1.2
 - Update EC2 Rescue for Linux to version 1.1.2
* Thur Feb 22 2018 Sean Poynter <seanpoyn@amazon.com - 1.1.1
 - Update EC2 Rescue for Linux to version 1.1.1
* Mon Jan 29 2018 Sean Poynter <seanpoyn@amazon.com - 1.1.0
 - Update EC2 Rescue for Linux to version 1.1.0
 - Set RPM build dir to rpmbuild
 - Remove extraneous output (pwd, ls)
* Tue Jul 18 2017 Greg Dunn <gregdunn@amazon.com - 1.0.0
 - Initial release
