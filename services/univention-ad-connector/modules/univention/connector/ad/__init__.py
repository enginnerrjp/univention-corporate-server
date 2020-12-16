#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention AD Connector
#  Basic class for the AD connector part
#
# Copyright 2004-2020 Univention GmbH
#
# https://www.univention.de/
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
# <https://www.gnu.org/licenses/>.


from __future__ import print_function
import string
import ldap
import sys
import base64
import time
import os
import copy
import types
import re
import array
import ldap.sasl
import subprocess
import univention.uldap
import univention.connector
import univention.debug2 as ud
from ldap.controls import LDAPControl
from ldap.controls import SimplePagedResultsControl
from ldap.filter import escape_filter_chars
from samba.dcerpc import nbt
from samba.param import LoadParm
from samba.net import Net
from samba.credentials import Credentials, DONT_USE_KERBEROS
from samba import drs_utils
from samba.dcerpc import drsuapi, lsa, security
import samba.dcerpc.samr
from tempfile import NamedTemporaryFile


class kerberosAuthenticationFailed(Exception):
	pass


class netbiosDomainnameNotFound(Exception):
	pass

LDB_CONTROL_DOMAIN_SCOPE_OID = "1.2.840.113556.1.4.1339"

# page results
PAGE_SIZE = 1000
# microsoft ldap schema binary attributes
# -> ldbsearch --paged -H AD_SERVER -U CREDS --cross-ncs '(|(attributeSyntax=2.5.5.15)(attributeSyntax=2.5.5.10)(attributeSyntax=2.5.5.17)(attributeSyntax=2.5.5.7))' lDAPDisplayName
BINARY_ATTRIBUTES = [
	'addressEntryDisplayTable', 'addressEntryDisplayTableMSDOS', 'addressSyntax', 'assocNTAccount',
	'attributeCertificateAttribute', 'attributeSecurityGUID', 'audio',
	'auditingPolicy', 'authorityRevocationList', 'birthLocation',
	'cACertificate', 'categoryId', 'certificateRevocationList',
	'controlAccessRights', 'cRLPartitionedRevocationList', 'crossCertificatePair',
	'currentLocation', 'currentValue', 'currMachineId',
	'dBCSPwd', 'deltaRevocationList', 'dhcpClasses',
	'dhcpOptions', 'dhcpProperties', 'dNSProperty',
	'dnsRecord', 'domainWidePolicy', 'dSASignature',
	'eFSPolicy', 'foreignIdentifier', 'fRSExtensions',
	'fRSReplicaSetGUID', 'fRSRootSecurity', 'fRSVersionGUID',
	'groupMembershipSAM', 'helpData16', 'helpData32',
	'implementedCategories', 'invocationId', 'ipsecData',
	'jpegPhoto', 'lDAPIPDenyList', 'linkTrackSecret',
	'lmPwdHistory', 'logonHours', 'logonWorkstation',
	'machineWidePolicy', 'marshalledInterface', 'may',
	'meetingBlob', 'moniker', 'moveTreeState',
	'msAuthz-CentralAccessPolicyID', 'msCOM-ObjectId', 'msDFS-GenerationGUIDv2',
	'msDFS-LinkIdentityGUIDv2', 'msDFS-LinkSecurityDescriptorv2', 'msDFS-NamespaceIdentityGUIDv2',
	'msDFSR-ContentSetGuid', 'msDFSR-Extension', 'msDFSR-ReplicationGroupGuid',
	'msDFSR-Schedule', 'msDFS-TargetListv2', 'msDNS-DNSKEYRecords',
	'msDNS-SigningKeyDescriptors', 'msDNS-SigningKeys', 'msDRM-IdentityCertificate',
	'msDS-AllowedToActOnBehalfOfOtherIdentity', 'msDS-AzObjectGuid', 'msDS-BridgeHeadServersUsed',
	'msDS-ByteArray', 'msDS-Cached-Membership', 'mS-DS-ConsistencyGuid',
	'mS-DS-CreatorSID', 'msDS-ExecuteScriptPassword', 'msDS-GenerationId',
	'msDS-GroupMSAMembership', 'msDS-HasInstantiatedNCs', 'msDS-ManagedPassword',
	'msDS-ManagedPasswordId', 'msDS-ManagedPasswordPreviousId', 'msDS-OptionalFeatureGUID',
	'msDS-QuotaTrustee', 'mS-DS-ReplicatesNCReason', 'msDS-RetiredReplNCSignatures',
	'msDS-RevealedUsers', 'msDs-Schema-Extensions', 'msDS-Site-Affinity',
	'msDS-TransformationRulesCompiled', 'msDS-TrustForestTrustInfo', 'msExchBlockedSendersHash',
	'msExchDisabledArchiveGUID', 'msExchMailboxGuid', 'msExchMailboxSecurityDescriptor',
	'msExchMasterAccountSid', 'msExchSafeRecipientsHash', 'msExchSafeSendersHash',
	'msFVE-KeyPackage', 'msFVE-RecoveryGuid', 'msFVE-VolumeGuid',
	'msieee80211-Data', 'msImaging-PSPIdentifier', 'msImaging-ThumbprintHash',
	'msiScript', 'msKds-KDFParam', 'msKds-RootKeyData',
	'msKds-SecretAgreementParam', 'mSMQDigests', 'mSMQDigestsMig',
	'mSMQEncryptKey', 'mSMQOwnerID', 'mSMQQMID',
	'mSMQQueueType', 'mSMQSignCertificates', 'mSMQSignCertificatesMig',
	'mSMQSignKey', 'mSMQSiteID', 'mSMQSites',
	'mSMQUserSid', 'ms-net-ieee-80211-GP-PolicyReserved', 'ms-net-ieee-8023-GP-PolicyReserved',
	'msPKIAccountCredentials', 'msPKI-CredentialRoamingTokens', 'msPKIDPAPIMasterKeys',
	'msPKIRoamingTimeStamp', 'msRTCSIP-UserRoutingGroupId', 'msSPP-ConfigLicense',
	'msSPP-CSVLKSkuId', 'msSPP-IssuanceLicense', 'msSPP-KMSIds',
	'msSPP-OnlineLicense', 'msSPP-PhoneLicense', 'msTAPI-ConferenceBlob',
	'msTPM-SrkPubThumbprint', 'msWMI-TargetObject', 'netbootDUID',
	'netbootGUID', 'nTGroupMembers', 'ntPwdHistory',
	'nTSecurityDescriptor', 'objectGUID', 'objectSid',
	'oMObjectClass', 'oMTGuid', 'oMTIndxGuid',
	'originalDisplayTable', 'originalDisplayTableMSDOS', 'otherWellKnownObjects',
	'parentCACertificateChain', 'parentGUID', 'partialAttributeDeletionList',
	'partialAttributeSet', 'pekList', 'pendingCACertificates',
	'perMsgDialogDisplayTable', 'perRecipDialogDisplayTable', 'photo',
	'pKIEnrollmentAccess', 'pKIExpirationPeriod', 'pKIKeyUsage',
	'pKIOverlapPeriod', 'pKT', 'pKTGuid',
	'prefixMap', 'previousCACertificates', 'priorValue',
	'privateKey', 'productCode', 'proxiedObjectName',
	'publicKeyPolicy', 'registeredAddress', 'replicationSignature',
	'replPropertyMetaData', 'replUpToDateVector', 'repsFrom',
	'repsTo', 'requiredCategories', 'retiredReplDSASignatures',
	'samDomainUpdates', 'schedule', 'schemaIDGUID',
	'schemaInfo', 'searchGuide', 'securityIdentifier',
	'serviceClassID', 'serviceClassInfo', 'serviceInstanceVersion',
	'sIDHistory', 'siteGUID', 'supplementalCredentials',
	'supportedApplicationContext', 'syncWithSID', 'teletexTerminalIdentifier',
	'telexNumber', 'terminalServer', 'thumbnailLogo',
	'thumbnailPhoto', 'tokenGroups', 'tokenGroupsGlobalAndUniversal',
	'tokenGroupsNoGCAcceptable', 'trustAuthIncoming', 'trustAuthOutgoing',
	'unicodePwd', 'unixUserPassword', 'upgradeProductCode',
	'userCert', 'userCertificate', 'userPassword',
	'userPKCS12', 'userSMIMECertificate', 'volTableGUID',
	'volTableIdxGUID', 'wellKnownObjects', 'winsockAddresses',
]


def activate_user(connector, key, object):
	# set userAccountControl to 544
	for i in range(0, 10):
		try:
			connector.lo_ad.lo.modify_s(compatible_modstring(object['dn']), [(ldap.MOD_REPLACE, 'userAccountControl', ['544'])])
		except ldap.NO_SUCH_OBJECT:
			time.sleep(1)
			continue
		return True
	return False


def set_univentionObjectFlag_to_synced(connector, key, ucs_object):
	if connector.configRegistry.is_true('ad/member', False):
		connector._object_mapping(key, ucs_object, 'ucs')

		ucs_result = connector.lo.search(base=ucs_object['dn'], attr=['univentionObjectFlag'])

		flags = ucs_result[0][1].get('univentionObjectFlag', [])
		if b'synced' not in flags:
			connector.lo.lo.lo.modify_s(ucs_object['dn'], [(ldap.MOD_ADD, 'univentionObjectFlag', b'synced')])


def group_members_sync_from_ucs(connector, key, object):
	return connector.group_members_sync_from_ucs(key, object)


def object_memberships_sync_from_ucs(connector, key, object):
	return connector.object_memberships_sync_from_ucs(key, object)


def group_members_sync_to_ucs(connector, key, object):
	return connector.group_members_sync_to_ucs(key, object)


def object_memberships_sync_to_ucs(connector, key, object):
	return connector.object_memberships_sync_to_ucs(key, object)


def primary_group_sync_from_ucs(connector, key, object):
	return connector.primary_group_sync_from_ucs(key, object)


def primary_group_sync_to_ucs(connector, key, object):
	return connector.primary_group_sync_to_ucs(key, object)


def disable_user_from_ucs(connector, key, object):
	return connector.disable_user_from_ucs(key, object)


def set_userPrincipalName_from_ucr(connector, key, object):
	return connector.set_userPrincipalName_from_ucr(key, object)


def disable_user_to_ucs(connector, key, object):
	return connector.disable_user_to_ucs(key, object)


def encode_attrib(attrib):
	if not attrib or isinstance(attrib, type(u'')):  # referral or already unicode
		return attrib
	return unicode(attrib, 'utf8')


def encode_attriblist(attriblist):
	if not isinstance(attriblist, type([])):
		return encode_attrib(attriblist)
	else:
		for i in range(len(attriblist)):
			attriblist[i] = encode_attrib(attriblist[i])
		return attriblist


def encode_ad_object(ad_object):
	if isinstance(ad_object, type([])):
		return encode_attriblist(ad_object)
	else:
		for key in ad_object.keys():
			if key == 'objectSid':
				ad_object[key] = [decode_sid(ad_object[key][0])]
			elif key in BINARY_ATTRIBUTES:
				ud.debug(ud.LDAP, ud.INFO, "encode_ad_object: attrib %s ignored during encoding" % key)  # don't recode
			else:
				try:
					ad_object[key] = encode_attriblist(ad_object[key])
				except (ldap.SERVER_DOWN, SystemExit):
					raise
				except:  # FIXME: which exception is to be caught?
					ud.debug(ud.LDAP, ud.WARN, "encode_ad_object: encode attrib %s failed, ignored!" % key)
		return ad_object


def encode_ad_result(ad_result):
	'''
	encode an result from an python-ldap search
	'''
	return (encode_attrib(ad_result[0]), encode_ad_object(ad_result[1]))


def encode_ad_resultlist(ad_resultlist):
	'''
	encode an result from an python-ldap search
	'''
	for i in range(len(ad_resultlist)):
		ad_resultlist[i] = encode_ad_result(ad_resultlist[i])
	return ad_resultlist


def unix2ad_time(l):
	d = 116444736000000000  # difference between 1601 and 1970
	return int(time.mktime(time.gmtime(time.mktime(time.strptime(l, "%Y-%m-%d")) + 90000))) * 10000000 + d  # 90000s are one day and one hour


def ad2unix_time(l):
	d = 116444736000000000  # difference between 1601 and 1970
	return time.strftime("%d.%m.%y", time.gmtime((l - d) / 10000000))


def samba2ad_time(l):
	if l in [0, 1]:
		return l
	d = 116444736000000000  # difference between 1601 and 1970
	return int(time.mktime(time.gmtime(l + 3600))) * 10000000 + d


def ad2samba_time(l):
	if l == 0:
		return l
	d = 116444736000000000  # difference between 1601 and 1970
	return int(((l - d)) / 10000000)

# mapping funtions


def samaccountname_dn_mapping(connector, given_object, dn_mapping_stored, ucsobject, propertyname, propertyattrib, ocucs, ucsattrib, ocad, dn_attr=None):
	'''
	map dn of given object (which must have an samaccountname in AD)
	ocucs and ocad are objectclasses in UCS and AD
	'''
	object = copy.deepcopy(given_object)

	samaccountname = u''
	dn_attr_val = u''

	if object['dn'] is not None:
		if 'sAMAccountName' in object['attributes']:
			samaccountname = object['attributes']['sAMAccountName'][0].decode('UTF-8')
		if dn_attr:
			try:
				dn_attr_vals = [value for key, value in object['attributes'].items() if dn_attr.lower() == key.lower()][0]
			except IndexError:
				pass
			else:
				dn_attr_val = dn_attr_vals[0].decode('UTF-8')

	def dn_premapped(object, dn_key, dn_mapping_stored):
		if (dn_key not in dn_mapping_stored) or (not object[dn_key]):
			ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: not premapped (in first instance)")
			return False
		else:  # check if DN exists
			if ucsobject:
				if connector.get_object(object[dn_key]) is not None:
					ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: premapped AD object found")
					return True
				else:
					ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: premapped AD object not found")
					return False
			else:
				if connector.get_ucs_ldap_object(object[dn_key]) is not None:
					ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: premapped UCS object found")
					return True
				else:
					ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: premapped UCS object not found")
					return False

	for dn_key in ['dn', 'olddn']:
		ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: check newdn for key %s: %s" % (dn_key, object.get(dn_key)))
		if dn_key in object and not dn_premapped(object, dn_key, dn_mapping_stored):

			dn = object[dn_key]

			# Skip Configuration objects with empty DNs
			if dn is None:
				break

			exploded_dn = ldap.dn.str2dn(dn)
			(_fst_rdn_attribute, fst_rdn_value, _flags) = exploded_dn[0][0]
			value = fst_rdn_value

			if ucsobject:
				# lookup the cn as sAMAccountName in AD to get corresponding DN, if not found create new
				ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: got an UCS-Object")

				if connector.property[propertyname].mapping_table and propertyattrib in connector.property[propertyname].mapping_table.keys():
					for ucsval, conval in connector.property[propertyname].mapping_table[propertyattrib]:
						if value.lower() == ucsval.lower():
							value = conval
							ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: map samaccountanme regarding to mapping-table")
							continue

				ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: search in ad samaccountname=%s" % value)
				search_filter = format_escaped('(&(objectclass={0!e})(samaccountname={1!e}))', ocad, value)
				result = connector.lo_ad.search(filter=compatible_modstring(search_filter))
				if result and len(result) > 0 and result[0] and len(result[0]) > 0 and result[0][0]:  # no referral, so we've got a valid result
					if dn_key == 'olddn' or (dn_key == 'dn' and 'olddn' not in object):
						newdn = result[0][0]
					else:
						# move
						# return a kind of frankenstein DN here, sync_from_ucs replaces the UCS LDAP base
						# with the AD LDAP base at a later stage, see Bug #48440
						newdn = ldap.dn.dn2str([str2dn(result[0][0])[0]] + exploded_dn[1:])
				else:
					newdn = ldap.dn.dn2str([[('cn', fst_rdn_value_utf8, ldap.AVA_STRING)]] + exploded_dn[1:])  # new object, don't need to change
				ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: newdn: %s" % newdn)
			else:
				# get the object to read the sAMAccountName in AD and use it as name
				# we have no fallback here, the given dn must be found in AD or we've got an error
				ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: got an AD-Object")
				i = 0

				while (not samaccountname):  # in case of olddn this is already set
					i = i + 1
					search_dn = dn
					if 'deleted_dn' in object:
						search_dn = object['deleted_dn']
					try:
						samaccountname_filter = format_escaped('(objectClass={0!e})', osad)
						samaccountname_search_result = connector.ad_search_ext_s(search_dn, ldap.SCOPE_BASE, samaccountname_filter, ['sAMAccountName'])
						samaccountname = samaccountname_search_result[0][1]['sAMAccountName'][0].decode('UTF-8')
						ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: got samaccountname from AD")
					except ldap.NO_SUCH_OBJECT:  # AD may need time
						if i > 5:
							raise
						time.sleep(1)  # AD may need some time...

				if connector.property[propertyname].mapping_table and propertyattrib in connector.property[propertyname].mapping_table.keys():
					for ucsval, conval in connector.property[propertyname].mapping_table[propertyattrib]:
						if samaccountname.lower() == conval.lower():
							samaccountname = ucsval
							ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: map samaccountanme according to mapping-table")
							continue
						else:
							ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: samaccountname not in mapping-table")

				# search for object with this dn in ucs, needed if it lies in a different container
				ucsdn = ''
				ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: samaccountname is: %r" % (samaccountname,))
				ucsdn_filter = format_escaped(u'(&(objectclass={0!e})({1}={2!e}))', ocucs, ucsattrib, samaccountname)
				ucsdn_result = connector.search_ucs(filter=ucsdn_filter, base=connector.lo.base, scope='sub', attr=['objectClass'])
				if ucsdn_result and len(ucsdn_result) > 0 and ucsdn_result[0] and len(ucsdn_result[0]) > 0:
					ucsdn = ucsdn_result[0][0]

				if ucsdn and (dn_key == 'olddn' or (dn_key == 'dn' and 'olddn' not in object)):
					newdn = ucsdn
					ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: newdn is ucsdn")
				else:
					if dn_attr:
						newdn_rdn = [(dn_attr, dn_attr_val, ldap.AVA_STRING)]  # guess the old dn
					else:
						newdn_rdn = [(ucsattrib, samaccountname, ldap.AVA_STRING)]

					newdn = ldap.dn.dn2str([newdn_rdn] + exploded_dn[1:])  # guess the old dn

			ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: newdn for key %r:" % (dn_key,))
			ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: olddn: %r" % (dn,))
			ud.debug(ud.LDAP, ud.INFO, "samaccount_dn_mapping: newdn: %r" % (newdn,))

			object[dn_key] = newdn
	return object


def user_dn_mapping(connector, given_object, dn_mapping_stored, isUCSobject):
	'''
	map dn of given user using the samaccountname/uid
	connector is an instance of univention.connector.ad, given_object an object-dict,
	dn_mapping_stored a list of dn-types which are already mapped because they were stored in the config-file
	'''
	return samaccountname_dn_mapping(connector, given_object, dn_mapping_stored, isUCSobject, 'user', u'samAccountName', u'posixAccount', 'uid', u'user')


def group_dn_mapping(connector, given_object, dn_mapping_stored, isUCSobject):
	'''
	map dn of given group using the samaccountname/cn
	connector is an instance of univention.connector.ad, given_object an object-dict,
	dn_mapping_stored a list of dn-types which are already mapped because they were stored in the config-file
	'''
	return samaccountname_dn_mapping(connector, given_object, dn_mapping_stored, isUCSobject, 'group', u'cn', u'posixGroup', 'cn', u'group')


def windowscomputer_dn_mapping(connector, given_object, dn_mapping_stored, isUCSobject):
	'''
	map dn of given windows computer using the samaccountname/uid
	connector is an instance of univention.connector.ad, given_object an object-dict,
	dn_mapping_stored a list of dn-types which are already mapped because they were stored in the config-file
	'''
	return samaccountname_dn_mapping(connector, given_object, dn_mapping_stored, isUCSobject, 'windowscomputer', u'samAccountName', u'posixAccount', 'uid', u'computer', 'cn')


def old_user_dn_mapping(connector, given_object):
	object = copy.deepcopy(given_object)

	# LDAP_SERVER_SHOW_DELETED_OID -> 1.2.840.113556.1.4.417
	ctrls = [LDAPControl('1.2.840.113556.1.4.417', criticality=1)]
	samaccountname = ''

	if 'sAMAccountName' in object:
		samaccountname = object['sAMAccountName']

	for dn_key in ['dn', 'olddn']:
		ud.debug(ud.LDAP, ud.INFO, "check newdn for key %s:" % dn_key)
		if dn_key in object:

			dn = object[dn_key]

			pos = dn.find('=')
			pos2 = len(univention.connector.ad.explode_unicode_dn(dn)[0]) - 1
			attrib = dn[:pos]
			value = dn[pos + 1:pos2]

			if attrib == 'uid':
				# lookup the uid as sAMAccountName in AD to get corresponding DN, if not found create new User
				ud.debug(ud.LDAP, ud.INFO, "search in ad samaccountname=%s" % value)
				search_filter = format_escaped('(&(objectclass=user)(samaccountname={0!e}))', value)
				result = connector.lo_ad.search(filter=search_filter)
				ud.debug(ud.LDAP, ud.INFO, "search in result %s" % result)
				if result and len(result) > 0 and result[0] and len(result[0]) > 0 and result[0][0]:  # no referral, so we've got a valid result
					addn = encode_attrib(result[0][0])
					ud.debug(ud.LDAP, ud.INFO, "search in ad gave dn %s" % addn)
					# adpos2 = len(univention.connector.ad.explode_unicode_dn(addn)[0]) - 1
					# newdn = addn[:adpos2] + dn[pos2:]
					newdn = addn
				else:
					newdn = 'cn' + dn[pos:]

			else:
				# get the object to read the sAMAccountName in AD and use it as uid
				# we have no fallback here, the given dn must be found in AD or we've got an error
				i = 0
				while (not samaccountname):  # in case of olddn this is already set
					i = i + 1
					search_dn = dn
					if 'deleted_dn' in object:
						search_dn = object['deleted_dn']
					search_dn = compatible_modstring(search_dn)
					try:
						result = connector.lo_ad.search(
							base=search_dn,
							scope='base', filter='(objectClass=user)',
							attr=['sAMAccountName'], serverctrls=ctrls)
						samaccountname = encode_attrib(result[0][1]['sAMAccountName'][0])
					except ldap.NO_SUCH_OBJECT:  # AD may need time
						if i > 5:
							raise
						time.sleep(1)  # AD may need some time...

				pos = dn.find('=')
				pos2 = len(univention.connector.ad.explode_unicode_dn(dn)[0]) - 1

				newdn = 'uid=' + samaccountname + dn[pos2:]
			try:
				ud.debug(ud.LDAP, ud.INFO, "newdn for key %s:" % dn_key)
				ud.debug(ud.LDAP, ud.INFO, "olddn: %s" % dn)
				ud.debug(ud.LDAP, ud.INFO, "newdn: %s" % newdn)
			except:  # FIXME: which exception is to be caught?
				pass

			object[dn_key] = newdn
	return object


def decode_sid(value):
	return str(ndr_unpack(security.dom_sid, value))


def __is_sid_string(sid):
	return sid.startswith(b'S-')


def __is_int(value):
	try:
		int(value)
		return True
	except (ValueError, TypeError):
		return False


def decode_addlist(list, encoding):
	newlist = []
	for (attr, values) in list:
		if hasattr(attr, 'decode') and not isinstance(attr, types.UnicodeType):
			newattr = attr.decode(encoding)
		else:
			newattr = attr

		if attr in BINARY_ATTRIBUTES:
			newlist.append((newattr, values))
			continue

		if isinstance(values, type([])):
			newlist.append((newattr, decode_list(values, encoding)))
		else:
			newlist.append((newattr, decode_list(values, encoding)))
	return newlist


def compatible_list(list):
	return encode_list(decode_list(list, 'latin'), 'utf8')


def compatible_modlist(list):
	return encode_modlist(decode_modlist(list, 'latin'), 'utf8')


def compatible_addlist(list):
	return encode_addlist(decode_addlist(list, 'latin'), 'utf8')


def compatible_modstring(string):
	if hasattr(string, 'decode') and not isinstance(string, types.UnicodeType):
		string = string.decode('latin')
	if hasattr(string, 'encode'):
		string = string.encode('utf8')
	return string


def explode_unicode_dn(dn, notypes=0):
	ret = []
	last = -1
	last_found = 0
	while dn.find(',', last + 1) > 0:
		last = dn.find(',', last + 1)
		if dn[last - 1] != '\\':
			if notypes == 1:
				last_found = dn.find('=', last_found) + 1
			if dn[last_found] == ',':
				last_found += 1
			ret.append(dn[last_found:last])
			last_found = last
	ret.append(dn[last + 1:])

	return ret


class LDAPEscapeFormatter(string.Formatter):
	"""
	A custom string formatter that supports a special `e` conversion, to employ
	the function `ldap.filter.escape_filter_chars()` on the given value.

	>>> LDAPEscapeFormatter().format("{0}", "*")
	'*'
	>>> LDAPEscapeFormatter().format("{0!e}", "*")
	'\\2a'

	Unfortunately this does not support the key/index-less variant
	(see http://bugs.python.org/issue13598).

	>>> LDAPEscapeFormatter().format("{!e}", "*")
	Traceback (most recent call last):
	KeyError: ''
	"""
	def convert_field(self, value, conversion):
		if conversion == 'e':
			if isinstance(value, six.string_types):
				return escape_filter_chars(value)
			if isinstance(value, bytes):
				raise TypeError('Filter must be string, not bytes: %r' % (value,))
			return escape_filter_chars(str(value))
		return super(LDAPEscapeFormatter, self).convert_field(value, conversion)


def format_escaped(format_string, *args, **kwargs):
	"""
	Convenience-wrapper around `LDAPEscapeFormatter`.

	Use `!e` do denote format-field that should be escaped using
	`ldap.filter.escape_filter_chars()`'

	>>> format_escaped("{0!e}", "*")
	'\\2a'
	"""
	return LDAPEscapeFormatter().format(format_string, *args, **kwargs)


class Simple_AD_Connection():

	''' stripped down univention.connector.ad.ad class
		difference: accept "bindpwd" directly instead of "bindpw" filename
		difference: don't require mapping
		difference: Skip init_group_cache code (i.e. use init_group_cache=False)
		difference: don't use TLS
	'''

	def __init__(self, CONFIGBASENAME, ucr, host, port, base, binddn, bindpw, certificate):

		self.CONFIGBASENAME = CONFIGBASENAME

		self.host = host
		self.port = port
		self.base = base
		self.binddn = binddn
		self.bindpw = bindpw
		self.certificate = certificate
		self.ucr = ucr
		self.protocol = 'ldaps' if ucr.is_true('%s/ad/ldap/ldaps' % CONFIGBASENAME, False) else 'ldap'
		self.uri = "%s://%s:%d" % (self.protocol, self.host, int(self.port))

		if self.certificate:
			ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.certificate)

		#ldap.set_option(ldap.OPT_DEBUG_LEVEL, 4095)
		#ldap._trace_level = 9
		#ldap.set_option(ldap.OPT_X_SASL_SSF_MIN, 1)
		#ldap.set_option(ldap.OPT_X_SASL_SECPROPS, "minssf=1")

		self.lo = ldap.ldapobject.ReconnectLDAPObject(self.uri, retry_max=10, retry_delay=1)

		if ucr.is_true('%s/ad/ldap/kerberos' % CONFIGBASENAME):
			princ = self.binddn
			if ldap.dn.is_dn(self.binddn):
				princ = ldap.dn.str2dn(self.binddn)[0][0][1]
			os.environ['KRB5CCNAME'] = '/var/cache/univention-ad-connector/krb5.cc.well'
			with NamedTemporaryFile('w') as tmp_file:
				tmp_file.write(self.bindpw)
				tmp_file.flush()
				p1 = subprocess.Popen(['kdestroy', ], close_fds=True)
				p1.wait()
				cmd_block = ['kinit', '--no-addresses', '--password-file=%s' % tmp_file.name, princ]
				p1 = subprocess.Popen(cmd_block, close_fds=True)
				stdout, stderr = p1.communicate()
				auth = ldap.sasl.gssapi("")
				self.lo.sasl_interactive_bind_s("", auth)
		else:
			self.lo.simple_bind_s(self.binddn, self.bindpw)

		self.lo.set_option(ldap.OPT_REFERRALS, 0)

		self.ad_sid = None
		result = self.lo.search_ext_s(self.base, ldap.SCOPE_BASE, 'objectclass=domain', ['objectSid'], timeout=-1, sizelimit=0)
		if 'objectSid' in result[0][1]:
			objectSid_blob = result[0][1]['objectSid'][0]
			self.ad_sid = univention.connector.ad.decode_sid(objectSid_blob)
		if self.ad_sid is None:
			raise Exception('Failed to get SID from AD!')


class ad(univention.connector.ucs):

	range_retrieval_pattern = re.compile("^([^;]+);range=(\d+)-(\d+|\*)$")

	def __init__(self, CONFIGBASENAME, property, baseConfig, ad_ldap_host, ad_ldap_port, ad_ldap_base, ad_ldap_binddn, ad_ldap_bindpw, ad_ldap_certificate, listener_dir, init_group_cache=True):

		univention.connector.ucs.__init__(self, CONFIGBASENAME, property, baseConfig, listener_dir)

		self.CONFIGBASENAME = CONFIGBASENAME

		self.ad_ldap_host = ad_ldap_host
		self.ad_ldap_port = ad_ldap_port
		self.ad_ldap_base = ad_ldap_base
		self.ad_ldap_binddn = ad_ldap_binddn
		self.ad_ldap_bindpw = ad_ldap_bindpw
		self.ad_ldap_certificate = ad_ldap_certificate
		self.baseConfig = baseConfig

		self.open_ad()

		# update binary attribute list
		global BINARY_ATTRIBUTES
		for attr in self.baseConfig.get('%s/ad/binary_attributes' % self.CONFIGBASENAME, '').split(','):
			attr = attr.strip()
			if attr not in BINARY_ATTRIBUTES:
				BINARY_ATTRIBUTES.append(attr)

		if not self.config.has_section('AD'):
			ud.debug(ud.LDAP, ud.INFO, "__init__: init add config section 'AD'")
			self.config.add_section('AD')

		if not self.config.has_section('AD rejected'):
			ud.debug(ud.LDAP, ud.INFO, "__init__: init add config section 'AD rejected'")
			self.config.add_section('AD rejected')

		if not self.config.has_option('AD', 'lastUSN'):
			ud.debug(ud.LDAP, ud.INFO, "__init__: init lastUSN with 0")
			self._set_config_option('AD', 'lastUSN', '0')
			self.__lastUSN = 0
		else:
			self.__lastUSN = int(self._get_config_option('AD', 'lastUSN'))

		if not self.config.has_section('AD GUID'):
			ud.debug(ud.LDAP, ud.INFO, "__init__: init add config section 'AD GUID'")
			self.config.add_section('AD GUID')

		# Save a list of objects just created, this is needed to
		# prevent the back sync of a password if it was changed just
		# after the creation
		self.creation_list = []

		# Build an internal cache with AD as key and the UCS object as cache
		self.group_mapping_cache_ucs = {}
		self.group_mapping_cache_con = {}

		# Save the old members of a group
		# The connector is object based, at least in the direction AD/AD to LDAP, because we don't
		# have a local cache. group_members_cache_ucs and group_members_cache_con help to
		# determine if the group membership was already saved. For example, one group and
		# five users are created on UCS side. After two users have been synced to AD/S4,
		# the group is snyced. But in AD/S4 only existing members can be stored in the group.
		# Now the sync goes back from AD/S4 to LDAP and we should not remove the three users
		# from the group. For this we remove only members who are in the local cache.

		# UCS groups and UCS members
		# * initialized during start
		# * entry updated in group_members_sync_from_ucs and object_memberships_sync_from_ucs
		# * entry flushed for group object in sync_to_ucs / add_in_ucs
		# * entry used for decision in group_members_sync_to_ucs
		self.group_members_cache_ucs = {}

		# AD groups and AD members
		# * initialized during start
		# * entry updated in group_members_sync_to_ucs and object_memberships_sync_to_ucs
		# * entry flushed for group object in sync_from_ucs / ADD
		# * entry used for decision in group_members_sync_from_ucs
		self.group_members_cache_con = {}

		if init_group_cache:
			ud.debug(ud.LDAP, ud.PROCESS, 'Building internal group membership cache')
			ad_groups = self.__search_ad(filter='(objectClass=group)', attrlist=['member'])
			ud.debug(ud.LDAP, ud.INFO, "__init__: ad_groups: %s" % ad_groups)
			for ad_group in ad_groups:
				if not ad_group or not ad_group[0]:
					continue
				ad_group_dn, ad_group_attrs = ad_group
				group = ad_group_dn.lower()
				self.group_members_cache_con[group] = set()
				if ad_group_attrs:
					ad_members = self.get_ad_members(ad_group_dn, ad_group_attrs)
					self.group_members_cache_con[group].update(m.lower() for m in ad_members)
			ud.debug(ud.LDAP, ud.INFO, "__init__: self.group_members_cache_con: %s" % self.group_members_cache_con)

			ucs_groups = self.search_ucs(filter='(objectClass=univentionGroup)', attr=['uniqueMember'])
			for ucs_group in ucs_groups:
				group = ucs_group[0].lower()
				self.group_members_cache_ucs[group] = set()
				if ucs_group[1]:
					for member in ucs_group[1].get('uniqueMember'):
						self.group_members_cache_ucs[group].add(member.lower())
			ud.debug(ud.LDAP, ud.INFO, "__init__: self.group_members_cache_ucs: %s" % self.group_members_cache_ucs)

			ud.debug(ud.LDAP, ud.PROCESS, 'Internal group membership cache was created')

		if self.lo_ad.binddn:
			try:
				result = self.lo_ad.search(base=self.lo_ad.binddn, scope='base')
				self.ad_ldap_bind_username = result[0][1]['sAMAccountName'][0]
			except Exception as msg:
				print("Failed to get SID from AD: %s" % msg)
				sys.exit(1)
		else:
			self.ad_ldap_bind_username = self.baseConfig['%s/ad/ldap/binddn' % self.CONFIGBASENAME]

		try:
			result = self.lo_ad.search(filter='(objectclass=domain)', base=ad_ldap_base, scope='base', attr=['objectSid'])
			object_sid = result[0][1]['objectSid'][0]
			self.ad_sid = univention.connector.ad.decode_sid(object_sid)
		except Exception as msg:
			print("Failed to get SID from AD: %s" % msg)
			sys.exit(1)

		# Get NetBios Domain Name
		self.ad_netbios_domainname = self.baseConfig.get('%s/ad/netbiosdomainname' % self.CONFIGBASENAME, None)
		if not self.ad_netbios_domainname:
			lp = LoadParm()
			net = Net(creds=None, lp=lp)
			try:
				cldap_res = net.finddc(address=self.ad_ldap_host, flags=nbt.NBT_SERVER_LDAP | nbt.NBT_SERVER_DS | nbt.NBT_SERVER_WRITABLE)
				self.ad_netbios_domainname = cldap_res.domain_name
			except RuntimeError:
				ud.debug(ud.LDAP, ud.WARN, 'Failed to find Netbios domain name from AD server. Maybe the Windows Active Directory server is rebooting. Othwise please configure the NetBIOS setting  manually: "ucr set %s/ad/netbiosdomainname=<AD NetBIOS Domainname>"' % self.CONFIGBASENAME)
				raise
		if not self.ad_netbios_domainname:
			raise netbiosDomainnameNotFound('Failed to find Netbios domain name from AD server. Please configure it manually: "ucr set %s/ad/netbiosdomainname=<AD NetBIOS Domainname>"' % self.CONFIGBASENAME)

		ud.debug(ud.LDAP, ud.PROCESS, 'Using %s as AD Netbios domain name' % self.ad_netbios_domainname)

		# Lookup list of single value attributes from AD DC Schema
		schema_base = "CN=Schema,CN=Configuration,%s" % self.ad_ldap_base
		try:
			result = self.__search_ad(filter='(isSingleValued=TRUE)', base=schema_base, attrlist=['lDAPDisplayName'])
		except ldap.LDAPError as msg:
			error_msg = "Failed to lookup attribute Schema from AD: %s" % msg
			ud.debug(ud.LDAP, ud.ERROR, error_msg)
			print(error_msg)
			sys.exit(1)

		self.single_valued_ad_attributes = [record[1]['lDAPDisplayName'][0] for record in result]

		# Flag single value attributes as such in the connector mapping
		for mapping_key, mapping_property in self.property.items():
			for attr_type in ('attributes', 'post_attributes'):
				conn_attributes = getattr(mapping_property, attr_type)
				if not conn_attributes:
					continue
				for attr_key, attr in conn_attributes.items():
					if not getattr(attr, 'con_other_attribute') and attr.con_attribute in self.single_valued_ad_attributes:
						attr.single_value = True

		# Mark mailPrimaryAddress as dependent on changes of AD "mail"
		for mapping_key, mapping_property in self.property.items():
			for attr_type in ('attributes', 'post_attributes'):
				con_attributes = getattr(mapping_property, attr_type)
				if not con_attributes:
					continue
				for attr_key, attr in con_attributes.items():
					if attr.ldap_attribute == 'mailPrimaryAddress':
						attr.con_depends = 'mail'

		# Log the active mapping
		if ud.get_level(ud.LDAP) >= ud.INFO:
			mapping_lines = ["Mapping:"]
			mapping_lines.append("ad_mapping = {")
			indent = " " * 4
			for mapping_key, mapping_property in self.property.items():
				mapping_lines.append("%s'%s' = univention.connector.property(" % (indent, mapping_key))
				indent = " " * 8
				for conn_attribute in sorted(vars(mapping_property)):
					subobj = getattr(mapping_property, conn_attribute)
					if not subobj:
						continue
					if isinstance(subobj, dict):
						mapping_lines.append("%s%s = {" % (indent, conn_attribute))
						indent = " " * 12
						for attr_key, mapping_attr in subobj.items():
							mapping_lines.append("%s%s = univention.connector.attribute(" % (indent, attr_key))
							indent = " " * 16
							if isinstance(mapping_attr, univention.connector.attribute):
								for attribute_member in sorted(vars(mapping_attr)):
									subsubobj = getattr(mapping_attr, attribute_member)
									if not subsubobj:
										continue
									if isinstance(subsubobj, str):
										mapping_lines.append("%s'%s' = '%s'" % (indent, attribute_member, subsubobj))
									else:
										mapping_lines.append("%s'%s' = %s" % (indent, attribute_member, subsubobj))
							indent = " " * 12
							mapping_lines.append("%s)" % (indent,))
						indent = " " * 8
						mapping_lines.append("%s}" % (indent,))
					elif isinstance(subobj, str):
						mapping_lines.append("%s%s = '%s'" % (indent, conn_attribute, subobj))
					else:
						mapping_lines.append("%s%s = %s" % (indent, conn_attribute, subobj))
				indent = " " * 4
				mapping_lines.append("%s)" % (indent,))
			mapping_lines.append("}")
			ud.debug(ud.LDAP, ud.INFO, '\n'.join(mapping_lines))

		self.drs = None
		self.samr = None

		self.profiling = self.baseConfig.is_true('%s/ad/poll/profiling' % self.CONFIGBASENAME, False)


	def open_drs_connection(self):
		lp = LoadParm()
		Net(creds=None, lp=lp)

		repl_creds = Credentials()
		repl_creds.guess(lp)
		repl_creds.set_kerberos_state(DONT_USE_KERBEROS)
		repl_creds.set_username(self.ad_ldap_bind_username)
		repl_creds.set_password(self.lo_ad.bindpw)

		# binding_options = "seal,print"
		self.drs, self.drsuapi_handle, bind_supported_extensions = drs_utils.drsuapi_connect(self.ad_ldap_host, lp, repl_creds)

		dcinfo = drsuapi.DsGetDCInfoRequest1()
		dcinfo.level = 1
		dcinfo.domain_name = self.ad_netbios_domainname
		i, o = self.drs.DsGetDomainControllerInfo(self.drsuapi_handle, 1, dcinfo)
		computer_dn = o.array[0].computer_dn

		req = drsuapi.DsNameRequest1()
		names = drsuapi.DsNameString()
		names.str = computer_dn
		req.format_offered = drsuapi.DRSUAPI_DS_NAME_FORMAT_FQDN_1779
		req.format_desired = drsuapi.DRSUAPI_DS_NAME_FORMAT_GUID
		req.count = 1
		req.names = [names]
		i, o = self.drs.DsCrackNames(self.drsuapi_handle, 1, req)
		source_dsa_guid = o.array[0].result_name
		self.computer_guid = source_dsa_guid.replace('{', '').replace('}', '').encode('utf8')

	def open_samr(self):
		lp = LoadParm()
		lp.load('/dev/null')

		creds = Credentials()
		creds.guess(lp)
		creds.set_kerberos_state(DONT_USE_KERBEROS)

		creds.set_username(self.ad_ldap_bind_username)
		creds.set_password(self.lo_ad.bindpw)

		binding_options = "\pipe\samr"
		binding = "ncacn_np:%s[%s]" % (self.ad_ldap_host, binding_options)

		self.samr = samba.dcerpc.samr.samr(binding, lp, creds)
		handle = self.samr.Connect2(None, security.SEC_FLAG_MAXIMUM_ALLOWED)

		sam_domain = lsa.String()
		sam_domain.string = self.ad_netbios_domainname
		sid = self.samr.LookupDomain(handle, sam_domain)
		self.dom_handle = self.samr.OpenDomain(handle, security.SEC_FLAG_MAXIMUM_ALLOWED, sid)

	def get_kerberos_ticket(self):
		p1 = subprocess.Popen(['kdestroy', ], close_fds=True)
		p1.wait()
		cmd_block = ['kinit', '--no-addresses', '--password-file=%s' % self.baseConfig['%s/ad/ldap/bindpw' % self.CONFIGBASENAME], self.baseConfig['%s/ad/ldap/binddn' % self.CONFIGBASENAME]]
		p1 = subprocess.Popen(cmd_block, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
		stdout, stderr = p1.communicate()
		if p1.returncode != 0:
			raise kerberosAuthenticationFailed('The following command failed: "%s" (%s): %s' % (' '.join(cmd_block), p1.returncode, stdout))

	def open_ad(self):
		tls_mode = 2
		if '%s/ad/ldap/ssl' % self.CONFIGBASENAME in self.configRegistry and self.configRegistry['%s/ad/ldap/ssl' % self.CONFIGBASENAME] == "no":
			ud.debug(ud.LDAP, ud.INFO, "__init__: The LDAP connection to AD does not use SSL (switched off by UCR \"%s/ad/ldap/ssl\")." % self.CONFIGBASENAME)
			tls_mode = 0
		ldaps = self.baseConfig.is_true('%s/ad/ldap/ldaps' % self.CONFIGBASENAME, False)  # tls or ssl

		# Determine ad_ldap_base with exact case
		try:
			self.lo_ad = univention.uldap.access(
				host=self.ad_ldap_host, port=int(self.ad_ldap_port),
				base='', binddn=None, bindpw=None, start_tls=tls_mode,
				use_ldaps=ldaps, ca_certfile=self.ad_ldap_certificate)
			default_naming_context = self._get_from_root_dse(['defaultNamingContext'])
			self.ad_ldap_base = default_naming_context['defaultNamingContext'][0]
		except Exception as ex:
			ud.debug(ud.LDAP, ud.ERROR, 'Failed to lookup AD LDAP base, using UCR value: %s' % ex)

		if self.baseConfig.is_true('%s/ad/ldap/kerberos' % self.CONFIGBASENAME):
			os.environ['KRB5CCNAME'] = '/var/cache/univention-ad-connector/krb5.cc'
			self.get_kerberos_ticket()
			auth = ldap.sasl.gssapi("")
			self.lo_ad = univention.uldap.access(host=self.ad_ldap_host, port=int(self.ad_ldap_port), base=self.ad_ldap_base, binddn=None, bindpw=self.ad_ldap_bindpw, start_tls=tls_mode, use_ldaps=ldaps, ca_certfile=self.ad_ldap_certificate, decode_ignorelist=BINARY_ATTRIBUTES)
			self.get_kerberos_ticket()
			self.lo_ad.lo.sasl_interactive_bind_s("", auth)
		else:
			self.lo_ad = univention.uldap.access(host=self.ad_ldap_host, port=int(self.ad_ldap_port), base=self.ad_ldap_base, binddn=self.ad_ldap_binddn, bindpw=self.ad_ldap_bindpw, start_tls=tls_mode, use_ldaps=ldaps, ca_certfile=self.ad_ldap_certificate, decode_ignorelist=BINARY_ATTRIBUTES)

		self.lo_ad.lo.set_option(ldap.OPT_REFERRALS, 0)

	# encode string to unicode
	def encode(self, string):
		try:
			return unicode(string)
		except:  # FIXME: which exception is to be caught?
			return unicode(string, 'Latin-1')

	def _get_lastUSN(self):
		return max(self.__lastUSN, int(self._get_config_option('AD', 'lastUSN')))

	def get_lastUSN(self):
		return self._get_lastUSN()

	def _commit_lastUSN(self):
		self._set_config_option('AD', 'lastUSN', str(self.__lastUSN))

	def _set_lastUSN(self, lastUSN):
		ud.debug(ud.LDAP, ud.INFO, "_set_lastUSN: new lastUSN is: %s" % lastUSN)
		self.__lastUSN = lastUSN

	def __encode_GUID(self, GUID):
		return base64.b64encode(GUID).decode('ASCII')

	def _get_DN_for_GUID(self, GUID):
		return self._get_config_option('AD GUID', self.__encode_GUID(GUID))

	def _set_DN_for_GUID(self, GUID, DN):
		self._set_config_option('AD GUID', self.__encode_GUID(GUID), DN)

	def _remove_GUID(self, GUID):
		self._remove_config_option('AD GUID', self.__encode_GUID(GUID))

	# handle rejected Objects
	def _save_rejected(self, id, dn):
		self._set_config_option('AD rejected', str(id), dn)

	def _get_rejected(self, id):
		return self._get_config_option('AD rejected', str(id))

	def _remove_rejected(self, id):
		self._remove_config_option('AD rejected', str(id))

	def _list_rejected(self):
		"""Returns rejected AD-objects"""
		return self._get_config_items('AD rejected')[:]

	def list_rejected(self):
		return self._list_rejected()

	def save_rejected(self, object):
		"""
		save object as rejected
		"""
		self._save_rejected(self.__get_change_usn(object), object['dn'])

	def remove_rejected(self, object):
		"""
		remove object from rejected
		"""
		self._remove_rejected(self.__get_change_usn(object), object['dn'])

	def addToCreationList(self, dn):
		if not dn.lower() in self.creation_list:
			self.creation_list.append(dn.lower())

	def removeFromCreationList(self, dn):
		self.creation_list = [s for s in self.creation_list if s != dn.lower()]

	def isInCreationList(self, dn):
		return dn.lower() in self.creation_list

	def parse_range_retrieval_attrs(self, ad_attrs, attr):
		for k in ad_attrs:
			m = self.range_retrieval_pattern.match(k)
			if not m or m.group(1) != attr:
				continue

			key = k
			values = ad_attrs[key]
			lower = int(m.group(2))
			upper = m.group(3)
			if upper != "*":
				upper = int(upper)
			break
		else:
			key = None
			values = []
			lower = 0
			upper = "*"
		return (key, values, lower, upper)

	def value_range_retrieval(self, ad_dn, ad_attrs, attr):
		(key, values, lower, upper) = self.parse_range_retrieval_attrs(ad_attrs, attr)
		ud.debug(ud.LDAP, ud.INFO, "value_range_retrieval: response:  %s" % (key,))
		if lower != 0:
			ud.debug(ud.LDAP, ud.ERROR, "value_range_retrieval: invalid range retrieval response:  %s" % (key,))
			raise ldap.PROTOCOL_ERROR
		all_values = values

		while upper != "*":
			next_key = "%s;range=%d-*" % (attr, upper + 1)
			ad_attrs = self.get_object(ad_dn, [next_key])
			returned_before = upper
			(key, values, lower, upper) = self.parse_range_retrieval_attrs(ad_attrs, attr)
			if lower != returned_before + 1:
				ud.debug(ud.LDAP, ud.ERROR, "value_range_retrieval: invalid range retrieval response: asked for %s but got %s" % (next_key, key))
				raise ldap.PARTIAL_RESULTS
			ud.debug(ud.LDAP, ud.INFO, "value_range_retrieval: response:  %s" % (key,))
			all_values.extend(values)
		return all_values

	def get_ad_members(self, ad_dn, ad_attrs):
		ad_members = ad_attrs.get('member', [])
		if not ad_members:
			ad_members = self.value_range_retrieval(ad_dn, ad_attrs, 'member')
			ad_attrs['member'] = ad_members
		return [x.decode('UTF-8') for x in ad_members]

	def get_object(self, dn, attrlist=None):
		try:
			ad_object = self.lo_ad.get(compatible_modstring(dn), attr=attrlist)
			try:
				ud.debug(ud.LDAP, ud.INFO, "get_object: got object: %s" % dn)
			except:  # FIXME: which exception is to be caught?
				ud.debug(ud.LDAP, ud.INFO, "get_object: got object: <print failed>")
			return encode_ad_object(ad_object)
		except (ldap.SERVER_DOWN, SystemExit):
			raise
		except:  # FIXME: which exception is to be caught?
			pass

	def __get_change_usn(self, samba_object):
		'''
		get change USN as max(uSNCreated, uSNChanged)
		'''
		if not samba_object:
			return 0
		usncreated = int(samba_object['attributes'].get('uSNCreated', [b'0'])[0])
		usnchanged = int(samba_object['attributes'].get('uSNChanged', [b'0'])[0])
		return max(usnchanged, usncreated)

	def __search_ad(self, base=None, scope=ldap.SCOPE_SUBTREE, filter='', attrlist=[], show_deleted=False):
		'''
		search ad
		'''

		if not base:
			base = self.lo_ad.base

		ctrls = [
			SimplePagedResultsControl(True, PAGE_SIZE, ''),  # Must be the first
			LDAPControl(LDB_CONTROL_DOMAIN_SCOPE_OID, criticality=0),  # Don't show referrals
		]

		if show_deleted:
			ctrls.append(LDAPControl(LDAP_SERVER_SHOW_DELETED_OID, criticality=1))

		ud.debug(ud.LDAP, ud.INFO, "Search AD with filter: %s" % filter)
		msgid = self.lo_ad.lo.search_ext(base, scope, filter, attrlist, serverctrls=ctrls, timeout=-1, sizelimit=0)

		res = []
		pages = 0
		while True:
			pages += 1
			rtype, rdata, rmsgid, serverctrls = self.lo_ad.lo.result3(msgid)
			res += rdata

			pctrls = [
				c
				for c in serverctrls
				if c.controlType == SimplePagedResultsControl.controlType
			]
			if pctrls:
				cookie = pctrls[0].cookie
				if cookie:
					if pages > 1:
						ud.debug(ud.LDAP, ud.PROCESS, "AD search continues, already found %s objects" % len(res))
					ctrls[0].cookie = cookie
					msgid = self.lo_ad.lo.search_ext(base, scope, filter, attrlist, serverctrls=ctrls, timeout=-1, sizelimit=0)
				else:
					break
			else:
				ud.debug(ud.LDAP, ud.WARN, "AD ignores PAGE_RESULTS")
				break

		return fix_dn_in_search(res)

	def __search_ad_changes(self, show_deleted=False, filter=''):
		'''
		search ad for changes since last update (changes greater lastUSN)
		'''
		lastUSN = self._get_lastUSN()
		# filter erweitern um "(|(uSNChanged>=lastUSN+1)(uSNCreated>=lastUSN+1))"
		# +1 da suche nur nach '>=', nicht nach '>' möglich

		def _ad_changes_filter(attribute, lowerUSN, higherUSN=''):
			if higherUSN:
				usn_filter_format = '(&({attribute}>={lower_usn!e})({attribute}<={higher_usn!e}))'
			else:
				usn_filter_format = '({attribute}>={lower_usn!e})'

			return format_escaped(usn_filter_format, attribute=attribute, lower_usn=lowerUSN, higher_usn=higherUSN)

		def search_ad_changes_by_attribute(usnFilter, last_usn):
			if filter != '':
				usnFilter = '(&(%s)(%s))' % (filter, usnFilter)

			res = self.__search_ad_partitions(filter=usnFilter, show_deleted=show_deleted)

			def _sortkey(element):
				usn_changed = int(element[1]['uSNChanged'][0])
				usn_created = int(element[1]['uSNCreated'][0])
				if last_usn <= 0:
					return usn_created
				return usn_created if usn_created > last_usn else usn_changed
			return sorted(res, key=_sortkey)

		# search for objects with uSNCreated and uSNChanged in the known range
		try:
			usn_filter = _ad_changes_filter('uSNCreated', lastUSN + 1)
			if lastUSN > 0:
				# During the init phase we have to search for created and changed objects
				usn_filter = '(|%s%s)' % (_ad_changes_filter('uSNChanged', lastUSN + 1), usn_filter)
			return search_ad_changes_by_attribute(usn_filter, lastUSN)
		except (ldap.SERVER_DOWN, SystemExit):
			raise
		except ldap.SIZELIMIT_EXCEEDED:
			# The LDAP control page results was not successful. Without this control
			# AD does not return more than 1000 results. We are going to split the
			# search.
			highestCommittedUSN = self.__get_highestCommittedUSN()
			tmpUSN = lastUSN
			ud.debug(ud.LDAP, ud.PROCESS, "Need to split results. highest USN is %s, lastUSN is %s" % (highestCommittedUSN, lastUSN))
			returnObjects = []
			while (tmpUSN != highestCommittedUSN):
				lastUSN = tmpUSN
				tmpUSN += 999
				if tmpUSN > highestCommittedUSN:
					tmpUSN = highestCommittedUSN

				ud.debug(ud.LDAP, ud.INFO, "__search_ad_changes: search between USNs %s and %s" % (lastUSN + 1, tmpUSN))

				usn_filter = _ad_changes_filter('uSNCreated', lastUSN + 1, tmpUSN)
				if lastUSN > 0:
					# During the init phase we have to search for created and changed objects
					usn_filter = '(|%s%s)' % (_ad_changes_filter('uSNChanged', lastUSN + 1, tmpUSN), usn_filter)
				returnObjects += search_ad_changes_by_attribute(usn_filter, lastUSN)

			return returnObjects

	def __search_ad_changeUSN(self, changeUSN, show_deleted=True, filter=''):
		'''
		search ad for change with id
		'''

		usn_filter = format_escaped('(|(uSNChanged={0!e})(uSNCreated={0!e}))', changeUSN)
		if filter != '':
			usn_filter = '(&({}){})'.format(filter, usn_filter)

		return self.__search_ad_partitions(filter=usn_filter, show_deleted=show_deleted)

	def __dn_from_deleted_object(self, object):
		'''
		gets dn for deleted object (original dn before the object was moved into the deleted objects container)
		'''

		rdn = object['dn'].split('\\0ADEL:')[0]
		last_known_parent = object['attributes'].get('lastKnownParent', [b''])[0].decode('UTF-8')
		if last_known_parent and '\\0ADEL:' in last_known_parent:
			dn, attr = self.__get_ad_deleted(last_known_parent)
			last_known_parent = self.__dn_from_deleted_object({'dn': dn, 'attributes': attr})

		if last_known_parent:
			ud.debug(ud.LDAP, ud.INFO, "__dn_from_deleted_object: get DN from lastKnownParent (%r) and rdn (%r)" % (last_known_parent, rdn))
			return ldap.dn.dn2str(str2dn(rdn) + str2dn(last_known_parent))
		else:
			ud.debug(ud.LDAP, ud.WARN, 'lastKnownParent attribute for deleted object rdn="%s" was not set, so we must ignore the object' % rdn)
			return None

	def __object_from_element(self, element):
		"""
		gets an object from an AD LDAP-element, implements necessary mapping

		:param element:
			(dn, attributes) tuple from a search in AD-LDAP
		:ptype element: tuple
		"""
		if element[0] == 'None' or element[0] is None:
			return None  # referrals

		object = {}
		object['dn'] = element[0]
		object['attributes'] = element[1]
		deleted_object = False

		# modtype
		if b'TRUE' in element[1].get('isDeleted', []):
			object['modtype'] = 'delete'
			deleted_object = True
		else:
			# check if is moved
			olddn = self._get_DN_for_GUID(element[1]['objectGUID'][0])
			ud.debug(ud.LDAP, ud.INFO, "object_from_element: olddn: %s" % olddn)
			if olddn and not olddn.lower() == element[0].lower() and ldap.explode_rdn(olddn.lower()) == ldap.explode_rdn(element[0].lower()):
				object['modtype'] = 'move'
				object['olddn'] = olddn
				ud.debug(ud.LDAP, ud.INFO, "object_from_element: detected move of AD-Object")
			else:
				object['modtype'] = 'modify'
				if olddn and not olddn.lower() == element[0].lower():  # modrdn
					object['olddn'] = olddn

		object['attributes'] = element[1]
		for key in object['attributes'].keys():
			vals = object['attributes'][key][:]
			if key not in BINARY_ATTRIBUTES:
				vals = [self.encode(value) for value in vals]
			object['attributes'][key] = vals

		if deleted_object:  # dn is in deleted-objects-container, need to parse to original dn
			object['deleted_dn'] = object['dn']
			object['dn'] = self.__dn_from_deleted_object(object)
			ud.debug(ud.LDAP, ud.PROCESS, "object_from_element: DN of removed object: %r" % (object['dn'],))
			# self._remove_GUID(element[1]['objectGUID'][0]) # cache is not needed anymore?

			if not object['dn']:
				return None
		return object

	def __identify(self, object):
		if not object or 'attributes' not in object:
			return None
		for key in self.property.keys():
			if self._filter_match(self.property[key].con_search_filter, object['attributes']):
				return key

	def __update_lastUSN(self, object):
		"""
		Update der lastUSN
		"""
		if self.__get_change_usn(object) > self._get_lastUSN():
			self._set_lastUSN(self.__get_change_usn(object))

	def __get_highestCommittedUSN(self):
		'''
		get highestCommittedUSN stored in AD
		'''
		try:
			return int(self.ad_search_ext_s(
				'',  # base
				ldap.SCOPE_BASE,
				'objectclass=*',  # filter
				['highestCommittedUSN'],
			)[0][1]['highestCommittedUSN'][0].decode('ASCII'))
		except ldap.LDAPError:
			self._debug_traceback(ud.ERROR, "search for highestCommittedUSN failed")
			print("ERROR: initial search in AD failed, check network and configuration")
			return 0

	def set_primary_group_to_ucs_user(self, object_key, object_ucs):
		'''
		check if correct primary group is set to a fresh UCS-User
		'''

		rid_filter = format_escaped("(samaccountname={0!e})", object_ucs['username'])
		ad_group_rid_resultlist = self.__search_ad(base=self.lo_ad.base, scope=ldap.SCOPE_SUBTREE, filter=rid_filter, attrlist=['dn', 'primaryGroupID'])

		if not ad_group_rid_resultlist[0][0] in [b'None', b'', None]:

			ad_group_rid = ad_group_rid_resultlist[0][1]['primaryGroupID'][0].decode('UTF-8')

			ud.debug(ud.LDAP, ud.INFO, "set_primary_group_to_ucs_user: AD rid: %r" % ad_group_rid)
			ldap_group_filter = format_escaped("(objectSid={0!e}-{1!e})", self.ad_sid, ad_group_rid)
			ldap_group_ad = self.__search_ad(base=self.lo_ad.base, scope=ldap.SCOPE_SUBTREE, filter=ldap_group_filter)

			if not ldap_group_ad[0][0]:
				ud.debug(ud.LDAP, ud.ERROR, "ad.set_primary_group_to_ucs_user: Primary Group in AD not found (not enough rights?), sync of this object will fail!")
			ucs_group = self._object_mapping('group', {'dn': ldap_group_ad[0][0], 'attributes': ldap_group_ad[0][1]}, object_type='con')

			object_ucs['primaryGroup'] = ucs_group['dn']

	def primary_group_sync_from_ucs(self, key, object):  # object mit ad-dn
		'''
		sync primary group of an ucs-object to ad
		'''

		object_key = key
		object_ucs = self._object_mapping(object_key, object)

		ldap_object_ucs = self.get_ucs_ldap_object(object_ucs['dn'])
		if not ldap_object_ucs:
			ud.debug(ud.LDAP, ud.PROCESS, 'primary_group_sync_from_ucs: The UCS object (%s) was not found. The object was removed.' % object_ucs['dn'])
			return

		ldap_object_ad = self.get_object(object['dn'])
		if not ldap_object_ad:
			ud.debug(ud.LDAP, ud.PROCESS, 'primary_group_sync_from_ucs: The AD object (%s) was not found. The object was removed.' % object['dn'])
			return

		ucs_group_id = ldap_object_ucs['gidNumber'][0].decode('UTF-8')  # FIXME: fails if group does not exists
		ucs_group_filter = format_escaped('(&(objectClass=univentionGroup)(gidNumber={0!e}))', ucs_group_id)
		ucs_group_ldap = self.search_ucs(filter=ucs_group_filter)  # is empty !?

		if ucs_group_ldap == []:
			ud.debug(ud.LDAP, ud.WARN, "primary_group_sync_from_ucs: failed to get UCS-Group with gid %s, can't sync to AD" % ucs_group_id)
			return

		member_key = 'group'  # FIXME: generate by identify-function ?
		ad_group_object = self._object_mapping(member_key, {'dn': ucs_group_ldap[0][0], 'attributes': ucs_group_ldap[0][1]}, 'ucs')
		ldap_object_ad_group = self.get_object(ad_group_object['dn'])
		# FIXME: default value "513" should be configurable
		rid = b'513'
		if 'objectSid' in ldap_object_ad_group:
			rid = decode_sid(ldap_object_ad_group['objectSid'][0]).rsplit('-', 1)[-1].encode('ASCII')

		# to set a valid primary group we need to:
		# - check if either the primaryGroupID is already set to rid or
		# - prove that the user is member of this group, so: at first we need the ad_object for this element
		# this means we need to map the user to get it's AD-DN which would call this function recursively

		if "primaryGroupID" in ldap_object_ad and ldap_object_ad["primaryGroupID"][0] == rid:
			ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_from_ucs: primary Group is correct, no changes needed")
			return True  # nothing left to do
		else:
			ad_members = self.get_ad_members(ad_group_object['dn'], ldap_object_ad_group)

			ad_members_lower = [x.lower() for x in ad_members]
			if object['dn'].lower() not in ad_members_lower:  # add as member
				ad_members.append(object['dn'])
				ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_from_ucs: primary Group needs change of membership in AD")
				self.lo_ad.lo.modify_s(ad_group_object['dn'], [(ldap.MOD_REPLACE, 'member', [x.encode('UTF-8') for x in ad_members])])

			# set new primary group
			ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_from_ucs: changing primary Group in AD")
			self.lo_ad.lo.modify_s(object['dn'], [(ldap.MOD_REPLACE, 'primaryGroupID', rid)])

			# If the user is not member in UCS of the previous primary group, the user must
			# be removed from this group in AD: https://forge.univention.org/bugzilla/show_bug.cgi?id=26514
			prev_samba_primary_group_id = ldap_object_ad['primaryGroupID'][0].decode('UTF-8')
			ad_group_filter = format_escaped('(objectSid={0!e}-{1!e})', self.ad_sid, prev_samba_primary_group_id)
			ad_group = self.__search_ad(base=self.lo_ad.base, scope=ldap.SCOPE_SUBTREE, filter=ad_group_filter)
			ucs_group_object = self._object_mapping('group', {'dn': ad_group[0][0], 'attributes': ad_group[0][1]}, 'con')
			ucs_group = self.get_ucs_ldap_object(ucs_group_object['dn'])
			is_member = False
			for member in ucs_group.get('uniqueMember', []):
				if member.lower() == object_ucs['dn'].lower():
					is_member = True
					break
			if not is_member:
				# remove AD member from previous group
				ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_from_ucs: remove AD member from previous group")
				self.lo_ad.lo.modify_s(ad_group[0][0], [(ldap.MOD_DELETE, 'member', [object['dn'].encode('UTF-8')])])

			return True

	def primary_group_sync_to_ucs(self, key, object):  # object mit ucs-dn
		'''
		sync primary group of an ad-object to ucs
		'''

		object_key = key

		ad_object = self._object_mapping(object_key, object, 'ucs')
		ldap_object_ad = self.get_object(ad_object['dn'])
		ad_group_rid = ldap_object_ad['primaryGroupID'][0].decode('UTF-8')
		ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_to_ucs: AD rid: %s" % ad_group_rid)

		ldap_group_filter = format_escaped('(objectSid={0!e}-{1!e})', self.ad_sid, ad_group_rid)
		ldap_group_ad = self.__search_ad(base=self.lo_ad.base, scope=ldap.SCOPE_SUBTREE, filter=ldap_group_filter)

		ucs_group = self._object_mapping('group', {'dn': ldap_group_ad[0][0], 'attributes': ldap_group_ad[0][1]})

		ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_to_ucs: ucs-group: %s" % ucs_group['dn'])

		ucs_admin_object = univention.admin.objects.get(self.modules[object_key], co='', lo=self.lo, position='', dn=object['dn'])
		ucs_admin_object.open()

		if not ucs_admin_object['primaryGroup'].lower() == ucs_group['dn'].lower():
			# need to set to dn with correct case or the ucs-module will fail
			new_group = ucs_group['dn'].lower()
			ucs_admin_object['primaryGroup'] = new_group
			ucs_admin_object.modify()

			ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_to_ucs: changed primary Group in ucs")
		else:
			ud.debug(ud.LDAP, ud.INFO, "primary_group_sync_to_ucs: change of primary Group in ucs not needed")

	def object_memberships_sync_from_ucs(self, key, object):
		"""
		sync group membership in AD if object was changend in UCS
		"""
		ud.debug(ud.LDAP, ud.INFO, "object_memberships_sync_from_ucs: object: %s" % object)

		# search groups in UCS which have this object as member

		object_ucs = self._object_mapping(key, object)

		# Exclude primary group
		ucs_object_gid = object_ucs['attributes']['gidNumber'][0].decode('UTF-8')
		ucs_group_filter = format_escaped('(&(objectClass=univentionGroup)(uniqueMember={0!e})(!(gidNumber={1!e})))', object_ucs['dn'], ucs_object_gid)
		ucs_groups_ldap = self.search_ucs(filter=ucs_group_filter)

		if ucs_groups_ldap == []:
			ud.debug(ud.LDAP, ud.INFO, "object_memberships_sync_from_ucs: No group-memberships in UCS for %s" % object['dn'])
			return

		ud.debug(ud.LDAP, ud.INFO, "object_memberships_sync_from_ucs: is member in %s groups " % len(ucs_groups_ldap))

		for groupDN, attributes in ucs_groups_ldap:
			if groupDN not in ['None', '', None]:
				ad_object = {'dn': groupDN, 'attributes': attributes, 'modtype': 'modify'}
				if not self._ignore_object('group', ad_object):
					sync_object = self._object_mapping('group', ad_object, 'ucs')
					sync_object_ad = self.get_object(sync_object['dn'])
					ad_group_object = {'dn': sync_object['dn'], 'attributes': sync_object_ad}
					if sync_object_ad:
						# self.group_members_sync_from_ucs( 'group', sync_object )
						self.one_group_member_sync_from_ucs(ad_group_object, object)

			self.__group_cache_ucs_append_member(groupDN, object_ucs['dn'])

	def __group_cache_ucs_append_member(self, group, member):
		member_cache = self.group_members_cache_ucs.setdefault(group.lower(), set())
		if member.lower() not in member_cache:
			ud.debug(ud.LDAP, ud.INFO, "__group_cache_ucs_append_member: Append user %r to UCS group member cache of %r" % (member, group))
			member_cache.add(member.lower())

	def group_members_sync_from_ucs(self, key, object):  # object mit ad-dn
		"""
		sync groupmembers in AD if changend in UCS
		"""

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: %s" % object)

		object_key = key
		object_ucs = self._object_mapping(object_key, object)
		object_ucs_dn = object_ucs['dn']

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: dn is: %r" % (object_ucs_dn,))
		ldap_object_ucs = self.get_ucs_ldap_object(object_ucs_dn)

		if not ldap_object_ucs:
			ud.debug(ud.LDAP, ud.PROCESS, 'group_members_sync_from_ucs:: The UCS object (%s) was not found. The object was removed.' % object_ucs_dn)
			return

		ldap_object_ucs_gidNumber = ldap_object_ucs['gidNumber'][0].decode('UTF-8')
		ucs_members = set(x.decode('UTF-8') for x in ldap_object_ucs.get('uniqueMember', []))
		ud.debug(ud.LDAP, ud.INFO, "ucs_members: %s" % ucs_members)

		# remove members which have this group as primary group (set same gidNumber)
		search_filter = format_escaped('(gidNumber={0!e})', ldap_object_ucs['gidNumber'][0])
		prim_members_ucs = self.lo.search(filter=search_filter, attr=['gidNumber'])

		# all dn's need to be lower-case so we can compare them later and put them in the group ucs cache:
		self.group_members_cache_ucs[object_ucs['dn'].lower()] = set()
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: UCS group member cache reset")

		for prim_object in prim_members_ucs:
			if prim_object[0].lower() in ucs_members:
				ucs_members.remove(prim_object[0].lower())

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: clean ucs_members: %s" % ucs_members)

		ldap_object_ad = self.get_object(object['dn'])
		if not ldap_object_ad:
			ud.debug(ud.LDAP, ud.PROCESS, 'group_members_sync_from_ucs:: The AD object (%s) was not found. The object was removed.' % object['dn'])
			return
		ad_members = set(self.get_ad_members(object['dn'], ldap_object_ad))
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: ad_members %s" % ad_members)

		# map members from UCS to AD and check if they exist
		ad_members_from_ucs = set()  # Code review comment: For some reason this is a list of lowercase DNs
		for member_dn in ucs_members:
			ad_dn = self.group_mapping_cache_ucs.get(member_dn.lower())
			if ad_dn and self.lo_ad.get(ad_dn, attr=['cn']):
				ud.debug(ud.LDAP, ud.INFO, "Found %s in group cache ucs: %s" % (member_dn, ad_dn))
				ad_members_from_ucs.append(ad_dn.lower())
				self.__group_cache_ucs_append_member(object_ucs['dn'], member_dn)
			else:
				ud.debug(ud.LDAP, ud.INFO, "Did not find %s in UCS group member cache" % member_dn)
				member_object = {'dn': member_dn, 'modtype': 'modify', 'attributes': self.lo.get(member_dn)}

				# can't sync them if users have no posix-account
				if 'gidNumber' not in member_object['attributes']:
					continue

				# check if this is members primary group, if true it shouldn't be added to ad
				if 'gidNumber' in member_object['attributes'] and 'gidNumber' in ldap_object_ucs and \
					member_object['attributes']['gidNumber'] == ldap_object_ucs['gidNumber']:
					# is primary group
					continue

				# print 'member_object: %s '%member_object
				for k in self.property.keys():
					if self.modules[k].identify(member_dn, member_object['attributes']):
						key = k
						break
				# print 'object key: %s' % key
				ad_dn = self._object_mapping(key, member_object, 'ucs')['dn']
				# check if dn exists in ad
				try:
					if self.lo_ad.get(ad_dn, attr=['cn']):  # search only for cn to suppress coding errors
						ad_members_from_ucs.add(ad_dn.lower())
						ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: Adding %s to UCS group member cache, value: %s" % (member_dn.lower(), ad_dn))
						self.group_mapping_cache_ucs[member_dn.lower()] = ad_dn
						self.__group_cache_ucs_append_member(object_ucs['dn'], member_dn)
				except (ldap.SERVER_DOWN, SystemExit):
					raise
				except Exception:  # FIXME: which exception is to be caught?
					self._debug_traceback(ud.PROCESS, "group_members_sync_from_ucs: failed to get AD dn for UCS group member %s, assume object doesn't exist" % member_dn)

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: UCS-members in ad_members_from_ucs %s" % ad_members_from_ucs)

		# check if members in AD don't exist in UCS, if true they need to be added in AD
		for member_dn in ad_members_from_ucs:
			if not member_dn.lower() in ad_members_from_ucs:
				try:
					ad_object = self.get_object(member_dn)

					mo_key = self.__identify_ad_type({'dn': member_dn, 'attributes': ad_object})
					ucs_dn = self._object_mapping(mo_key, {'dn': member_dn, 'attributes': ad_object})['dn']
					if not self.lo.get(ucs_dn, attr=['cn']):
						# Leave the following line commented out, as we don't want to keep the member in AD if it's not present in OpenLDAP
						# Note: in this case the membership gets removed even if the object itself is ignored for synchronization
						# ad_members_from_ucs.append(member_dn.lower())
						ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: Object exists only in AD [%s]" % ucs_dn)
					elif self._ignore_object(mo_key, {'dn': member_dn, 'attributes': ad_object}):
						# Keep the member in AD if it's also present in OpenLDAP but ignored in synchronization?
						ad_members_from_ucs.add(member_dn.lower())
						ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: Object ignored in AD [%s], key = [%s]" % (ucs_dn, mo_key))
				except ldap.SERVER_DOWN:
					raise
				except Exception:  # FIXME: which exception is to be caught?
					self._debug_traceback(ud.PROCESS, "group_members_sync_from_ucs: failed to get UCS dn for AD group member %s" % member_dn)

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: UCS-and AD-members in ad_members_from_ucs %s" % ad_members_from_ucs)

		# compare lists and generate modlist
		# direct compare is not possible, because ad_members_from_ucs are all lowercase, ad_members are not, so we need to iterate...
		# FIXME: should be done in the last iteration (above)

		# need to remove users from ad_members_from_ucs which have this group as primary group. may failed earlier if groupnames are mapped
		try:
			group_rid = decode_sid(fix_dn_in_search(self.lo_ad.lo.search_s(object['dn'], ldap.SCOPE_BASE, '(objectClass=*)', ['objectSid']))[0][1]['objectSid'][0]).rsplit('-', 1)[-1]
		except ldap.NO_SUCH_OBJECT:
			group_rid = None

		if group_rid:
			# search for members who have this as their primaryGroup
			prim_members_ad_filter = format_escaped('(primaryGroupID={0!e})', group_rid)
			prim_members_ad = self.__search_ad(self.lo_ad.base, ldap.SCOPE_SUBTREE, prim_members_ad_filter, ['cn'])

			for prim_dn, prim_object in prim_members_ad:
				if prim_dn not in ['None', '', None]:  # filter referrals
					if prim_dn.lower() in ad_members_from_ucs:
						ad_members_from_ucs.remove(prim_dn.lower())
					elif prim_dn in ad_members_from_ucs:
						# Code review comment: Obsolete? ad_members_from_ucs should be all lowercase at this point
						ad_members_from_ucs.remove(prim_dn)

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: ad_members_from_ucs without members with this as their primary group: %s" % ad_members_from_ucs)

		add_members = ad_members_from_ucs
		del_members = set()

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: members to add initialized: %s" % add_members)

		for member_dn in ad_members:
			ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: %s in ad_members_from_ucs?" % member_dn)
			member_dn_lower = member_dn.lower()
			if member_dn_lower in ad_members_from_ucs:
				ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: Yes")
				add_members.remove(member_dn_lower)
			else:
				if object['modtype'] == 'add':
					ud.debug(ud.LDAP, ud.PROCESS, "group_members_sync_from_ucs: %s is newly added. For this case don't remove current AD members." % (object['dn'].lower()))
				elif (member_dn_lower in self.group_members_cache_con.get(object['dn'].lower(), set())) or (self.property.get('group') and self.property['group'].sync_mode in ['write', 'none']):
					# FIXME: Should this really also be done if sync_mode for group is 'none'?
					# remove member only if he was in the cache on AD side
					# otherwise it is possible that the user was just created on AD and we are on the way back
					ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: No")
					del_members.add(member_dn)
				else:
					ud.debug(ud.LDAP, ud.PROCESS, "group_members_sync_from_ucs: %s was not found in AD group member cache of %s, don't delete" % (member_dn_lower, object['dn'].lower()))

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: members to add: %s" % add_members)
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_from_ucs: members to del: %s" % del_members)

		if add_members:
			self.lo_ad.lo.modify_s(compatible_modstring(object['dn']), [(ldap.MOD_ADD, 'member', list(map(compatible_modstring, add_members)))])
		if del_members:
			self.lo_ad.lo.modify_s(compatible_modstring(object['dn']), [(ldap.MOD_DELETE, 'member', list(map(compatible_modstring, del_members)))])

		return True

	def object_memberships_sync_to_ucs(self, key, object):
		"""
		sync group membership in UCS if object was changend in AD
		"""
		# disable this debug line, see Bug #12031
		# ud.debug(ud.LDAP, ud.INFO, "object_memberships_sync_to_ucs: object: %s" % object)

		self._object_mapping(key, object)

		if 'memberOf' in object['attributes']:
			for groupDN in object['attributes']['memberOf']:
				groupDN = groupDN.decode('UTF-8')
				ad_object = {'dn': groupDN, 'attributes': self.get_object(groupDN), 'modtype': 'modify'}
				if not self._ignore_object('group', ad_object):
					sync_object = self._object_mapping('group', ad_object)
					ldap_object_ucs = self.get_ucs_ldap_object(sync_object['dn'])
					ucs_group_object = {'dn': sync_object['dn'], 'attributes': ldap_object_ucs}
					ud.debug(ud.LDAP, ud.INFO, "object_memberships_sync_to_ucs: sync_object: %s" % ldap_object_ucs)
					# check if group exists in UCS, may fail
					# if the group will be synced later
					if ldap_object_ucs:
						self.one_group_member_sync_to_ucs(ucs_group_object, object)

				dn = object['attributes'].get('distinguishedName', [None])[0]
				if dn:
					groupDN_lower = groupDN.lower()
					member_cache = self.group_members_cache_con.setdefault(groupDN_lower, set())
					dn_lower = dn.decode('UTF-8').lower()
					if dn_lower not in member_cache:
						ud.debug(ud.LDAP, ud.INFO, "object_memberships_sync_to_ucs: Append user %s to AD group member cache of %s" % (dn_lower, groupDN_lower))
						member_cache.add(dn_lower)
				else:
					ud.debug(ud.LDAP, ud.INFO, "object_memberships_sync_to_ucs: Failed to append user %s to AD group member cache of %s" % (object['dn'].lower(), groupDN.lower()))

	def __compare_lowercase(self, dn, dn_list):
		"""
		Checks if dn is in dn_list
		"""
		for d in dn_list:
			if dn.lower() == d.lower():
				return True
		return False

	def one_group_member_sync_to_ucs(self, ucs_group_object, object):
		"""
		sync groupmembers in UCS if changend one member in AD
		"""
		# In AD the object['dn'] is member of the group sync_object

		ml = []
		if not self.__compare_lowercase(object['dn'].encode('UTF-8'), ucs_group_object['attributes'].get('uniqueMember', [])):
			ml.append((ldap.MOD_ADD, 'uniqueMember', [object['dn'].encode('UTF-8')]))

		if object['attributes'].get('uid'):
			uid = object['attributes']['uid'][0]
			if not self.__compare_lowercase(uid, ucs_group_object['attributes'].get('memberUid', [])):
				ml.append((ldap.MOD_ADD, 'memberUid', [uid]))

		if ml:
			ud.debug(ud.LDAP, ud.ALL, "one_group_member_sync_to_ucs: modlist: %s" % ml)
			try:
				self.lo.lo.modify_s(ucs_group_object['dn'], ml)
			except ldap.ALREADY_EXISTS:
				# The user is already member in this group or it is his primary group
				# This might happen, if we synchronize a rejected file with old information
				# See Bug #25709 Comment #17: https://forge.univention.org/bugzilla/show_bug.cgi?id=25709#c17
				ud.debug(ud.LDAP, ud.INFO, "one_group_member_sync_to_ucs: User is already member of the group: %s modlist: %s" % (ucs_group_object['dn'], ml))

	def one_group_member_sync_from_ucs(self, ad_group_object, object):
		"""
		sync groupmembers in AD if changend one member in AD
		"""
		ml = []
		if not self.__compare_lowercase(object['dn'].encode('UTF-8'), ad_group_object['attributes'].get('member', [])):
			ml.append((ldap.MOD_ADD, 'member', [object['dn'].encode('UTF-8')]))

		if ml:
			ud.debug(ud.LDAP, ud.ALL, "one_group_member_sync_from_ucs: modlist: %s" % ml)
			try:
				self.lo_ad.lo.modify_s(ad_group_object['dn'], ml)
			except ldap.ALREADY_EXISTS:
				# The user is already member in this group or it is his primary group
				# This might happen, if we synchronize a rejected file with old information
				# See Bug #25709 Comment #17: https://forge.univention.org/bugzilla/show_bug.cgi?id=25709#c17
				ud.debug(ud.LDAP, ud.INFO, "one_group_member_sync_from_ucs: User is already member of the group: %s modlist: %s" % (ad_group_object['dn'], ml))

		# The user has been removed from the cache. He must be added in any case
		ud.debug(ud.LDAP, ud.INFO, "one_group_member_sync_from_ucs: Append user %s to AD group member cache of %s" % (object['dn'].lower(), ad_group_object['dn'].lower()))
		self.group_members_cache_con.setdefault(ad_group_object['dn'].lower(), set()).add(object['dn'].lower())

	def __group_cache_con_append_member(self, group, member):
		group_lower = group.lower()
		member_cache = self.group_members_cache_con.setdefault(group_lower, set())
		member_lower = member.lower()
		if member_lower not in member_cache:
			ud.debug(ud.LDAP, ud.INFO, "__group_cache_con_append_member: Append user %s to AD group member cache of %s" % (member_lower, group_lower))
			member_cache.add(member_lower)

	def group_members_sync_to_ucs(self, key, object):
		"""
		sync groupmembers in UCS if changend in AD
		"""
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: object: %s" % object)

		object_key = key
		ad_object = self._object_mapping(object_key, object, 'ucs')
		ad_object_dn = ad_object['dn']
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: ad_object (mapped): %s" % ad_object)

		# FIXME: does not use dn-mapping-function
		ldap_object_ad = self.get_object(ad_object_dn)
		if not ldap_object_ad:
			ud.debug(ud.LDAP, ud.PROCESS, 'group_members_sync_to_ucs:: The AD object (%s) was not found. The object was removed.' % ad_object_dn)
			return

		ad_members = self.get_ad_members(object['dn'], ldap_object_ad)
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: ad_members %s" % ad_members)

		# search and add members which have this as their primaryGroup
		group_rid = decode_sid(ldap_object_ad['objectSid'][0]).rsplit('-', 1)[-1]
		prim_members_ad_filter = format_escaped('(primaryGroupID={0!e})', group_rid)
		prim_members_ad = self.__search_ad(self.lo_ad.base, ldap.SCOPE_SUBTREE, prim_members_ad_filter)
		for prim_dn, prim_object in prim_members_ad:
			if prim_dn not in ['None', '', None]:  # filter referrals
				ad_members.append(prim_dn)
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: clean ad_members %s" % ad_members)

		self.group_members_cache_con[ad_object_dn.lower()] = set()
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: AD group member cache reset")

		# lookup all current members of UCS group
		ldap_object_ucs = self.get_ucs_ldap_object(object['dn'])
		ucs_members = set(x.decode('UTF-8') for x in ldap_object_ucs.get('uniqueMember', []))
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: ucs_members: %s" % ucs_members)

		# map members from AD to UCS and check if they exist
		ucs_members_from_ad = {'user': [], 'group': [], 'unknown': []}
		dn_mapping_ucs_member_to_ad = {}
		for member_dn in ad_members:
			ucs_dn = self.group_member_mapping_cache_con.get(member_dn.lower())
			if ucs_dn:
				ud.debug(ud.LDAP, ud.INFO, "Found %s in AD group member cache: DN: %s" % (member_dn, ucs_dn))
				ucs_members_from_ad['unknown'].append(ucs_dn.lower())
				dn_mapping_ucs_member_to_ad[ucs_dn.lower()] = member_dn
				self.__group_cache_con_append_member(ad_object_dn, member_dn)
			else:
				ud.debug(ud.LDAP, ud.INFO, "Did not find %s in AD group member cache" % member_dn)
				member_object = self.get_object(member_dn)
				if member_object:
					mo_key = self.__identify_ad_type({'dn': member_dn, 'attributes': member_object})
					if not mo_key:
						ud.debug(ud.LDAP, ud.WARN, "group_members_sync_to_ucs: failed to identify object type of AD group member, ignore membership: %s" % member_dn)
						continue  # member is an object which will not be synced
					if self._ignore_object(mo_key, {'dn': member_dn, 'attributes': member_object}):
						ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: Object dn %s should be ignored, ignore membership" % member_dn)
						continue

					ucs_dn = self._object_mapping(mo_key, {'dn': member_dn, 'attributes': member_object})['dn']
					ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: mapped AD group member to ucs DN %s" % ucs_dn)

					dn_mapping_ucs_member_to_ad[ucs_dn.lower()] = member_dn

					try:
						if self.lo.get(ucs_dn):
							ucs_members_from_ad['unknown'].append(ucs_dn.lower())
							self.group_member_mapping_cache_con[member_dn.lower()] = ucs_dn
							self.__group_cache_con_append_member(ad_object_dn, member_dn)
						else:
							ud.debug(ud.LDAP, ud.INFO, "Failed to find %s via self.lo.get" % ucs_dn)
					except ldap.SERVER_DOWN:
						raise
					except Exception:  # FIXME: which exception is to be caught?
						self._debug_traceback(ud.PROCESS, "group_members_sync_to_ucs: failed to get UCS dn for AD group member %s, assume object doesn't exist" % member_dn)

		# build an internal cache
		cache = {}

		# check if members in UCS don't exist in AD, if true they need to be added in UCS
		for member_dn in ucs_members:
			member_dn_lower = member_dn.lower()
			if not (member_dn_lower in ucs_members_from_ad['user'] or member_dn_lower in ucs_members_from_ad['group'] or member_dn_lower in ucs_members_from_ad['unknown'] or member_dn_lower in ucs_members_from_ad['windowscomputer']):
				try:
					cache[member_dn] = self.lo.get(member_dn)
					ucs_object = {'dn': member_dn, 'modtype': 'modify', 'attributes': cache[member_dn]}

					if self._ignore_object(key, object):
						continue

					for k in self.property.keys():
						if self.modules[k].identify(member_dn, ucs_object['attributes']):
							ad_dn = self._object_mapping(k, ucs_object, 'ucs')['dn']

							if not dn_mapping_ucs_member_to_ad.get(member_dn_lower):
								dn_mapping_ucs_member_to_ad[member_dn_lower] = ad_dn

							ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: search for: %s" % ad_dn)
							# search only for cn to suppress coding errors
							if not self.lo_ad.get(ad_dn, attr=['cn']):
								# member does not exist in AD but should
								# stay a member in UCS
								ucs_members_from_ad[k].append(member_dn_lower)
							break
				except ldap.SERVER_DOWN:
					raise
				except Exception:  # FIXME: which exception is to be caught?
					self._debug_traceback(ud.PROCESS, "group_members_sync_to_ucs: failed to get AD dn for UCS group member %s" % member_dn)

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: dn_mapping_ucs_member_to_ad=%s" % (dn_mapping_ucs_member_to_ad))
		add_members = copy.deepcopy(ucs_members_from_ad)
		del_members = {'user': [], 'group': [], 'windowscomputer': [], }

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: members to add initialized: %s" % add_members)

		for member_dn in ucs_members:
			member_dn_lower = member_dn.lower()
			if member_dn_lower in ucs_members_from_ad['user']:
				add_members['user'].remove(member_dn_lower)
			elif member_dn_lower in ucs_members_from_ad['group']:
				add_members['group'].remove(member_dn_lower)
			elif member_dn_lower in ucs_members_from_ad['unknown']:
				add_members['unknown'].remove(member_dn_lower)
			elif member_dn_lower in ucs_members_from_ad['windowscomputer']:
				add_members['windowscomputer'].remove(member_dn_lower)
			else:
				# remove member only if he was in the cache
				# otherwise it is possible that the user was just created on UCS

				if (member_dn_lower in self.group_members_cache_ucs.get(object['dn'].lower(), set())) or (self.property.get('group') and self.property['group'].sync_mode in ['read', 'none']):
					# FIXME: Should this really also be done if sync_mode for group is 'none'?
					ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: %s was found in UCS group member cache of %s" % (member_dn_lower, object['dn'].lower()))
					ucs_object_attr = cache.get(member_dn)
					if not ucs_object_attr:
						ucs_object_attr = self.lo.get(member_dn)
						cache[member_dn] = ucs_object_attr
					ucs_object = {'dn': member_dn, 'modtype': 'modify', 'attributes': ucs_object_attr}

					for k in self.property.keys():
						# identify if DN is a user or a group (will be ignored it is a host)
						if self.modules[k].identify(member_dn, ucs_object['attributes']):
							if not self._ignore_object(k, ucs_object):
								del_members[k].append(member_dn)
							break
				else:
					ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: %s was not found in UCS group member cache of %s, don't delete" % (member_dn_lower, object['dn'].lower()))

		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: members to add: %s" % add_members)
		ud.debug(ud.LDAP, ud.INFO, "group_members_sync_to_ucs: members to del: %s" % del_members)

		if add_members['user'] or add_members['group'] or del_members['user'] or del_members['group'] or add_members['unknown'] or add_members['windowscomputer'] or del_members['windowscomputer']:
			ucs_admin_object = univention.admin.objects.get(self.modules[object_key], co='', lo=self.lo, position='', dn=object['dn'])
			ucs_admin_object.open()

			uniqueMember_add = add_members['user'] + add_members['group'] + add_members['unknown'] + add_members['windowscomputer']
			uniqueMember_del = del_members['user'] + del_members['group'] + del_members['windowscomputer']
			memberUid_add = []
			memberUid_del = []
			for member in add_members['user']:
				(_rdn_attribute, uid, _flags) = str2dn(member)[0][0]
				memberUid_add.append(uid)
			for member in add_members['unknown'] + add_members['windowscomputer']:  # user or group?
				ucs_object_attr = self.lo.get(member)
				uid = ucs_object_attr.get('uid')
				if uid:
					memberUid_add.append(uid[0].decode('UTF-8'))
			for member in del_members['user']:
				(_rdn_attribute, uid, _flags) = str2dn(member)[0][0]
				memberUid_del.append(uid)
			for member in del_members['windowscomputer']:
				ucs_object_attr = self.lo.get(member)
				uid = ucs_object_attr.get('uid')
				if uid:
					memberUid_del.append(uid[0])
			if uniqueMember_del or memberUid_del:
				ucs_admin_object.fast_member_remove(uniqueMember_del, memberUid_del, ignore_license=True)
			if uniqueMember_add or memberUid_del:
				ucs_admin_object.fast_member_add(uniqueMember_add, memberUid_add)

	def set_userPrincipalName_from_ucr(self, key, object):
		object_key = key
		object_ucs = self._object_mapping(object_key, object)
		ldap_object_ad = self.get_object(object['dn'])
		modlist = None
		if 'userPrincipalName' not in ldap_object_ad:
			# add missing userPrincipalName
			kerberosdomain = self.baseConfig.get('%s/ad/mapping/kerberosdomain' % self.CONFIGBASENAME, None)
			if kerberosdomain:
				ucs_admin_object = univention.admin.objects.get(self.modules[object_key], co='', lo=self.lo, position='', dn=object_ucs['dn'])
				ucs_admin_object.open()
				userPrincipalName = "%s@%s" % (ucs_admin_object['username'], kerberosdomain)
				modlist = [(ldap.MOD_REPLACE, 'userPrincipalName', [userPrincipalName])]
		else:
			# update userPrincipalName
			if self.baseConfig.is_true('%s/ad/mapping/sync/userPrincipalName' % self.CONFIGBASENAME, True):
				ucs_admin_object = univention.admin.objects.get(self.modules[object_key], co='', lo=self.lo, position='', dn=object_ucs['dn'])
				ucs_admin_object.open()
				if ucs_admin_object['username'] + '@' not in ldap_object_ad['userPrincipalName'][0]:
					if '@' in ldap_object_ad['userPrincipalName'][0]:
						princ = ldap_object_ad['userPrincipalName'][0].split('@', 1)[1]
						modlist = [(ldap.MOD_REPLACE, 'userPrincipalName', [ucs_admin_object['username'] + '@' + princ])]
		if modlist:
			ud.debug(ud.LDAP, ud.INFO, "set_userPrincipalName_from_ucr: set kerberos principle for AD user %s with modlist %s " % (object['dn'], modlist))
			self.lo_ad.lo.modify_s(compatible_modstring(object['dn']), compatible_modlist(modlist))

	def disable_user_from_ucs(self, key, object):
		object_key = key

		object_ucs = self._object_mapping(object_key, object)
		ldap_object_ad = self.get_object(object['dn'])

		ucs_admin_object = univention.admin.objects.get(self.modules[object_key], co='', lo=self.lo, position='', dn=object_ucs['dn'])
		ucs_admin_object.open()

		modlist = []

		ud.debug(ud.LDAP, ud.INFO, "Disabled state: %s" % ucs_admin_object['disabled'].lower())
		if not (ucs_admin_object['disabled'].lower() in ['none', '0']):
			# user disabled in UCS
			if 'userAccountControl' in ldap_object_ad and (int(ldap_object_ad['userAccountControl'][0]) & 2) == 0:
				# user enabled in AD -> change
				res = str(int(ldap_object_ad['userAccountControl'][0]) | 2).encode('ASCII')
				modlist.append((ldap.MOD_REPLACE, 'userAccountControl', [res]))
		else:
			# user enabled in UCS
			if 'userAccountControl' in ldap_object_ad and (int(ldap_object_ad['userAccountControl'][0]) & 2) > 0:
				# user disabled in AD -> change
				res = str(int(ldap_object_ad['userAccountControl'][0]) - 2).encode('ASCII')
				modlist.append((ldap.MOD_REPLACE, 'userAccountControl', [res]))

		# account expires
		# This value represents the number of 100 nanosecond intervals since January 1, 1601 (UTC). A value of 0 or 0x7FFFFFFFFFFFFFFF (9223372036854775807) indicates that the account never expires.
		if not ucs_admin_object['userexpiry']:
			# ucs account not expired
			if 'accountExpires' in ldap_object_ad and (int(ldap_object_ad['accountExpires'][0]) != int(9223372036854775807) or int(ldap_object_ad['accountExpires'][0]) == 0):
				# ad account expired -> change
				modlist.append((ldap.MOD_REPLACE, 'accountExpires', [b'9223372036854775807']))
		else:
			# ucs account expired
			if 'accountExpires' in ldap_object_ad and int(ldap_object_ad['accountExpires'][0]) != unix2ad_time(ucs_admin_object['userexpiry']):
				# ad account not expired -> change
				modlist.append((ldap.MOD_REPLACE, 'accountExpires', [str(unix2ad_time(ucs_admin_object['userexpiry'])).encode('ASCII')]))

		if modlist:
			ud.debug(ud.LDAP, ud.ALL, "disable_user_from_ucs: modlist: %s" % modlist)
			self.lo_ad.lo.modify_s(object['dn'], modlist)

	def disable_user_to_ucs(self, key, object):
		object_key = key

		ad_object = self._object_mapping(object_key, object, 'ucs')

		self.get_ucs_ldap_object(object['dn'])
		ldap_object_ad = self.get_object(ad_object['dn'])

		modified = 0
		ucs_admin_object = univention.admin.objects.get(self.modules[object_key], co='', lo=self.lo, position='', dn=object['dn'])
		ucs_admin_object.open()

		if 'userAccountControl' in ldap_object_ad and (int(ldap_object_ad['userAccountControl'][0]) & 2) == 0:
			# user enabled in AD
			if not ucs_admin_object['disabled'].lower() in ['none', '0']:
				# user disabled in UCS -> change
				ucs_admin_object['disabled'] = '0'
				modified = 1
		else:
			# user disabled in AD
			if ucs_admin_object['disabled'].lower() in ['none', '0']:
				# user enabled in UCS -> change
				ucs_admin_object['disabled'] = '1'
				modified = 1
		if 'accountExpires' in ldap_object_ad and (int(ldap_object_ad['accountExpires'][0]) == int(9223372036854775807) or int(ldap_object_ad['accountExpires'][0]) == 0):
			# ad account not expired
			if ucs_admin_object['userexpiry']:
				# ucs account expired -> change
				ucs_admin_object['userexpiry'] = None
				modified = 1
		else:
			# ad account expired
			ud.debug(ud.LDAP, ud.INFO, "sync account_expire:      adtime: %s    unixtime: %s" % (int(ldap_object_ad['accountExpires'][0]), ucs_admin_object['userexpiry']))

			if ad2unix_time(int(ldap_object_ad['accountExpires'][0])) != ucs_admin_object['userexpiry']:
				# ucs account not expired -> change
				ucs_admin_object['userexpiry'] = ad2unix_time(int(ldap_object_ad['accountExpires'][0]))
				modified = 1

		if modified:
			ucs_admin_object.modify()

	def initialize(self):
		print("--------------------------------------")
		print("Initialize sync from AD")
		if self._get_lastUSN() == 0:  # we startup new
			ud.debug(ud.LDAP, ud.PROCESS, "initialize AD: last USN is 0, sync all")
			# query highest USN in LDAP
			highestCommittedUSN = self.__get_highestCommittedUSN()

			# poll for all objects without deleted objects
			self.poll(show_deleted=False)

			# compare highest USN from poll with highest before poll, if the last changes deletes
			# the highest USN from poll is to low
			self._set_lastUSN(max(highestCommittedUSN, self._get_lastUSN()))

			self._commit_lastUSN()
			ud.debug(ud.LDAP, ud.INFO, "initialize AD: sync of all objects finished, lastUSN is %d", self.__get_highestCommittedUSN())
		else:
			self.resync_rejected()
			self.poll()
			self._commit_lastUSN()
		print("--------------------------------------")

	def resync_rejected(self):
		'''
		tries to resync rejected dn
		'''
		print("--------------------------------------")

		change_count = 0
		rejected = self._list_rejected()
		print("Sync %s rejected changes from AD to UCS" % len(rejected))
		sys.stdout.flush()
		for change_usn, dn in rejected:
			ud.debug(ud.LDAP, ud.PROCESS, 'sync to ucs: Resync rejected dn: %s' % (dn))
			try:
				sync_successfull = False
				elements = self.__search_ad_changeUSN(change_usn, show_deleted=True)
				if not elements or len(elements) < 1 or not elements[0][0]:
					ud.debug(ud.LDAP, ud.INFO, "rejected change with id %s not found, don't need to sync" % change_usn)
					self._remove_rejected(change_usn)
				elif len(elements) > 1 and not (elements[1][0] == 'None' or elements[1][0] is None):  # all except the first should be referrals
					ud.debug(ud.LDAP, ud.WARN, "more than one rejected object with id %s found, can't proceed" % change_usn)
				else:
					samba_object = self.__object_from_element(elements[0])
					property_key = self.__identify_ad_type(samba_object)
					if not property_key:  # TODO: still needed? (removed in s4)
						ud.debug(ud.LDAP, ud.INFO, "sync to ucs: Dropping reject for unidentified object %s" % (dn,))
						self._remove_rejected(id)
						continue
					mapped_object = self._object_mapping(property_key, samba_object)
					try:
						if not self._ignore_object(property_key, mapped_object) and not self._ignore_object(property_key, samba_object):
							sync_successfull = self.sync_to_ucs(property_key, mapped_object, dn, samba_object)
						else:
							sync_successfull = True
					except ldap.SERVER_DOWN:
						raise
					except Exception:  # FIXME: which exception is to be caught?
						self._debug_traceback(ud.ERROR, "sync of rejected object failed \n\t%s" % (samba_object['dn']))
						sync_successfull = False
					if sync_successfull:
						change_count += 1
						self._remove_rejected(change_usn)
						self.__update_lastUSN(samba_object)
						self._set_DN_for_GUID(elements[0][1]['objectGUID'][0], elements[0][0])
			except ldap.SERVER_DOWN:
				raise
			except Exception:
				self._debug_traceback(ud.ERROR, "unexpected Error during ad.resync_rejected")
		print("restored %s rejected changes" % change_count)
		print("--------------------------------------")
		sys.stdout.flush()

	def poll(self, show_deleted=True):
		'''
		poll for changes in AD
		'''
		# search from last_usn for changes
		change_count = 0
		changes = []
		try:
			changes = self.__search_ad_changes(show_deleted=show_deleted)
		except ldap.SERVER_DOWN:
			raise
		except Exception:  # FIXME: which exception is to be caught?
			self._debug_traceback(ud.WARN, "Exception during search_ad_changes")

		if self.profiling and changes:
			ud.debug(ud.LDAP, ud.PROCESS, "POLL FROM CON: Incoming %s" % (len(changes),))

		print("--------------------------------------")
		print("try to sync %s changes from AD" % len(changes))
		print("done:", end=' ')
		sys.stdout.flush()
		done = {'counter': 0}
		samba_object = None
		lastUSN = self._get_lastUSN()
		newUSN = lastUSN

		def print_progress(ignore=False):
			done['counter'] += 1
			message = '(%s)' if ignore else '%s'
			print(message % (done['counter'],), end=' ')
			sys.stdout.flush()

		# Check if the connection to UCS ldap exists. Otherwise re-create the session.
		try:
			self.search_ucs(scope=ldap.SCOPE_BASE)
		except ldap.SERVER_DOWN:
			ud.debug(ud.LDAP, ud.INFO, "UCS LDAP connection was closed, re-open the connection.")
			self.open_ucs()

		for element in changes:
			old_element = copy.deepcopy(element)
			samba_object = self.__object_from_element(element)

			if not samba_object:
				print_progress(True)
				continue

			property_key = self.__identify_ad_type(samba_object)
			if not property_key:
				ud.debug(ud.LDAP, ud.INFO, "ignoring not identified object dn: %r" % (samba_object['dn'],))
				newUSN = max(self.__get_change_usn(samba_object), newUSN)
				print_progress(True)
				continue

			if True:
					if self._ignore_object(property_key, samba_object):
						if samba_object['modtype'] == 'move':
							ud.debug(ud.LDAP, ud.INFO, "object_from_element: Detected a move of an AD object into a ignored tree: dn: %s" % samba_object['dn'])
							samba_object['deleted_dn'] = samba_object['olddn']
							samba_object['dn'] = samba_object['olddn']
							samba_object['modtype'] = 'delete'
							# check the move target
						else:
							self.__update_lastUSN(samba_object)
							print_progress()
							continue

					if samba_object['dn'].find('\\0ACNF:') > 0:
						ud.debug(ud.LDAP, ud.PROCESS, 'Ignore conflicted object: %s' % samba_object['dn'])
						self.__update_lastUSN(samba_object)
						print_progress()
						continue

					sync_successfull = False
					try:
						try:
							mapped_object = self._object_mapping(property_key, samba_object)
							if not self._ignore_object(property_key, mapped_object):
								sync_successfull = self.sync_to_ucs(property_key, mapped_object, samba_object['dn'], samba_object)
							else:
								sync_successfull = True
						except univention.admin.uexceptions.ldapError as msg:
							if isinstance(msg.original_exception, ldap.SERVER_DOWN):
								raise msg.original_exception
							raise
					except ldap.SERVER_DOWN:
						ud.debug(ud.LDAP, ud.ERROR, "Got server down during sync, re-open the connection to UCS and AD")
						time.sleep(1)
						self.open_ucs()
						self.open_ad()
					except Exception:  # FIXME: which exception is to be caught?
						self._debug_traceback(ud.WARN, "Exception during poll/sync_to_ucs")

					if sync_successfull:
						change_count += 1
						newUSN = max(self.__get_change_usn(samba_object), newUSN)
						try:
							GUID = old_element[1]['objectGUID'][0]
							self._set_DN_for_GUID(GUID, old_element[0])
						except ldap.SERVER_DOWN:
							raise
						except Exception:  # FIXME: which exception is to be caught?
							self._debug_traceback(ud.WARN, "Exception during set_DN_for_GUID")
					else:
						ud.debug(ud.LDAP, ud.WARN, "sync to ucs was not successful, save rejected")
						ud.debug(ud.LDAP, ud.WARN, "object was: %s" % samba_object['dn'])
						self.save_rejected(samba_object)
						self.__update_lastUSN(samba_object)

					print_progress()

		print("")

		if newUSN != lastUSN:
			self._set_lastUSN(newUSN)
			self._commit_lastUSN()

		# return number of synced objects
		rejected = self._list_rejected()
		print("Changes from AD:  %s (%s saved rejected)" % (change_count, len(rejected)))
		print("--------------------------------------")
		sys.stdout.flush()
		if self.profiling and change_count:
			ud.debug(ud.LDAP, ud.PROCESS, "POLL FROM CON: Processed %s" % (change_count,))
		return change_count

	def __has_attribute_value_changed(self, attribute, old_ucs_object, new_ucs_object):
		return not old_ucs_object.get(attribute) == new_ucs_object.get(attribute)

	def _remove_dn_from_group_cache(self, con_dn=None, ucs_dn=None):
		if con_dn:
			try:
				ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: Removing %s from AD group member mapping cache" % con_dn)
				del self.group_member_mapping_cache_con[con_dn.lower()]
			except KeyError:
				ud.debug(ud.LDAP, ud.ALL, "sync_from_ucs: %s was not present in AD group member mapping cache" % con_dn)
				pass
		if ucs_dn:
			try:
				ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: Removing %s from UCS group member mapping cache" % ucs_dn)
				del self.group_member_mapping_cache_ucs[ucs_dn.lower()]
			except KeyError:
				ud.debug(ud.LDAP, ud.ALL, "sync_from_ucs: %s was not present in UCS group member mapping cache" % ucs_dn)
				pass

	def _update_group_member_cache(self, remove_con_dn=None, remove_ucs_dn=None, add_con_dn=None, add_ucs_dn=None):
		for group in self.group_members_cache_con:
			if remove_con_dn and remove_con_dn in self.group_members_cache_con[group]:
				ud.debug(ud.LDAP, ud.INFO, "_update_group_member_cache: remove %s from con cache for group %s" % (remove_con_dn, group))
				self.group_members_cache_con[group].remove(remove_con_dn)
			if add_con_dn and add_con_dn not in self.group_members_cache_con[group]:
				ud.debug(ud.LDAP, ud.INFO, "_update_group_member_cache: add %s to con cache for group %s" % (add_con_dn, group))
				self.group_members_cache_con[group].add(add_con_dn)
		for group in self.group_members_cache_ucs:
			if remove_ucs_dn and remove_ucs_dn in self.group_members_cache_ucs[group]:
				ud.debug(ud.LDAP, ud.INFO, "_update_group_member_cache: remove %s from ucs cache for group %s" % (remove_ucs_dn, group))
				self.group_members_cache_ucs[group].remove(remove_ucs_dn)
			if add_ucs_dn and add_ucs_dn not in self.group_members_cache_ucs[group]:
				ud.debug(ud.LDAP, ud.INFO, "_update_group_member_cache: add %s to ucs cache for group %s" % (add_ucs_dn, group))
				self.group_members_cache_ucs[group].add(add_ucs_dn)

	def sync_from_ucs(self, property_type, object, pre_mapped_ucs_dn, old_dn=None, old_ucs_object=None, new_ucs_object=None):
		# NOTE: pre_mapped_ucs_dn means: original ucs_dn (i.e. before _object_mapping)
		# Diese Methode erhaelt von der UCS Klasse ein Objekt,
		# welches hier bearbeitet wird und in das AD geschrieben wird.
		# object ist brereits vom eingelesenen UCS-Objekt nach AD gemappt, old_dn ist die alte UCS-DN
		ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: sync object: %s" % object['dn'])

		# if sync is read (sync from AD) or none, there is nothing to do
		if self.property[property_type].sync_mode in ['read', 'none']:
			ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs ignored, sync_mode is %s" % self.property[property_type].sync_mode)
			return True

		# check for move, if old_object exists, set modtype move
		pre_mapped_ucs_old_dn = old_dn
		if old_dn:
			ud.debug(ud.LDAP, ud.INFO, "move %s from [%s] to [%s]" % (property_type, old_dn, object['dn']))
			if hasattr(self.property[property_type], 'dn_mapping_function'):
				tmp_object = copy.deepcopy(object)
				tmp_object['dn'] = old_dn
				for function in self.property[property_type].dn_mapping_function:
					tmp_object = function(self, tmp_object, [], isUCSobject=True)
				old_dn = tmp_object['dn']
			if hasattr(self.property[property_type], 'position_mapping'):
				for mapping in self.property[property_type].position_mapping:
					old_dn = self._subtree_replace(old_dn.lower(), mapping[0].lower(), mapping[1].lower())
				old_dn = self._subtree_replace(old_dn, self.lo.base, self.lo_ad.base)

			# the old object was moved in UCS, but does this object exist in AD?
			try:
				old_object = self.ad_search_ext_s(old_dn, ldap.SCOPE_BASE, 'objectClass=*')
			except ldap.SERVER_DOWN:
				raise
			except Exception:
				old_object = None

			if old_object:
				ud.debug(ud.LDAP, ud.INFO, "move %s from [%s] to [%s]" % (property_type, old_dn, object['dn']))
				try:
					self.lo_ad.rename(old_dn, object['dn'])
				except ldap.NO_SUCH_OBJECT:  # check if object is already moved (we may resync now)
					new = self.ad_search_ext_s(object['dn'], ldap.SCOPE_BASE, 'objectClass=*')
					if not new:
						raise
				# need to actualise the GUID, group cache and DN-Mapping
				object['modtype'] = 'move'
				self._remove_dn_from_group_cache(con_dn=old_dn, ucs_dn=pre_mapped_ucs_old_dn)
				self._update_group_member_cache(
					remove_con_dn=old_dn.lower(),
					remove_ucs_dn=pre_mapped_ucs_old_dn.lower(),
					add_con_dn=object['dn'].lower(),
					add_ucs_dn=pre_mapped_ucs_dn.lower())
				ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: Updating UCS and AD group member mapping cache for %s to %s" % (pre_mapped_ucs_dn, object['dn']))
				self.group_member_mapping_cache_ucs[pre_mapped_ucs_dn.lower()] = object['dn']
				self.group_member_mapping_cache_con[object['dn'].lower()] = pre_mapped_ucs_dn

				self._set_DN_for_GUID(self.ad_search_ext_s(object['dn'], ldap.SCOPE_BASE, 'objectClass=*')[0][1]['objectGUID'][0], object['dn'])
				self._remove_dn_mapping(pre_mapped_ucs_old_dn, old_dn)
				self._check_dn_mapping(pre_mapped_ucs_dn, object['dn'])

		ud.debug(ud.LDAP, ud.PROCESS, 'sync from ucs: [%14s] [%10s] %s' % (property_type, object['modtype'], object['dn']))

		if 'olddn' in object:
			object.pop('olddn')  # not needed anymore, will fail object_mapping in later functions
		old_dn = None

		addlist = []
		modlist = []

		# get current object
		ad_object = self.get_object(object['dn'])

		#
		# ADD
		#
		if not ad_object and object['modtype'] in ('add', 'modify', 'move'):
			ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: add object: %s" % object['dn'])

			self.addToCreationList(object['dn'])

			# objectClass
			if self.property[property_type].con_create_objectclass:
				addlist.append(('objectClass', self.property[property_type].con_create_objectclass))

			# fixed Attributes
			if self.property[property_type].con_create_attributes:
				addlist += self.property[property_type].con_create_attributes

			if hasattr(self.property[property_type], 'attributes') and self.property[property_type].attributes is not None:
				for attr, value in object['attributes'].items():
					for attr_key in self.property[property_type].attributes.keys():
						attribute = self.property[property_type].attributes[attr_key]
						if attr not in (attribute.con_attribute, attribute.con_other_attribute):
							continue
						addlist.append((attr, value))
			if hasattr(self.property[property_type], 'post_attributes') and self.property[property_type].post_attributes is not None:
				for attr, value in object['attributes'].items():
					for attr_key in self.property[property_type].post_attributes.keys():
						post_attribute = self.property[property_type].post_attributes[attr_key]
						if post_attribute.reverse_attribute_check:
							if not object['attributes'].get(post_attribute.ldap_attribute):
								continue
						if attr not in (post_attribute.con_attribute, post_attribute.con_other_attribute):
							continue

						if value:
							modlist.append((ldap.MOD_REPLACE, attr, value))

			ud.debug(ud.LDAP, ud.INFO, "to add: %s" % object['dn'])
			ud.debug(ud.LDAP, ud.ALL, "sync_from_ucs: addlist: %s" % addlist)
			self.lo_ad.lo.add_s(compatible_modstring(object['dn']), compatible_addlist(addlist))  # FIXME encoding

			if property_type == 'group':
				self.group_members_cache_con[object['dn'].lower()] = set()
				ud.debug(ud.LDAP, ud.INFO, "group_members_cache_con[%s]: {}" % (object['dn'].lower()))

			if hasattr(self.property[property_type], "post_con_create_functions"):
				for f in self.property[property_type].post_con_create_functions:
					f(self, property_type, object)

			ud.debug(ud.LDAP, ud.INFO, "to modify: %s" % object['dn'])
			if modlist:
				ud.debug(ud.LDAP, ud.ALL, "sync_from_ucs: modlist: %s" % modlist)
				try:
					self.lo_ad.lo.modify_s(compatible_modstring(object['dn']), compatible_modlist(modlist))
				except:
					ud.debug(ud.LDAP, ud.ERROR, "sync_from_ucs: traceback during modify object: %s" % object['dn'])
					ud.debug(ud.LDAP, ud.ERROR, "sync_from_ucs: traceback due to modlist: %s" % modlist)
					raise

			if hasattr(self.property[property_type], "post_con_modify_functions"):
				for f in self.property[property_type].post_con_modify_functions:
					ud.debug(ud.LDAP, ud.INFO, "Call post_con_modify_functions: %s" % f)
					f(self, property_type, object)
					ud.debug(ud.LDAP, ud.INFO, "Call post_con_modify_functions: %s (done)" % f)

		#
		# MODIFY
		#
		elif ad_object and object['modtype'] in ('add', 'modify', 'move'):
			ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: modify object: %s" % object['dn'])

			ud.debug(ud.LDAP, ud.ALL, "sync_from_ucs: object: %s" % object)
			ud.debug(ud.LDAP, ud.ALL, "sync_from_ucs: object_old: %s" % object_old)
			attribute_list = set(object_old['attributes'].keys() + object['attributes'].keys())

			# Iterate over attributes and post_attributes
			for attribute_type_name, attribute_type in [('attributes', self.property[property_type].attributes),
					('post_attributes', self.property[property_type].post_attributes)]:
				if hasattr(self.property[property_type], attribute_type_name) and attribute_type is not None:
					for attr in attribute_list:
						if not self.__has_attribute_value_changed(attr, object_old, object):
							continue

						ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: The following attribute has been changed: %s" % attr)

						for attribute in attribute_type.keys():
							if attr not in (attribute_type[attribute].con_attribute, attribute_type[attribute].con_other_attribute):
								continue

							ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: Found a corresponding mapping defintion: %s" % attribute)
							ad_attribute = attribute_type[attribute].con_attribute
							ad_other_attribute = attribute_type[attribute].con_other_attribute

							if attribute_type[attribute].sync_mode not in ['write', 'sync']:
								ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: %s is in not in write or sync mode. Skipping" % attribute)
								continue

							modify = False

							# Get the UCS attributes
							old_values = set(object_old['attributes'].get(attr, []))
							new_values = set(object['attributes'].get(attr, []))

							ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: %s old_values: %s" % (attr, old_values))
							ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: %s new_values: %s" % (attr, new_values))

							if attribute_type[attribute].compare_function:
								if not attribute_type[attribute].compare_function(list(old_values), list(new_values)):
									modify = True
							# FIXME: use defined compare-function from mapping.py
							elif not univention.connector.compare_lowercase(list(old_values), list(new_values)):
								modify = True

							if not modify:
								ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: no modification necessary for %s" % attribute)
								continue

							# So, at this point we have the old and the new UCS object.
							# Thus we can create the diff, but we have to check the current AD object

							if not old_values:
								to_add = new_values
								to_remove = set([])
							elif not new_values:
								to_remove = old_values
								to_add = set([])
							else:
								to_add = new_values - old_values
								to_remove = old_values - new_values

							if ad_other_attribute:
								# This is the case, where we map from a multi-valued UCS attribute to two AD attributes.
								# telephoneNumber/otherTelephone (AD) to telephoneNumber (UCS) would be an example.
								#
								# The direct mapping assumes preserved ordering of the multi-valued UCS
								# attributes and places the first value in the primary AD attribute,
								# the rest in the secondary AD attributes.
								# Assuming preserved ordering is wrong, as LDAP does not guarantee is and the
								# deduplication of LDAP attribute values in `__set_values()` destroys it.
								#
								# The following code handles the correct distribution of the UCS attribute,
								# to two AD attributes. It also ensures, that the primary AD attribute keeps
								# its value as long as that value is not removed. If removed the primary
								# attribute is assigned a random value from the UCS attribute.
								try:
									current_ad_values = set([v for k, v in ad_object.iteritems() if ad_attribute.lower() == k.lower()][0])
								except IndexError:
									current_ad_values = set([])
								ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: The current AD values: %s" % current_ad_values)

								try:
									current_ad_other_values = set([v for k, v in ad_object.iteritems() if ad_other_attribute.lower() == k.lower()][0])
								except IndexError:
									current_ad_other_values = set([])
								ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: The current AD other values: %s" % current_ad_other_values)

								new_ad_values = current_ad_values - to_remove
								if not new_ad_values and to_add:
									for n_value in new_values:
										if n_value in to_add:
											to_add = to_add - set([n_value])
											new_ad_values = [n_value]
											break

								new_ad_other_values = (current_ad_other_values | to_add) - to_remove - current_ad_values
								if current_ad_values != new_ad_values:
									if new_ad_values:
										modlist.append((ldap.MOD_REPLACE, ad_attribute, new_ad_values))
									else:
										modlist.append((ldap.MOD_REPLACE, ad_attribute, []))

								if current_ad_other_values != new_ad_other_values:
									modlist.append((ldap.MOD_REPLACE, ad_other_attribute, new_ad_other_values))
							else:
								try:
									current_ad_values = set([v for k, v in ad_object.iteritems() if ad_attribute.lower() == k.lower()][0])
								except IndexError:
									current_ad_values = set([])

								ud.debug(ud.LDAP, ud.INFO, "sync_from_ucs: The current AD values: %s" % current_ad_values)

								if (to_add or to_remove) and attribute_type[attribute].single_value:
									modify = False
									if not current_ad_values or not new_values:
										modify = True
									elif attribute_type[attribute].compare_function:
										if not attribute_type[attribute].compare_function(list(current_ad_values), list(new_values)):
											modify = True
									elif not univention.connector.compare_lowercase(list(current_ad_values), list(new_values)):
										modify = True
									if modify:
										modlist.append((ldap.MOD_REPLACE, ad_attribute, new_values))
								else:
									if to_remove:
										r = current_ad_values & to_remove
										if r:
											modlist.append((ldap.MOD_DELETE, ad_attribute, r))
									if to_add:
										a = to_add - current_ad_values
										if a:
											modlist.append((ldap.MOD_ADD, ad_attribute, a))

			if not modlist:
				ud.debug(ud.LDAP, ud.ALL, "nothing to modify: %s" % object['dn'])
			else:
				ud.debug(ud.LDAP, ud.INFO, "to modify: %s" % object['dn'])
				ud.debug(ud.LDAP, ud.ALL, "sync_from_ucs: modlist: %s" % modlist)
				try:
					self.lo_ad.lo.modify_s(compatible_modstring(object['dn']), compatible_modlist(modlist))
				except:
					ud.debug(ud.LDAP, ud.ERROR, "sync_from_ucs: traceback during modify object: %s" % object['dn'])
					ud.debug(ud.LDAP, ud.ERROR, "sync_from_ucs: traceback due to modlist: %s" % modlist)
					raise

			if hasattr(self.property[property_type], "post_con_modify_functions"):
				for f in self.property[property_type].post_con_modify_functions:
					ud.debug(ud.LDAP, ud.INFO, "Call post_con_modify_functions: %s" % f)
					f(self, property_type, object)
					ud.debug(ud.LDAP, ud.INFO, "Call post_con_modify_functions: %s (done)" % f)
		#
		# DELETE
		#
		elif object['modtype'] == 'delete':
			self.delete_in_ad(object)
			# update group cache
			self._remove_dn_from_group_cache(con_dn=object['dn'], ucs_dn=pre_mapped_ucs_dn)
			self._update_group_member_cache(remove_con_dn=object['dn'].lower(), remove_ucs_dn=pre_mapped_ucs_dn.lower())
		else:
			ud.debug(ud.LDAP, ud.WARN, "unknown modtype (%s : %s)" % (object['dn'], object['modtype']))
			return False

		self._check_dn_mapping(pre_mapped_ucs_dn, object['dn'])

		ud.debug(ud.LDAP, ud.ALL, "sync from ucs return True")
		return True  # FIXME: return correct False if sync fails

	def _get_objectGUID(self, dn):
		ad_object = self.get_object(dn, ['objectGUID'])
		if not ad_object:
			ud.debug(ud.LDAP, ud.WARN, "Failed to search objectGUID for %s" % dn)
			return ''
		return ad_object.get('objectGUID')[0]

	def delete_in_ad(self, object):
		try:
			objectGUID = self._get_objectGUID(object['dn'])
			self.lo_ad.lo.delete_s(compatible_modstring(object['dn']))
			entryUUID = object.get('attributes').get('entryUUID')[0]
			self.update_deleted_cache_after_removal(entryUUID, objectGUID)
		except ldap.NO_SUCH_OBJECT:
			pass  # object already deleted
		except ldap.NOT_ALLOWED_ON_NONLEAF:
			ud.debug(ud.LDAP, ud.INFO, "remove object from AD failed, need to delete subtree")
			object_dn = compatible_modstring(object['dn'])
			for result in self.lo_ad.search(base=object_dn):
				if univention.connector.compare_lowercase(result[0], object['dn']):
					continue
				ud.debug(ud.LDAP, ud.INFO, "delete: %s" % result[0])
				subobject = {'dn': result[0], 'modtype': 'delete', 'attributes': result[1]}
				key = None
				for k in self.property.keys():
					if self.modules[k].identify(result[0], result[1]):
						key = k
						break
				object_mapping = self._object_mapping(key, subobject)
				ud.debug(ud.LDAP, ud.WARN, "delete subobject: %s" % object_mapping['dn'])
				if not self._ignore_object(key, object_mapping):
					if not self.sync_from_ucs(key, subobject, object_mapping['dn']):
						try:
							ud.debug(ud.LDAP, ud.WARN, "delete of subobject failed: %s" % result[0])
						except (ldap.SERVER_DOWN, SystemExit):
							raise
						except:  # FIXME: which exception is to be caught?
							ud.debug(ud.LDAP, ud.WARN, "delete of subobject failed")
						return False

			return self.delete_in_ad(object)
