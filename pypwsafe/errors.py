# =============================================================================
# SYMANTEC:  Copyright (C) 2009-2011 Symantec Corporation. All rights reserved.
#
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

"""Various errors the library can generate."""


class PSafeError(Exception):
    """Base pwsafe error."""


class PasswordError(PSafeError):
    """Password does not match the safe."""


class InvalidHMACError(PSafeError):
    """Calculated HMAC does not equal HMAC in the file."""


class ROSafe(PSafeError):
    """Safe is not in read/write mode."""


class UUIDNotFoundError(PSafeError):
    """UUID was not found."""


class RecordError(PSafeError):
    """Failed to perform an action on a record."""


class AccessError(PSafeError):
    """Insufficient permissions to access a safe file."""


class ROSafeError(PSafeError):
    """A write request was made on a read-only safe."""


class PropError(RecordError):
    """Failed to perform an action with a property."""


class PropParsingError(PropError):
    """Failed to parse a property."""


class HeaderError(PSafeError):
    """Error in the headers."""


class PrefrencesHeaderError(HeaderError):
    """An error occurred in the preferences header."""


class PrefsValueError(PrefrencesHeaderError):
    """Unexpected or improper value for the header preference."""


class PrefsDataTypeError(PrefrencesHeaderError):
    """Error parsing the preferences type of the preferences header record."""


class ConfigItemNotFoundError(PrefrencesHeaderError):
    """No such preference."""


class UnableToFindADelimitersError(PrefrencesHeaderError):
    """Couldn't find an unused char to delimit the string."""


class AlreadyLockedError(RuntimeError):
    """Safe is already locked; can't acquire new lock."""


class LockAlreadyAcquiredError(AlreadyLockedError):
    """Safe is already locked by this instance; can't acquire new lock."""


class NotLockedError(RuntimeError):
    """Safe is not locked; can't unlock."""
