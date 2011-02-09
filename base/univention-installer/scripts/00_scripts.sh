#!/bin/sh
#
# Univention Installer
#  copies installer scripts
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

if [ -d /mnt/script/installer ]; then
	cp /mnt/script/installer/* /lib/univention-installer-scripts.d/
	chmod +x /lib/univention-installer-scripts.d/*
fi

/bin/umount /mnt
