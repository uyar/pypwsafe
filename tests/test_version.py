# =============================================================================
# This file is part of PyPWSafe.
#
# PyPWSafe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# PyPWSafe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyPWSafe.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================

# original author: Paulson McIntyre <paul@gpmidi.net>

import pytest


SAFE_FILENAME = "VersionTest.psafe3"


def test_safe_should_not_have_a_version(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    assert safe.getVersion() is None


def test_set_pretty_version_should_set_correct_id(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    safe.setVersionPretty(version="PasswordSafe V3.28")
    assert safe.getVersion() == 0x030A


def test_set_pretty_version_should_raise_error_with_bogus_version(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    with pytest.raises(ValueError):
        safe.setVersionPretty(version="Bogus version")
