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

"""Read & write Password Safe v3 files."""

import datetime
import getpass
import logging
import logging.config
import os
import os.path
import re
import socket
from hmac import new as HMAC
from struct import pack, unpack
from uuid import uuid4

from Crypto.Hash import SHA256
from pygcrypt.ciphers import Cipher

from . import headers, errors
from .records import Record


log = logging.getLogger("psafe.lib.init")
log.debug("initing")


def stretchkey(passwd, salt, count):
    """
    Stretch a key. H(pass+salt)
    @param passwd: The password being stretched
    @type passwd: string
    @param salt: Salt for the password. Should pre-provided random data.
    @type salt: string
    @param count: The number of times to repeat the stretch function
    @type count: int
    """
    assert count > 0
    # Hash once with both
    inithsh = SHA256.new()
    inithsh.update(passwd)
    inithsh.update(salt)
    # Expecting it in binary form; NOT HEX FORM
    hsh = inithsh.digest()
    # Rehash
    for i in range(count):
        t = SHA256.new()
        t.update(hsh)
        hsh = t.digest()
    return hsh


def _findHeader(headers, htype):
    for hdr in headers:
        if type(hdr) == htype:
            return hdr
    return None


def _getHeaderField(headers, htype, ignored=""):
    hdr = _findHeader(headers, htype)
    if hdr:
        return getattr(hdr, htype.FIELD)
    return None


def _getHeaderFields(headers, htype):
    """For headers that may be there multiple times"""
    found = []
    for hdr in headers:
        if type(hdr) == htype:
            found.append(getattr(hdr, htype.FIELD))
    return found


def _setHeaderField(headers, htype, value):
    hdr = _findHeader(headers, htype)
    if hdr:
        setattr(hdr, htype.FIELD, value)
        return True
    return False


class PWSafe3(object):
    """A Password safe object.

    Allows read/write access to most header fields and records
    in a psafe object.
    """

    filename = None
    """@ivar: Full path to pwsafe
    @type filename: string
    """

    password = None
    """@ivar: Passsafe password
    @type password: string
    """

    fl = None
    """@ivar: PWSafe file handle
    @type fl: File Handle
    """

    flfull = None
    """@ivar: Contents of pwsafe file
    @type flfull: string
    """

    pprime = None
    """@ivar: Stretched key used in B1 - B4
    @type pprime: string
    """

    enckey = None
    """@ivar: K; session key for main data block
    @type enckey: string
    """

    hshkey = None
    """@ivar: L; hmac key
    @type hshkey: string
    """

    records = None
    """@ivar: List of all records we have
    @type records: [Record,...]
    """

    hmacreq = None
    """@ivar: List of functions to run to generate hmac. Order matters when reading a file.
    @type hmacreq: function
    """

    hmac = None
    """@ivar: Originally its the hmac from the file. Should be updated when ever changes are made.
    @type hmac: string
    """

    mode = None
    """@ivar: Read only or read/write mode. "RO" for read-only or "RW" or read/write.
    @type mode: string
    """

    iv = None
    """@ivar: Initialization vector used for CBC mode when encrypting / decrypting the header and records.
    @type iv: string[16]
    """

    def __init__(self, filename, password, mode="RW"):
        """
        @param filename: The path to the Password Safe file. Will be created if it doesn't already exist.
        @type filename: string
        @param password: The password to encrypt/decrypt the safe with.
        @type password: string
        @param mode: Read only or read/write mode. "RO" for read-only or "RW" or read/write.
        @type mode: string
        """
        log.debug("Creating psafe %s" % repr(filename))
        self.locked = False
        filename = os.path.realpath(filename)
        psafe_exists = os.access(filename, os.F_OK)
        psafe_canwrite = os.access(filename, os.W_OK)
        psafe_canwritebase = os.access(os.path.dirname(filename), os.W_OK)
        psafe_canread = os.access(filename, os.R_OK)
        if psafe_exists and psafe_canread and not psafe_canwrite:
            log.debug("Opening RO")
            self.mode = "RO"
        elif psafe_exists and psafe_canread and psafe_canwrite and mode == "RW":
            log.debug("Opening RW")
            self.mode = "RW"
        elif psafe_exists and psafe_canread and psafe_canwrite and mode != "RW":
            log.debug("Opening RO")
            self.mode = "RO"
        elif not psafe_exists and psafe_canwritebase and mode == "RW":
            log.debug("Creating new psafe as RW")
            self.mode = "RW"
        elif not psafe_exists and psafe_canwrite and mode != "RW":
            log.warn("Asked to create a new psafe but mode is set to RO")
            raise errors.AccessError("Asked to create a new safe in RO mode")
        elif psafe_exists:
            log.warn("Can't read safe %s" % repr(filename))
            raise errors.AccessError("Can't read %s" % filename)
        else:
            log.warn("Safe doesn't exist or can't read directory")
            raise errors.AccessError("No such safe %s" % filename)
        if psafe_exists:
            self.filename = filename
            log.debug("Loading existing safe from %r" % self.filename)
            self.fl = open(self.filename, "rb")
            try:
                self.flfull = self.fl.read()
                log.debug("Full data len: %d" % len(self.flfull))
                self.password = str(password).encode("utf-8")
                # Read in file
                self.load()
            finally:
                self.fl.close()
        else:
            log.debug("New psafe")
            self.password = str(password)
            self.filename = filename
            # Init local vars
            # SALT
            self.salt = os.urandom(32)
            log.debug("Salt is %s" % repr(self.salt))
            # ITER
            self.iter = pow(2, 11)  # 2048
            log.debug("Iter set to %s" % self.iter)
            # K
            self.enckey = os.urandom(32)
            # L
            self.hshkey = os.urandom(32)
            # IV
            self.iv = os.urandom(16)
            # Tag
            self.tag = "PWS3"
            # EOF
            self.eof = "PWS3-EOFPWS3-EOF"
            self.headers = []
            self.hmacreq = []
            self.records = []
            # Add EOF headers
            self.headers.append(headers.EOFHeader())
            self.autoUpdateHeaders()

    def autoUpdateHeaders(self):
        """Set auto-set headers that should be set on save"""
        self.setUUID(updateAutoData=False)
        self.setLastSaveApp("pypwsafe", updateAutoData=False)
        self.setTimeStampOfLastSave(datetime.datetime.now(), updateAutoData=False)
        self.setLastSaveHost(updateAutoData=False)
        self.setLastSaveUser(updateAutoData=False)

    def __len__(self):
        return len(self.records)

    def save(self):
        """Save the safe to disk"""
        if self.mode == "RW":
            self.serialiaze()
            fil = open(self.filename, "w")
            fil.write(self.flfull.decode("iso8859-1"))
            fil.close()
        else:
            raise errors.ROSafe("Safe is not in read/write mode")

    def serialiaze(self):
        """Turn the in-memory objects into in-memory strings."""
        # P'
        self._regen_pprime()
        # Regen b1b2
        self._regen_b1b2()
        # Regen b3b4
        self._regen_b3b4()
        # Regen H(P')
        self._regen_hpprime()
        # Regen hmac
        self.hmac = self.current_hmac()

        log.debug("Loading psafe")
        self.flfull = pack(
            "4s32sI32s32s32s16s",
            self.tag,
            self.salt,
            self.iter,
            self.hpprime,
            self.b1b2,
            self.b3b4,
            self.iv,
        )
        log.debug("Pre-header flfull now %s", (self.flfull,))
        self.fulldata = b""
        for header in self.headers:
            self.fulldata += header.serialiaze()
            # log.debug("In header flfull now %s",(self.flfull,))
        for record in self.records:
            self.fulldata += record.serialiaze()
            # log.debug("In record flfull now %s",(self.flfull,))
        # Encrypted self.fulldata to self.cryptdata
        log.debug("Encrypting header/record data %s" % repr(self.fulldata))
        self.encrypt_data()
        self.flfull += self.cryptdata
        log.debug("Adding crypt data %s" % repr(self.cryptdata))
        self.flfull += pack("16s32s", self.eof, self.hmac)
        log.debug("Post EOF flfull now %s", (self.flfull,))

    def _regen_pprime(self):
        """Regenerate P'. This is the stretched version of salt and password."""
        self.pprime = stretchkey(self.password, self.salt, self.iter)
        log.debug("P' = % s" % repr(self.pprime))

    def _regen_b1b2(self):
        """Regenerate b1 and b2. This is the encrypted form of K."""
        tw = Cipher(b"TWOFISH", "ECB")
        # HTU tw.init(self.pprime)
        tw.key = self.pprime
        self.b1b2 = tw.encrypt(self.enckey)
        log.debug("B1/B2 set to %s" % repr(self.b1b2))

    def _regen_b3b4(self):
        """Regenerate b3 and b4. This is the encrypted form of L."""
        tw = Cipher(b"TWOFISH", "ECB")
        # HTU tw.init(self.pprime)
        tw.key = self.pprime
        self.b3b4 = tw.encrypt(self.hshkey)
        log.debug("B3/B4 set to %s" % repr(self.b3b4))

    def _regen_hpprime(self):
        """Regenerate H(P')
        Save the SHA256 of self.pprime.
        """
        hsh = SHA256.new()
        hsh.update(self.pprime)
        self.hpprime = hsh.digest()
        log.debug("Set H(P') to % s" % repr(self.hpprime))
        assert self.check_password()

    def load(self):
        """Load a psafe3 file
        Will raise PasswordError if the password is bad.
        Format:
        Name    Bytes    Type
        TAG     4     ASCII
        SALT    32    BIN
        ITER    4    INT 32
        H(P')    32    BIN
        B1    16    BIN
        B2    16    BIN
        B3    16    BIN
        B4    16    BIN
        IV    16    BIN
        Crypted    16n    BIN
        EOF    16    ASCII
        HMAC    32    BIN
        """
        log.debug("Loading psafe")
        log.debug("len: %d flful: %r" % (len(self.flfull[:152]), self.flfull[:152]))
        (
            self.tag,
            self.salt,
            self.iter,
            self.hpprime,
            self.b1b2,
            self.b3b4,
            self.iv,
        ) = unpack("4s32sI32s32s32s16s", self.flfull[:152])
        log.debug("Tag: %s" % repr(self.tag))
        log.debug("Salt: %s" % repr(self.salt))
        log.debug("Iter: %s" % repr(self.iter))
        log.debug("H(P'): % s" % repr(self.hpprime))
        log.debug("B1B2: % s" % repr(self.b1b2))
        log.debug("B3B4: % s" % repr(self.b3b4))
        log.debug("IV: % s" % repr(self.iv))
        self.cryptdata = self.flfull[152:-48]
        (self.eof, self.hmac) = unpack("16s32s", self.flfull[-48:])
        log.debug("EOF: % s" % repr(self.eof))
        log.debug("HMAC: % s" % repr(self.hmac))
        # Determine the password hash
        self.update_pprime()
        # Verify password
        if not self.check_password():
            raise errors.PasswordError
        # Figure out the encryption and hash session keys
        log.debug("Calc'ing keys")
        self.calc_keys()
        log.debug("Going to decrypt data")
        self.decrypt_data()

        # Parse headers
        self.headers = []
        self.hmacreq = []
        self.remaining_headers = self.fulldata
        hdr = headers.Create_Header(self._fetch_block)
        self.headers.append(hdr)
        self.hmacreq.append(hdr.hmac_data)
        # print str(hdr) +" - -"+ repr(hdr)
        while type(hdr) != headers.EOFHeader:
            hdr = headers.Create_Header(self._fetch_block)
            self.headers.append(hdr)
            # print str(hdr) +" - -"+ repr(hdr)

        # Parse DB
        self.records = []
        while len(self.remaining_headers) > 0:
            req = Record(self._fetch_block)
            self.records.append(req)

        if self.current_hmac(cached=True) != self.hmac:
            log.error(
                "Invalid HMAC Calculated: %s File: %s"
                % (repr(self.current_hmac()), repr(self.hmac))
            )
            raise errors.InvalidHMACError(
                "Calculated: % s File: % s"
                % (repr(self.current_hmac()), repr(self.hmac))
            )

    def __str__(self):
        ret = ""
        for i in self.records:
            ret += str(i) + "\n\n"
        return ret

    def _fetch_block(self, num_blocks=1):
        """Returns one or more 16 - byte block of data.

        Raises EOFError when there is no more data.
        """
        num_blocks = int(num_blocks)
        num_bytes = num_blocks * 16
        if num_bytes > len(self.remaining_headers):
            raise EOFError("No more header data")
        ret = self.remaining_headers[:num_bytes]
        self.remaining_headers = self.remaining_headers[num_bytes:]
        return ret

    def calc_keys(self):
        """Calculate sessions keys for encryption and hmac.

        Is based on pprime, b1b2, b3b4.
        """
        tw = Cipher(b"TWOFISH", "ECB")
        # HTU tw.init(self.pprime)
        tw.key = self.pprime
        self.enckey = tw.decrypt(self.b1b2)
        # its ok to reuse; ecb doesn't keep state info
        self.hshkey = tw.decrypt(self.b3b4)
        log.debug("Encryption key K: %s " % repr(self.enckey))
        log.debug("HMAC Key L: %s " % repr(self.hshkey))

    def decrypt_data(self):
        """Decrypt encrypted portion of header and data."""
        log.debug("Creating mcrypt object")
        tw = Cipher(b"TWOFISH", "CBC")
        log.debug("Adding key & iv")
        # HTU tw.init(self.enckey, self.iv)
        tw.key = self.enckey
        tw.iv = self.iv
        log.debug("Decrypting data")
        self.fulldata = tw.decrypt(self.cryptdata)

    def encrypt_data(self):
        """Encrypted fulldata to cryptdata."""
        tw = Cipher(b"TWOFISH", "CBC")
        # HTU tw.init(self.enckey, self.iv)
        tw.key = self.enckey
        tw.iv = self.iv
        self.cryptdata = tw.encrypt(self.fulldata)

    def current_hmac(self, cached=False):
        """Returns the current hmac of self.fulldata."""
        data = b""
        for i in self.headers:
            log.debug(
                "Adding hmac data %r from %r" % (i.hmac_data(), i.__class__.__name__)
            )
            if cached:
                data += i.data
            else:
                d = i.hmac_data()
                if isinstance(d, str):
                    d = d.encode("us-ascii")
                data += d
                # assert i.data == i.hmac_data(), "Working on %r where %r!=%r" % (i, i.data, i.hmac_data())
        for i in self.records:
            # TODO: Add caching support
            log.debug(
                "Adding hmac data %r from %r" % (i.hmac_data(), i.__class__.__name__)
            )
            data += i.hmac_data()
        log.debug("Building hmac with key %s", repr(self.hshkey))
        hm = HMAC(self.hshkey, data, SHA256)
        # print hm.hexdigest()
        log.debug("HMAC %s-%s", repr(hm.hexdigest()), repr(hm.digest()))
        return hm.digest()

    def check_password(self):
        """Check that the hash in self.pprime matches what's in the password safe. True if password matches hash in hpprime. False otherwise"""
        hsh = SHA256.new()
        hsh.update(self.pprime)
        return hsh.digest() == self.hpprime

    def update_pprime(self):
        """Update self.pprime. This key is used to decrypt B1 / 2 and B3 / 4"""
        self.pprime = stretchkey(self.password, self.salt, self.iter)

    def close(self):
        """Close out open file"""
        self.fl.close()

    def __del__(self):
        try:
            self.fl.close()
        except:
            pass

    def listall(self):
        """
        Yield all entries in the form
                (uuid, title, group, username, password, notes)
        @rtype: [(uuid, title, group, username, password, notes),...]
        @return A list of tuples covering all known records.
        """

        def nrwrapper(name):
            try:
                return record[name]
            except KeyError:
                return None

        for record in self.records:
            yield (
                nrwrapper("UUID"),
                nrwrapper("Title"),
                nrwrapper("Group"),
                nrwrapper("Username"),
                nrwrapper("Password"),
                nrwrapper("Notes"),
            )

    def getEntries(self):
        """Return a list of all records
        @rtype: [Record,...]
        @return: A list of all records.
        """
        return self.records

    def getpass(self, uuid=None):
        """Returns the password of the item with the given UUID
        @param uuid: UUID of the record to find
        @type uuid: UUID object
        @rtype: string
        @return: Password for the record with the given UUID. Raise an exception otherwise
        @raise UUIDNotFoundError
        """
        for record in self.records:
            if record["UUID"] == uuid:
                return record["Password"]
        raise errors.UUIDNotFoundError("UUID %s was not found. " % repr(uuid))

    def __getitem__(self, *args, **kwargs):
        return self.records.__getitem__(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        return self.records.__setitem__(*args, **kwargs)

    def getUUID(self):
        """Return the safe's uuid"""
        return _getHeaderField(self.headers, headers.UUIDHeader)

    def setUUID(self, uuid=None, updateAutoData=True):
        if updateAutoData:
            self.autoUpdateHeaders()

        if uuid is None:
            uuid = uuid4()

        if not _setHeaderField(self.headers, headers.UUIDHeader, uuid):
            self.headers.insert(0, headers.UUIDHeader(uuid=uuid))

    def removeUUID(self):
        _setHeaderField(self.headers, headers.UUIDHeader, None)

    def getVersion(self):
        """Return the safe's version"""
        return _getHeaderField(self.headers, headers.VersionHeader, "version")

    def setVersion(self, version=None, updateAutoData=True):
        """Return the safe's version"""
        if updateAutoData:
            self.autoUpdateHeaders()

        if not _setHeaderField(self.headers, headers.VersionHeader, version):
            self.headers.insert(0, headers.VersionHeader(version=version))

    def getVersionPretty(self):
        """Return the safe's version"""
        hdr = _findHeader(self.headers, headers.VersionHeader)
        if hdr:
            return hdr.getVersionHuman()
        return None

    def setVersionPretty(self, version=None, updateAutoData=True):
        """Return the safe's version"""
        if updateAutoData:
            self.autoUpdateHeaders()

        hdr = _findHeader(self.headers, headers.VersionHeader)
        if hdr:
            hdr.setVersionHuman(version)
        else:
            n = headers.VersionHeader(version=0x00)
            n.setVersionHuman(version=version)
            self.headers.insert(0, n)

    def getTimeStampOfLastSave(self):
        return _getHeaderField(self.headers, headers.TimeStampOfLastSaveHeader, "lastsave")

    def setTimeStampOfLastSave(self, timestamp, updateAutoData=True):
        if updateAutoData:
            self.autoUpdateHeaders()

        if not _setHeaderField(
            self.headers, headers.TimeStampOfLastSaveHeader, timestamp.timetuple()
        ):
            self.headers.insert(
                0, headers.TimeStampOfLastSaveHeader(lastsave=timestamp.timetuple())
            )

    def getLastSaveApp(self):
        return _getHeaderField(self.headers, headers.LastSaveAppHeader, "lastSafeApp")

    def setLastSaveApp(self, app, updateAutoData=True):
        if updateAutoData:
            self.autoUpdateHeaders()

        if not _setHeaderField(self.headers, headers.LastSaveAppHeader, app):
            self.headers.insert(0, headers.LastSaveAppHeader(lastSaveApp=app))

    def getLastSaveUser(self, fallbackOld=True):
        ret = self.getLastSaveUserNew()
        if ret or not fallbackOld:
            return ret
        return self.getLastSaveUserOld()

    def getLastSaveUserNew(self):
        """Get the last saving user using only the non-deprecated field"""
        return _getHeaderField(self.headers, headers.LastSaveUserHeader, "username")

    def getLastSaveUserOld(self):
        """Get the last saving user using only the deprecated 0x05 field"""
        return _getHeaderField(self.headers, headers.WhoLastSavedHeader)

    def setLastSaveUser(self, username=None, updateAutoData=True, addOld=False):
        if updateAutoData:
            self.autoUpdateHeaders()
        if username is None:
            username = getpass.getuser()

        if not _setHeaderField(self.headers, headers.LastSaveUserHeader, username):
            self.headers.insert(0, headers.LastSaveUserHeader(username=username))
        if addOld and not _setHeaderField(self.headers, headers.WhoLastSavedHeader, username):
            self.headers.insert(0, headers.WhoLastSavedHeader(username=username))

    def getLastSaveHost(self):
        return _getHeaderField(self.headers, headers.LastSaveHostHeader, "hostname")

    def setLastSaveHost(self, hostname=None, updateAutoData=True):
        if updateAutoData:
            self.autoUpdateHeaders()
        if not hostname:
            hostname = socket.gethostname()

        if not _setHeaderField(self.headers, headers.LastSaveHostHeader, hostname):
            self.headers.insert(0, headers.LastSaveHostHeader(hostname=hostname))

    def getDbName(self):
        """Returns the name of the db according to the psafe headers"""
        return _getHeaderField(self.headers, headers.DBNameHeader, "dbName")

    def setDbName(self, dbName, updateAutoData=True):
        """Returns the name of the db according to the psafe headers"""
        if updateAutoData:
            self.autoUpdateHeaders()

        if not _setHeaderField(self.headers, headers.DBNameHeader, dbName):
            self.headers.insert(0, headers.DBNameHeader(dbName=dbName))

    def getDbDesc(self):
        """Returns the description of the db according to the psafe headers"""
        return _getHeaderField(self.headers, headers.DBDescHeader, "dbDesc")

    def setDbDesc(self, dbDesc, updateAutoData=True):
        """Returns the description of the db according to the psafe headers"""
        if updateAutoData:
            self.autoUpdateHeaders()

        if not _setHeaderField(self.headers, headers.DBDescHeader, dbDesc):
            self.headers.insert(0, headers.DBDescHeader(dbDesc=dbDesc))

    def getDbPolicies(self):
        """Return a list of all named password policies"""
        return _getHeaderField(self.headers, headers.NamedPasswordPoliciesHeader)

    def setDbPolicies(self, dbName, updateAutoData=True):
        """Returns the name of the db according to the psafe headers"""
        raise NotImplementedError("FIXME: Add db policy control methods")

    def getDbRecentEntries(self):
        """Return a list of recent headers"""
        return _getHeaderFields(self.headers, headers.RecentEntriesHeader)

    def setDbRecentEntries(self, entryUUID, updateAutoData=True):
        """Returns the name of the db according to the psafe headers"""
        raise NotImplementedError("FIXME: Add db recent entries control methods")

    def getDbPrefs(self):
        """Return a list of recent headers"""
        return _getHeaderField(self.headers, headers.NonDefaultPrefsHeader)

    def setDbPrefs(self, prefs, updateAutoData=True):
        """Returns the name of the db according to the psafe headers"""
        if updateAutoData:
            self.autoUpdateHeaders()

        if not _setHeaderField(self.headers, headers.NonDefaultPrefsHeader, prefs):
            self.headers.insert(0, headers.NonDefaultPrefsHeader(**prefs))

    def setDbPref(self, prefName, prefValue, updateAutoData=True):
        """Returns the name of the db according to the psafe headers"""
        if updateAutoData:
            self.autoUpdateHeaders()

        hdr = _findHeader(self.headers, headers.NonDefaultPrefsHeader)
        if hdr:
            attr = getattr(hdr, headers.NonDefaultPrefsHeader.FIELD)
            attr[prefName] = prefValue
        else:
            self.headers.insert(0, headers.NonDefaultPrefsHeader(prefName=prefValue))

    def getEmptyGroups(self):
        """Return a list of empty group names"""
        return _getHeaderFields(self.headers, headers.EmptyGroupHeader)

    def setEmptyGroups(self, groups, updateAutoData=True):
        """Removes all existing empty group headers and adds one as given by groups"""
        if updateAutoData:
            self.autoUpdateHeaders()

        for hdr in self.headers:
            if type(hdr) == headers.EmptyGroupHeader:
                self.headers.remove(hdr)

        for groupName in groups:
            self.headers.insert(0, headers.EmptyGroupHeader(groupName=groupName))

    def addEmptyGroup(self, groupName, updateAutoData=True):
        """Removes all existing empty group headers and adds one as given by groups"""
        if updateAutoData:
            self.autoUpdateHeaders()

        assert groupName not in self.getEmptyGroups()

        self.headers.insert(0, headers.EmptyGroupHeader(groupName=groupName))

    def _get_lock_data(self):
        """Get a string representing the data that should be stored in the lockfile.

        For details about Password Safe's implementation
        see: http://passwordsafe.git.sourceforge.net/git/gitweb.cgi?p=passwordsafe/pwsafe.git;a=blob;f=pwsafe/pwsafe/src/os/windows/file.cpp
        """
        pid = os.getpid()
        username = getpass.getuser()
        host = socket.gethostname()
        return "%s@%s:%d" % (username, host, pid)

    # Example Lockfile data: 'myusername@myhostname:12345'
    LOCKFILE_PARSE_RE = re.compile(r"^(.*)@([^@:]*):(\d+)$")

    def lock(self):
        """Acquire a lock on the DB. Raise an exception on failure. Raises an error
        if the lock has already be acquired by this process or another.
        Note: Make sure to wrap the post-lock, pre-unlock in a try-finally
        so that the safe is always unlocked.
        Note: The type of locking/unlocking used should be compatable with
        the actuall Password Safe app. If the psafe save dir is shared via
        NFS/CIFS/etc then users of the share should be able to read/write/lock/unlock
        psafe files.
        Note: No gurentee that this will work in Windows
        """

        # Use splitext() to handle the case where the file may not have psafe3 ext or any extension at all.
        # Note the full path of filename is not lost when the extension is split off.
        filename, _ = os.path.splitext(self.filename)
        lfile = os.path.extsep.join((filename, "plk"))

        log.debug("Going to lock %r using %r", self, lfile)

        # Make sure we don't already hold the lock
        if self.locked and os.access(lfile, os.R_OK):
            raise errors.LockAlreadyAcquiredError

        if os.path.isfile(lfile):
            # May be a dead pid
            log.debug("Lock file already exists. Reading it. ")
            f = open(lfile, "rb")
            data = f.read()
            f.close()
            found = self.LOCKFILE_PARSE_RE.findall(data)
            log.debug("Got %r from the lock", found)
            if len(found) == 1:
                (lusername, lhostname, lpid) = found[0]
                if lhostname == socket.gethostbyname():
                    try:  # Check if the other proc is still alive
                        os.kill(pid, 0)  # @UndefinedVariable
                        log.info(
                            "Other process (PID: %r) is alive. Can't override lock for %r ",
                            lpid,
                            self,
                        )
                        raise errors.AlreadyLockedError(
                            "Other process is alive. Can't override lock. "
                        )
                    except:
                        # Not really locked, remove stale lock
                        log.warning("Removing stale lock file of %r at %r", self, lfile)
                        os.remove(lfile)
                        return self.lock()
                else:
                    log.info(
                        "Lock file is for a different host (%r). Assuming %r is locked. ",
                        lhostname,
                        self,
                    )
                    raise errors.AlreadyLockedError(
                        "Lock is on a different host. Can't try to unlock. "
                    )
            else:
                log.info(
                    "Lock file contains invalid data: %r Assuming the safe, %r, is already locked. ",
                    found,
                    self,
                )
                raise errors.AlreadyLockedError(
                    "Lock file contains invalid data. Assuming the safe is already locked. "
                )
        self.locked = lfile

        # Create the lock file with no race conditions
        # Should generate an OS error if the file already exists
        try:
            fd = os.open(lfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, self._get_lock_data())
            os.close(fd)
        except OSError as e:
            log.info("%r reported as unlocked but can't create the lockfile", self)
            raise errors.AlreadyLockedError

    def unlock(self):
        """Unlock the DB
        Note: See lock method for important locking info.
        """
        if not self.locked:
            log.info("%r is not locked. Failing to unlock. ", self)
            raise errors.NotLockedError("Not currently locked")
        try:
            os.remove(self.locked)
            self.locked = False
            log.debug("%r for %r is unlocked", self.locked, self)
        except OSError:
            log.info("%r reported as locked but no lock file exists", self)
            raise errors.NotLockedError("Obj reported as locked but no lock file exists")

    def forceUnlock(self):
        """Try to unlock and remove the lock file by force.
        Note: File permissions can cause this to fail.
        @return: True if a lock file was removed. False otherwise.
        """
        lfile = self.filename.replace(".psafe3", ".plk")
        log.debug(
            "Going to remove lock file %r from %r by force. Local obj lock status: %r",
            lfile,
            self,
            self.locked,
        )
        self.locked = False
        try:
            os.remove(lfile)
            log.info("Removed lock file %r by force", lfile)
            return True
        except OSError:
            log.debug("Lock file %r doesn't exist", lfile)
            return False


# Misc helper functions
def ispsafe3(filename):
    """Return True if the file appears to be a psafe v3 file. Does not do in-depth checks."""
    fil = open(filename, "r")
    data = fil.read(4)
    fil.close()
    return data == "PWS3"


if __name__ == "__main__":
    import doctest

    doctest.testmod()
