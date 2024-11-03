%undefine _debugsource_packages
#define pre rc2

Name:		gitea
Version:	1.22.3
Release:	1
Summary:	Git with a cup of tea, painless self-hosted git service
License:	MIT
Group:		Development/Other
Url:		https://gitea.io/

# https://github.com/go-gitea/gitea
Source0:	https://github.com/go-gitea/gitea/releases/download/v%{version}/gitea-src-%{version}.tar.gz
# Note latest tarballs from gihub gitea now contain the Go dependencies 
# so the package can be built from source
# Tarball containing go dependencies -- generated by (inside the source tree)
# running:
# export GOPATH=/tmp/.godeps
# go mod download
# cd /tmp
# tar cJf godeps-for-gitea-%{version}.tar.xz .godeps
#Source1:	godeps-for-gitea-%{version}.tar.xz

Source10:	gitea.service
Source11:	gitea.service.d.conf
Source12:	app.ini

Requires:	git-core

BuildRequires:	golang make
BuildRequires:	pam-devel
BuildRequires:	pkgconfig(sqlite3)
BuildRequires:	nodejs

%description
The goal of this project is to make the easiest, fastest, and most painless way
of setting up a self-hosted Git service. It is similar to GitHub, Bitbucket,
and Gitlab. Gitea is a fork of Gogs.

%prep
%autosetup -p1 -n %{name}-src-%{version}

%build
#export GOPATH="`pwd`/.godeps"
#export GOPROXY="file://`pwd`/.godeps"
#export NODE_OPTIONS=--openssl-legacy-provider

TAGS="bindata sqlite sqlite_unlock_notify pam" make VERSION=%version build

%install
mkdir -p %buildroot/srv/%{name}
mkdir -p %buildroot%{_localstatedir}/log/%{name}
install -Dm 0755 %name %buildroot%_bindir/%{name}
install -Dm 0640 %SOURCE10 %buildroot%_unitdir/%{name}.service
mkdir -p %buildroot%_sysconfdir/systemd/system/gitea.service.d
install -Dm 0640 %SOURCE11 %buildroot%_sysconfdir/systemd/system/gitea.service.d/port.conf
install -Dm 0660 %SOURCE12 %buildroot%_sysconfdir/%{name}/conf/app.ini

# install docs
mkdir -p %buildroot%_docdir/%name
install -Dm 0644 "custom/conf/app.example.ini" \
	%buildroot%_docdir/%name/default-app.ini

mkdir -p %{buildroot}%{_sysusersdir}
cat >%{buildroot}%{_sysusersdir}/%{name}.conf <<'EOF'
g %{name} - -
u %{name} - "gitea server" /srv/gitea /sbin/nologin
EOF

%files
%attr(6755,root,%name) %_bindir/%name
%dir %attr(0700,%name,%name) /srv/%name
%dir %attr(0700,%name,%name) %{_localstatedir}/log/%name
%dir %_sysconfdir/%name
%dir %_sysconfdir/%name/conf
%config(noreplace) %attr(0660,root,%name) %_sysconfdir/%name/conf/app.ini
%config(noreplace) %attr(0660,root,%name) %_sysconfdir/systemd/system/gitea.service.d/port.conf
%_unitdir/%name.service
%_docdir/%name/default-app.ini
%doc *.md
%{_sysusersdir}/*.conf
