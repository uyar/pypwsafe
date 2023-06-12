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

from pypwsafe.consts import conf_bools, conf_ints, conf_strs, ptDatabase


SAFE_FILENAME = "NonDefaultPrefsTest.psafe3"


def test_safe_should_have_some_settings(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    prefs = safe.getDbPrefs()
    assert len(prefs) == 30


def test_db_level_settings_should_be_in_stored(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    prefs = safe.getDbPrefs()
    for pref_types in [conf_bools, conf_ints, conf_strs]:
        for name, info in pref_types.items():
            if info["type"] == ptDatabase:
                assert name in prefs


def test_non_db_level_settings_should_not_be_stored(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    prefs = safe.getDbPrefs()
    for pref_types in [conf_bools, conf_ints, conf_strs]:
        for name, info in pref_types.items():
            if info["type"] != ptDatabase:
                assert name not in prefs


# TODO: Add a check to make sure default values aren't being saved
