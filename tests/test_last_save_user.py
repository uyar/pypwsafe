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


SAFE_FILENAME = "LastSaveUserTest.psafe3"


def test_safe_should_have_new_last_save_user(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    user = safe.getLastSaveUserNew()
    assert user == b"gpmidi"


def test_safe_should_not_have_old_last_save_user(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    user = safe.getLastSaveUserOld()
    assert user is None


def test_last_user_fallback_should_match_new_or_old(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    new_user = safe.getLastSaveUserNew()
    old_user = safe.getLastSaveUserOld()
    user = safe.getLastSaveUser(fallbackOld=True)
    assert (user == new_user) or (user == old_user)


def test_last_user_set_should_save_given_user(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    last_user = safe.getLastSaveUserNew()
    assert last_user == b"gpmidi"
    safe.setLastSaveUser(username="user123", updateAutoData=True, addOld=True)
    new_user = safe.getLastSaveUserNew()
    old_user = safe.getLastSaveUserOld()
    assert new_user == "user123"
    assert old_user == "user123"
