# -*- coding: utf-8 -*-
#
# Univention Directory Listener
#  stub file
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

from univention.config_registry import ConfigRegistry
from typing import Any, Callable, List, Optional, Type, TypeVar, Union
from types import TracebackType

_F = TypeVar("_F", bound=Callable[..., Any])

configRegistry: ConfigRegistry


def setuid(uid: Union[str, int]) -> None:
	...
def unsetuid()  -> None:
	...
def run(file: str, argv: List[str], uid: int = -1, wait: int = 1) -> int:
	...

class AsUser(object):
	def __init__(self, uid: int = ...) -> None:
		...
	def __enter__(self) -> None:
		...
	def ___exit__(
		self,
		exc_type: Optional[Type[BaseException]] = ...,
		exc_value: Optional[BaseException] = ...,
		traceback: Optional[TracebackType] = ...,
	) -> None:
		...
	def __call__(self, f: _F) -> Callable[[_F], _F]:
		...
