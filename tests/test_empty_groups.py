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


SAFE_FILENAME = "EmptyGroupTest.psafe3"


def test_safe_should_have_multiple_empty_groups(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    assert safe.getEmptyGroups() == [b"asdf", b"fdas"]


def test_add_empty_group_should_add_empty_group(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    safe.addEmptyGroup("bogus5324")
    assert "bogus5324" in safe.getEmptyGroups()
