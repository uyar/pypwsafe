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

import unittest

from TestSafeTests import STANDARD_TEST_SAFE_PASSWORD, TestSafeTestBase


class RecentEntriesTest_DBLevel(TestSafeTestBase):
    # Should be overridden with a test safe file name.
    # The path should be relative to the test_safes directory.
    # All test safes must have the standard password (see above).
    testSafe = "RecentEntriesTest.psafe3"
    # Automatically open safes
    autoOpenSafe = False
    # How to open the safe
    autoOpenMode = "RO"

    def _openSafe(self):
        from pypwsafe import PWSafe3

        self.testSafeO = PWSafe3(
            filename=self.ourTestSafe,
            password=STANDARD_TEST_SAFE_PASSWORD,
            mode=self.autoOpenMode,
        )

    def test_open(self):
        self.testSafeO = None
        self._openSafe()
        self.assertTrue(self.testSafeO, "Failed to open the test safe")


class RecentEntriesTest_RecordLevel(TestSafeTestBase):
    # Should be overridden with a test safe file name.
    # The path should be relative to the test_safes directory.
    # All test safes must have the standard password (see above).
    testSafe = "RecentEntriesTest.psafe3"
    # Automatically open safes
    autoOpenSafe = True
    # How to open the safe
    autoOpenMode = "RO"

    def test_entries(self):
        from uuid import UUID

        for entry in self.testSafeO.getDbRecentEntries():
            self.assertTrue(type(entry) == UUID, "Expected a UUID")


# FIXME: Add save test
