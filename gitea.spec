%undefine _debugsource_packages
#define pre rc2

Name:		gitea
Version:	1.25.5
Release:	2
Summary:	Git with a cup of tea, painless self-hosted git service
License:	MIT
Group:		Development/Other
Url:		https://gitea.io/

# https://github.com/go-gitea/gitea
Source0:	https://github.com/go-gitea/gitea/releases/download/v%{version}/gitea-src-%{version}.tar.gz

Source10:	gitea.service
Source11:	gitea.service.d.conf
Source12:	app.ini

Source15:	gitea.redis

Requires:	git-core

BuildRequires:	golang make
BuildRequires:	pam-devel
BuildRequires:	pkgconfig(sqlite3)
BuildRequires:	nodejs

# Only in our default config
Requires:	redis
Requires:	postgresql-server
Requires(post):	postgresql-server openssl

%description
The goal of this project is to make the easiest, fastest, and most painless way
of setting up a self-hosted Git service. It is similar to GitHub, Bitbucket,
and Gitlab. Gitea is a fork of Gogs.

%prep
%autosetup -p1 -n %{name}-src-%{version}

%build
%make_build frontend
TAGS="bindata sqlite sqlite_unlock_notify pam" make VERSION=%version build

%install
mkdir -p %buildroot/srv/%{name}
mkdir -p %buildroot%{_localstatedir}/log/%{name}
mkdir -p %buildroot%{_datadir}/%{name}/conf
install -Dm 0600 %{S:12} %buildroot%{_datadir}/%{name}/conf
install -Dm 0755 %name %buildroot%{_bindir}/%{name}
install -Dm 0640 %{S:10} %buildroot%{_unitdir}/%{name}.service
mkdir -p %buildroot%{_sysconfdir}/systemd/system/gitea.service.d
install -Dm 0640 %{S:11} %buildroot%{_sysconfdir}/systemd/system/gitea.service.d/port.conf
mkdir -p %buildroot%{_sysconfdir}/%{name}
touch %buildroot%{_sysconfdir}/%{name}/app.ini

# install docs
mkdir -p %buildroot%_docdir/%name
install -Dm 0644 "custom/conf/app.example.ini" \
	%buildroot%_docdir/%name/app.ini.example

mkdir -p %{buildroot}%{_sysusersdir}
cat >%{buildroot}%{_sysusersdir}/%{name}.conf <<'EOF'
g %{name} - -
u %{name} - "gitea server" /srv/gitea /sbin/nologin
EOF

mkdir -p %{buildroot}%{_sysconfdir}/redis
install -c -m 644 %{S:15} %{buildroot}%{_sysconfdir}/redis/gitea.conf

%post
if [[ "$1" -eq 1 ]]; then
	systemctl is-active postgresql &>/dev/null || systemctl start postgresql
	if ! runuser -u postgres -- psql -lqt |cut -d'|' -f1 |xargs echo |grep -qw gitea; then
		PG_PASSWORD="$(openssl rand -base64 30)"
		if [[ -n "${PG_PASSWORD}" ]]; then
			runuser -u postgres -- psql -c "CREATE USER gitea WITH PASSWORD '${PG_PASSWORD}';" &>/dev/null
			runuser -u postgres -- psql -c "CREATE DATABASE gitea WITH OWNER gitea;" &>/dev/null
			runuser -u postgres -- psql -d gitea -c "GRANT ALL ON SCHEMA public TO gitea;" &>/dev/null
			if [[ ! -e %{_sysconfdir}/%{name}/app.ini || ! -s %{_sysconfdir}/%{name}/app.ini ]]; then
				sed -e "s,@PG_PASSWORD@,${PG_PASSWORD}," %{_datadir}/%{name}/conf/app.ini >%{_sysconfdir}/%{name}/app.ini
			elif grep -q '^\[database\]$' %{_sysconfdir}/%{name}/app.ini; then
				if sed -n '/^\[database\]/,/^\[/p' %{_sysconfdir}/%{name}/app.ini | grep -q '^PASSWD[[:space:]]*='; then
					sed -i '/^\[database\]/,/^\[/ s/^PASSWD[[:space:]]*=.*/PASSWD = '"${PG_PASSWORD}"'/' %{_sysconfdir}/%{name}/app.ini
				else
					sed -i "/^\[database\]/aPASSWD = ${PG_PASSWORD}" %{_sysconfdir}/%{name}/app.ini
				fi
			else
				cat >>%{_sysconfdir}/%{name}/app.ini <<EOF
[database]
PASSWD = ${PG_PASSWORD}
EOF
			fi
			chown root:gitea %{_sysconfdir}/%{name}/app.ini
			chmod 0660 %{_sysconfdir}/%{name}/app.ini
		fi
	elif [[ ! -e %{_sysconfdir}/%{name}/app.ini || ! -s %{_sysconfdir}/%{name}/app.ini ]]; then
		cp %{_datadir}/%{name}/conf/app.ini %{_sysconfdir}/%{name}/app.ini
		cat >&2 <<EOF
Please set [database].PASSWORD to the password of your gitea postgres
database owner, replacing the @PG_PASSWORD@ placeholder.
EOF
	fi
fi

%files
%attr(6755,root,%name) %_bindir/%name
%dir %attr(0700,%name,%name) /srv/%name
%dir %attr(0700,%name,%name) %{_localstatedir}/log/%name
%dir %_sysconfdir/%name
%{_datadir}/%{name}
%config(noreplace) %attr(0660,root,%name) %verify(not md5 size mtime) %_sysconfdir/%name/app.ini
%config(noreplace) %attr(0660,root,%name) %_sysconfdir/systemd/system/gitea.service.d/port.conf
%config %{_sysconfdir}/redis/gitea.conf
%_unitdir/%name.service
%_docdir/%name/app.ini.example
%doc *.md
%{_sysusersdir}/*.conf
