#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Debmirror
#  mirrors a repository server
#
# Copyright 2009-2011 Univention GmbH
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

import os
import errno
import re
import subprocess
import itertools

from tools import UniventionUpdater, UCS_Version
try:
	import univention.debug as ud
except ImportError:
	import univention.debug2 as ud

class UniventionMirror( UniventionUpdater ):
	def __init__( self ):
		UniventionUpdater.__init__( self )
		self.repository_path =  self.configRegistry.get( 'repository/mirror/basepath', '/var/lib/univention-repository' )

		if self.configRegistry.has_key( 'repository/mirror/version/end' ):
			self.version_end = UCS_Version( self.configRegistry.get( 'repository/mirror/version/end' ) )
		else:
			self.version_end = UCS_Version( ( self.version_major, self.version_minor, self.patchlevel ) )
		if self.configRegistry.has_key( 'repository/mirror/version/start' ):
			self.version_start = UCS_Version( self.configRegistry.get( 'repository/mirror/version/start' ) )
		else:
			self.version_start = UCS_Version( ( self.version_major, 0, 0 ) )
		# set architectures to mirror
		archs = self.configRegistry.get( 'repository/mirror/architectures', '' )
		if archs:
			self.architectures = archs.split( ' ' )

	def config_repository( self ):
		""" Retrieve configuration to access repository. Overrides UniventionUpdater. """
		self.online_repository = self.configRegistry.get('repository/mirror', 'yes').lower() in ('yes', 'true', 'enabled', '1')
		self.repository_server = self.configRegistry.get( 'repository/mirror/server', 'apt.univention.de' )
		self.repository_port = self.configRegistry.get( 'repository/mirror/port', '80' )
		self.repository_prefix = self.configRegistry.get( 'repository/mirror/prefix', '' ).strip('/')
		self.sources = self.configRegistry.get( 'repository/mirror/sources', 'no' ).lower() in ( 'true', 'yes' )
		self.http_method = self.configRegistry.get('repository/mirror/httpmethod', 'HEAD').upper()


	def mirror_repositories( self ):
		'''uses apt-mirror to copy a repository'''
		# check if the repository directory structure exists, otherwise create it
		if not os.path.exists( self.repository_path ):
			os.makedirs( self.repository_path )

		# these sub-directories are required by apt-mirror
		for dir in ( 'skel', 'mirror', 'var' ):
			path = os.path.join( self.repository_path, dir )
			if not os.path.exists( path ):
				os.makedirs( path )
		path = os.path.join(self.repository_path, 'mirror', 'univention-repository')
		if not os.path.exists(path):
			os.symlink('.', path)

		log = open('/var/log/univention/repository.log', 'a')
		try:
			return subprocess.call('/usr/bin/apt-mirror', stdout=log, stderr=log, shell=False)
		finally:
			log.close()

	def mirror_update_scripts( self ):
		'''mirrors the preup.sh and postup.sh scripts'''
		start = self.version_start
		end = self.version_end
		parts = self.parts
		archs = ('all',)

		repos = self._iterate_version_repositories(start, end, parts, archs) # returns generator

		start_errata = UCS_Version((start.major, start.minor, 0))  # errata updates start with 'errata001'
		end_errata = UCS_Version((end.major, end.minor, 99)) # get all available for mirror
		hotfixes = self.hotfixes
		errata = self._iterate_errata_repositories(start_errata, end_errata, parts, archs) # returns generator

		components = self.get_components()
		comp = self._iterate_component_repositories(components, start, end, archs, for_mirror_list=True) # returns generator

		all_repos = itertools.chain(repos, errata, comp) # concatenate all generators into a single one
		for server, struct, phase, path, script in UniventionUpdater.get_sh_files(all_repos):
			assert script is not None, 'No script'

			# use prefix if defined - otherwise file will be stored in wrong directory
			if server.prefix:
				filename = os.path.join(self.repository_path, 'mirror', server.prefix, path)
			else:
				filename = os.path.join(self.repository_path, 'mirror', path)

			# Check disabled, otherwise files won't get refetched if they change on upstream server
			#if os.path.exists(filename):
			# 	ud.debug(ud.NETWORK, ud.ALL, "Script already exists, skipping: %s" % filename)
			# 	continue

			dirname = os.path.dirname(filename)
			try:
				os.makedirs(dirname, 0755)
			except OSError, e:
				if e.errno == errno.EEXIST:
					pass
				else:
					raise
			fd = open(filename, "w")
			try:
				fd.write(script)
				ud.debug(ud.ADMIN, ud.INFO, "Successfully mirrored script: %s" % filename)
			finally:
				fd.close()

	def list_local_repositories( self, start = None, end = None, maintained = True, unmaintained = False ):
		'''
		This function returns a sorted list of local (un)maintained repositories.
		Arguments: start: smallest version that shall be returned (type: UCS_Version)
				   end:   largest version that shall be returned (type: UCS_Version)
				   maintained:   True if list shall contain maintained repositories
				   unmaintained: True if list shall contain unmaintained repositories
		Returns: a list of ( directory, UCS_Version, is_maintained ) tuples.
		'''
		result = []
		repobase = os.path.join( self.repository_path, 'mirror')
		RErepo = re.compile('^%s/(\d+[.]\d)/(maintained|unmaintained)/(\d+[.]\d+-\d+)$' % repobase )
		for dirname, subdirs, files in os.walk(repobase):
			match = RErepo.match(dirname)
			if match:
				if not maintained and match.group(2) == 'maintained':
					continue
				if not unmaintained and match.group(2) == 'unmaintained':
					continue

				version = UCS_Version( match.group(3) )
				# do not compare start with None by "!=" or "=="
				if not start is None and version < start:
					continue
				# do not compare end with None by "!=" or "=="
				if not end is None and end < version:
					continue

				result.append( ( dirname, version, match.group(2) == 'maintained' ) )

		result.sort(lambda x,y: cmp(x[1], y[1]))

		return result

	def update_dists_files( self ):
		last_version = None
		last_dirname = None
		repobase = os.path.join( self.repository_path, 'mirror')

		# iterate over all local repositories
		for dirname, version, is_maintained in self.list_local_repositories( start=self.version_start, end=self.version_end, unmaintained = False ):
			if version.patchlevel == 0:
				archlist = ( 'i386', 'amd64' )
				for arch in archlist:
					# create dists directory if missing
					d = os.path.join( dirname, 'dists/univention/main/binary-%s' % arch )
					if not os.path.exists( d ):
						os.makedirs( d, 0755 )

					# truncate dists packages file
					fn = os.path.join( d, 'Packages' )
					open(fn,'w').truncate(0)

					# fetch all downloaded repository packages files and ...
					for cur_packages in ( os.path.join( dirname, 'all/Packages' ), os.path.join( dirname, arch, 'Packages' ) ):
						# ...if it exists....
						if os.path.exists( cur_packages ):
							# ... convert that file and append it to new dists packages file
							subprocess.call( 'sed -re "s|^Filename: %s/|Filename: |" < %s >> %s' % (version, cur_packages, fn ), shell=True )

					# append existing Packages file of previous versions
					if not last_version is None: # do not compare last_version with None by "!=" or "=="
						# do not append Packages from other major versions
						if last_version.major == version.major:
							# get last three items of pathname and build prefix
							prefix = '../../../%s' % os.path.join( *( last_dirname.split('/')[-3:]) )
							subprocess.call( 'sed -re "s|^Filename: %s/|Filename: %s/%s/|" < %s/dists/univention/main/binary-%s/Packages >> %s' % (
								arch, prefix, arch, last_dirname, arch, fn ), shell=True )

					# create compressed copy of dists packages files
					subprocess.call( 'gzip < %s > %s.gz' % (fn, fn), shell=True )

				# remember last version and directory name
				last_version = version
				last_dirname = dirname


	def run( self ):
		'''starts the mirror process'''
		self.mirror_repositories()
		self.mirror_update_scripts()
		self.update_dists_files()

if __name__ == '__main__':
	import doctest
	doctest.testmod()
