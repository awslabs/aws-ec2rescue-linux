%define debug_package %{nil}

Name:           ec2rl
Version:	1.0.0
Release:        1
Summary:        Automatic diagnostic tool for Linux

Group:          Diagnostics
License:        Apache 2
URL:            https://github.com/awslabs/aws-ec2rescue-linux
BuildArch:	noarch
Source:         ec2rl.tgz
BuildRoot:	%{_tmppath}/%name-root-%(%{__id_u} -n)

%description
A framework and collection of modules for diagnosing issues and collecting data.

%prep

%setup -q

%build
pwd
ls -alh

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
* Wed Jul 18 2017 Greg Dunn <gregdunn@amazon.com - 1.0.0
Initial release
