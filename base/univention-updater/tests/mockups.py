#!/usr/bin/python3
# vim:set fileencoding=utf-8 filetype=python tabstop=4 shiftwidth=4 expandtab:
from __future__ import print_function

import json
import os.path
import sys
from itertools import groupby
from operator import itemgetter

try:
    from typing import Dict, Iterable, List, Sequence, Tuple  # noqa F401
except ImportError:
    pass

import six
from six.moves import http_client as httplib

import univention
univention.__path__.insert(0, os.path.abspath('modules/univention'))  # type: ignore
import univention.updater.tools as U  # noqa: E402
import univention.updater.mirror as M  # noqa: E402
import univention.config_registry as C  # noqa: E402


MAJOR = 3
MINOR = 0
PATCH = 1
ERRAT = 3
PART = 'part'
ARCH = 'arch'


class MockUCSHttpServer(U.UCSLocalServer):

    """Mockup for UCSHttpServer."""
    PREFIX = 'mock'
    mock_content = {}  # type: Dict[str, bytes]

    def __init__(self, baseurl, user_agent=None, timeout=None):
        U.UCSLocalServer.__init__(self, MockUCSHttpServer.PREFIX)
        self.mock_url = baseurl
        self.mock_uris = []
        self.mock_uri = None

    def access(self, repo, filename=None, get=False):  # pylint: disable-msg=W0613
        """Access relative URI."""
        rel = filename if repo is None else repo.path(filename)
        self.mock_uri = self.join(rel)
        self.mock_uris.append(self.mock_uri)
        try:
            data = MockUCSHttpServer.mock_content[self.mock_uri]
            self.log.info('Retrieved %s: %d', self.mock_uri, len(data))
            return (httplib.OK, len(data), data)
        except KeyError:
            self.log.info('Failed %s', self.mock_uri)
            raise U.DownloadError(self.mock_uri, -1)

    @classmethod
    def mock_add(cls, relpath, content):
        """Add content to mackup (including all parent directories)."""
        dirname, _base = os.path.split(relpath)
        while dirname:
            uri = 'file:///%s/%s/' % (MockUCSHttpServer.PREFIX, dirname)
            cls.mock_content.setdefault(uri, b'')
            dirname = os.path.dirname(dirname)
            if dirname == '/':
                break
        uri = 'file:///%s/%s' % (MockUCSHttpServer.PREFIX, relpath)
        cls.mock_content[uri] = content

    def mock_dump(self, out=sys.stdout):
        """Print accessed URIs."""
        print('Registered URIs:', file=out)
        print('\n'.join(sorted(MockUCSHttpServer.mock_content)), file=out)
        print('Requested URIs:', file=out)
        print('\n'.join(self.mock_uris), file=out)

    @classmethod
    def mock_reset(cls):
        """Reset log of accessed URIs."""
        cls.mock_content = {}


class MockPopen(object):

    """Mockup for Popen."""
    _ORIG = U.subprocess.Popen
    mock_commands = []  # type: List[Sequence[str]]
    mock_stdout = ''
    mock_stderr = ''

    def __init__(self, cmd, shell=False, *args, **kwargs):  # pylint: disable-msg=W0613
        self.returncode = 0
        self.stdin = ''
        self.stdout = MockPopen.mock_stdout
        self.stderr = MockPopen.mock_stderr
        if shell:
            MockPopen.mock_commands.append(cmd)
        else:
            if isinstance(cmd, six.string_types):
                cmd = (cmd,)
            try:
                fd_script = open(cmd[0], 'r')
                try:
                    content = fd_script.read(1024)
                finally:
                    fd_script.close()
            except IOError as ex:
                content = ex
            MockPopen.mock_commands.append(tuple(cmd) + (content,))

    def wait(self, timeout=None):
        """Return result code."""
        return self.returncode

    def poll(self):
        """Return result code."""
        return self.returncode

    def communicate(self, stdin=None):  # pylint: disable-msg=W0613
        """Return stdout and strerr."""
        return self.stdout, self.stderr

    @classmethod
    def mock_get(cls):
        """Return list of called commands."""
        commands = cls.mock_commands
        cls.mock_commands = []
        return commands

    @classmethod
    def mock_reset(cls):
        """Reset list of called commands."""
        cls.mock_commands = []
        cls.mock_stdout = cls.mock_stderr = ''


class MockFile(object):

    """Wrapper for open() / file()."""
    _ORIG = open

    def __init__(self, base='/tmp'):
        self.mock_base = base
        self.mock_whitelist = set()

    def __call__(self, name, mode='r', *args, **kwargs):
        if mode.startswith('r'):
            return MockFile._ORIG(name, mode, *args, **kwargs)
        else:
            head, tail = os.path.split(name)
            if head not in self.mock_whitelist and not os.path.isdir(head):
                raise IOError(errno.ENOENT, "No such file or directory: '%s'" % (name,))
            dirname = self.mock_base + head
            M.makedirs(dirname)
            filename = os.path.join(dirname, tail)
            return MockFile._ORIG(filename, mode, *args, **kwargs)


def gen_releases(releases):  # type: (Iterable[Tuple[int, int, int]]) -> bytes
    """Generate a releases.json string from a list of given releases"""
    data = dict(
        releases=[
            dict(
                major=major,
                minors=[
                    dict(
                        minor=minor,
                        patchlevels=[
                            dict(
                                patchlevel=patchlevel,
                                status="maintained",
                            ) for major, minor, patchlevel in patchelevels
                        ]
                    ) for minor, patchelevels in groupby(minors, key=itemgetter(1))
                ]
            ) for major, minors in groupby(releases, key=itemgetter(0))
        ]
    )
    return json.dumps(data).encode('UTF-8')


def verbose(verbose_mode=True):
    """Turn on verbose network mode."""
    U.ud.init('stdout', U.ud.NO_FLUSH, U.ud.NO_FUNCTION)
    level = U.ud.ALL if verbose_mode else U.ud.ERROR
    U.ud.set_level(U.ud.NETWORK, level)
