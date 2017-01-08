#!/bin/sh
# -*- coding: utf-8 -*-
#
# Univention Lib
#  shell function for creating UMC operation and acl objects
#
# Copyright 2011-2017 Univention GmbH
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


eval "$(/usr/sbin/univention-config-registry shell ldap/base)"

_umc_udm_bind () {
	UMC_UDM_BIND_DN=
	UMC_UDM_BIND_PWD=
	UMC_UDM_BIND_PWDFILE=
	while [ $# -ge 1 ]
	do
		case "$1" in
		--bindd*=*) UMC_UDM_BIND_DN=${1#--bindd*=} ;;
		--bindd*) UMC_UDM_BIND_DN=${2} ; shift ;;
		--bindpwd=*) UMC_UDM_BIND_PWD=${1#--bindpwd=} ;;
		--bindpwd) UMC_UDM_BIND_PWD=${2} ; shift ;;
		--bindpwdf*=*) UMC_UDM_BIND_PWDFILE=${1#--bindpwdf*=} ;;
		--bindpwdf*) UMC_UDM_BIND_PWDFILE=${2} ; shift ;;
		esac
		shift
	done
}
_umc_udm_bind "$@"
umc_udm () {
	local module="${1:?Missing module}" action="${2:?Missing action}"
	shift 2 || return $?
	univention-directory-manager "$module" "$action" \
		${UMC_UDM_BIND_DN:+--binddn "$UMC_UDM_BIND_DN"} \
		${UMC_UDM_BIND_PWD:+--bindpwd "$UMC_UDM_BIND_PWD"} \
		${UMC_UDM_BIND_PWDFILE:+--bindpwdfile "$UMC_UDM_BIND_PWDFILE"} \
		"$@"
}

umc_frontend_new_hash () {
	# create new timestamps for index.html and debug.html in order to
	# avoid caching problems in browsers
	local ifile f idir timestamp="$(date +'%Y%d%m%H%M%S')"
	for ifile in index.html debug.html error.html js/umc/login.html; do
		f="/usr/share/univention-management-console-frontend/$ifile"
		[ -w "$f" ] && sed -i 's/\$\(.*\)\$/$'$timestamp'$/' "$f"
	done

	# update the symlinks to the js/css directories
	for idir in css js; do
		rm -f "/usr/share/univention-management-console-frontend/${idir}_\$"*\$ || true
		ln -s "$idir" "/usr/share/univention-management-console-frontend/${idir}_\$${timestamp}\$" || true
	done

	return 0
}

umc_init () {
	eval "$(/usr/sbin/univention-config-registry shell groups/default/domainadmins groups/default/domainusers)"

	# containers
	umc_udm container/cn create --ignore_exists --position "cn=univention,$ldap_base" --set name=UMC || exit $?
	umc_udm container/cn create --ignore_exists --position "cn=policies,$ldap_base" --set name=UMC --set policyPath=1 || exit $?
	umc_udm container/cn create --ignore_exists --position "cn=UMC,cn=univention,$ldap_base" --set name=operations || exit $?

	# default admin policy
	umc_udm policies/umc create --ignore_exists --set name=default-umc-all \
		--position "cn=UMC,cn=policies,$ldap_base" || exit $?

	# link default admin policy to the group "Domain Admins"
	group_admins="${groups_default_domainadmins:-Domain Admins}"
	umc_udm groups/group modify --ignore_exists --dn "cn=$group_admins,cn=groups,$ldap_base" \
		--policy-reference="cn=default-umc-all,cn=UMC,cn=policies,$ldap_base" || exit $?

	# default user policy
	umc_udm policies/umc create --ignore_exists --set name=default-umc-users \
		--position "cn=UMC,cn=policies,$ldap_base" || exit $?

	# link default user policy to the group "Domain Users"
	group_users="${groups_default_domainusers:-Domain Users}"
	umc_udm groups/group modify --ignore_exists --dn "cn=$group_users,cn=groups,$ldap_base" \
		--policy-reference="cn=default-umc-users,cn=UMC,cn=policies,$ldap_base" || exit $?
}

_umc_remove_old () {
	# removes an object and ignores all errors
	local name="$1" module="$2" container="$3"
	umc_udm "$module" remove --dn "cn=$name,$container,$ldap_base" 2>/dev/null || true
}

umc_operation_create () {
	# example: umc_operation_create "udm" "UDM" "users/user" "udm/*:objectType=users/*"
	local name="$1" description="$2" flavor="$3" nargs arg
	shift 3 || return $?
	nargs=$#
	for arg in "$@"
	do
		set -- "$@" --append operation="$arg"
	done
	shift $nargs || return $?
	umc_udm settings/umc_operationset create --ignore_exists \
		--position "cn=operations,cn=UMC,cn=univention,$ldap_base" \
		--set name="$name" \
		--set description="$description" \
		--set flavor="$flavor" "$@" || exit $?
}

umc_policy_append () {
	# example: umc_policy_append "default-umc-all" "udm-all" "udm-users"
	local policy="$1" nargs arg
	shift || return $?
	nargs=$#
	for arg in "$@"
	do
		set -- "$@" --append allow="cn=$arg,cn=operations,cn=UMC,cn=univention,$ldap_base"
	done
	shift $nargs || return $?
	umc_udm policies/umc modify --ignore_exists \
		--dn "cn=$policy,cn=UMC,cn=policies,$ldap_base" "$@" || exit $?
}
