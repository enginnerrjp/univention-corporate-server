#!/bin/sh
#
# Univention Installer
#  debootstrap
#
# Copyright 2004-2011 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

. /tmp/installation_profile

architecture=`/bin/uname -m`

if [ -n "$cdrom_device" ]; then
	nfs=`echo $cdrom_device | grep "nfs:"`
	smbfs=`echo $cdrom_device | grep "smbfs:"`
	if [ -n "$nfs" ]; then
		/bin/mount -t nfs `echo $cdrom_device | sed -e 's|nfs:||'` /mnt
	elif [ -n "$smbfs" ]; then
		/bin/mount -t smbfs `echo $cdrom_device | sed -e 's|smbfs:||'` /mnt
	else
		/bin/mount -t iso9660 $cdrom_device /mnt
	fi
fi

## check for repository structure
# old repository (DVD)
if [ -d /mnt/packages ]; then
	repo_dir="file:/mnt/packages"
else
	version=`cat /mnt/.univention_install | grep VERSION | sed -e 's|VERSION=||'`

	repo_dir="file:/mnt/mirror/${version}/maintained/${version}-0/"
fi

if [ -n "$to_scan" ] || [ -n "$scan" ]; then
	for ts in $to_scan $scan; do
		if [ "$ts" = "hostname" ]; then
			ipcmd=`cat /proc/cmdline | grep ip | sed -e 's/.*ip=//g'`
			myip=`echo $ipcmd | awk -F ':' '{print $1}'`
			if [ -n "$nameserver1" ]; then
				host=`host $myip $nameserver1 |tail -1 | awk '{print $5}' | awk -F '.' '{print \$1}'`
			elif [ -n "$nameserver_1" ]; then
				host=`host $myip $nameserver_1 |tail -1 | awk '{print $5}' | awk -F '.' '{print \$1}'`
			fi
		fi
	done
fi

if [ -n "$host" ]; then
	hostname $host
fi

if [ -n "$hostname" ]; then
	hostname $hostname
fi

# Installing univention base system
if [ -z "$USE_NO_LOG" ]; then
	if [ "$architecture" = "powerpc" -o "$architecture" = "ppc64" ]; then
		debootstrap --arch powerpc --include="postfix" --exclude="pcmcia-cs libpcre3-udeb udev-udeb libc6-udeb rsyslog" univention /instmnt/ $repo_dir 2>&1 | tee -a /instmnt/.log
	elif [ "$architecture" = "x86_64" ]; then
		debootstrap --arch amd64 --include="postfix" --exclude="pcmcia-cs libpcre3-udeb udev-udeb libc6-udeb rsyslog" univention /instmnt/ $repo_dir 2>&1 | tee -a /instmnt/.log
	else
		debootstrap --arch i386 --include="postfix" --exclude="pcmcia-cs libpcre3-udeb udev-udeb libc6-udeb rsyslog" univention /instmnt/ $repo_dir 2>&1 | tee -a /instmnt/.log
	fi
else
	if [ "$architecture" = "powerpc" -o "$architecture" = "ppc64" ]; then
		debootstrap --arch powerpc --include="postfix" --exclude="pcmcia-cs libpcre3-udeb udev-udeb libc6-udeb rsyslog" univention /instmnt/ $repo_dir
	elif [ "$architecture" = "x86_64" ]; then
		debootstrap --arch amd64 --include="postfix" --exclude="pcmcia-cs libpcre3-udeb udev-udeb libc6-udeb rsyslog" univention /instmnt/ $repo_dir
	else
		debootstrap --arch i386 --include="postfix" --exclude="pcmcia-cs libpcre3-udeb udev-udeb libc6-udeb rsyslog" univention /instmnt/ $repo_dir
	fi
fi

if [ -e /instmnt/dev/.udev ]; then
	# disable udev during the installer process
	mv /instmnt/dev/.udev /instmnt/dev/.udev.disabled
fi

# do not umount the source device as it is required in 14_sources_list.sh again
