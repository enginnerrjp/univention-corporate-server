#!/usr/bin/python3
# vim:set fileencoding=utf-8 filetype=python tabstop=4 shiftwidth=4 expandtab:
# pylint: disable-msg=C0301,R0903,R0913
from __future__ import print_function

import sys
import os.path
import errno

import six
from six.moves import http_client as httplib
import pytest

import univention.updater.tools as U  # noqa: E402
import univention.updater.mirror as M  # noqa: E402
from univention.config_registry import ConfigRegistry
from mockups import MAJOR, MINOR, PATCH, ERRAT, MockUCSHttpServer, MockPopen

try:
    from typing import Dict, List, Sequence  # noqa F401
except ImportError:
    pass


@pytest.fixture(autouse=True)
def ucr(monkeypatch, tmpdir):
    db = tmpdir / "base.conf"
    monkeypatch.setenv("UNIVENTION_BASECONF", str(db))
    cr = ConfigRegistry()

    def extra(conf={}, **kwargs):
        cr.update(conf)
        cr.update(kwargs)
        cr.save()

    extra({
        'version/version': '%d.%d' % (MAJOR, MINOR),
        'version/patchlevel': '%d' % (PATCH,),
        'version/erratalevel': '%d' % (ERRAT,),
    })

    return extra


@pytest.fixture
def http(mocker):
    director = mocker.patch("urllib2.OpenerDirector", autospec=True)
    opener = mocker.patch("urllib2.build_opener")
    opener.return_value = director
    return opener


@pytest.fixture  # (autouse=True)
def server(monkeypatch):
    # FIXME: PMH WIP
    monkeypatch.setattr(sys.modules["univention.updater.tools"], "UCSHttpServer", MockUCSHttpServer)
    monkeypatch.setattr(U, "UCSHttpServer", MockUCSHttpServer)


@pytest.fixture  # (autouse=True)
def popen(monkeypatch):
    # FIXME: PMH WIP
    monkeypatch.setattr(sys.modules["subprocess"], "Popen", MockPopen)
