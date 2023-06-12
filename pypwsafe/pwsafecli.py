# =============================================================================
# Copyright (C) 2023 H. Turgut Uyar <uyar@tekir.org>
#   original author: Paulson McIntyre <paul@gpmidi.net>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyPWSafe.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================

import datetime
import logging
import logging.config
import sys
import time
from argparse import ArgumentParser
from getpass import getpass
from socket import getfqdn
from uuid import UUID

from pypwsafe import PWSafe3, Record
from pypwsafe.errors import PasswordError


__version__ = "0.1"


class PWSafeCLIError(Exception):
    """Errors related to the PWSafe CLI operations."""


class PWSafeCLIValidationError(Exception):
    """Errors related to PWSafe CLI usage arguments."""


VALID_ATTRIBUTES = [
    "group",
    "title",
    "username",
    "password",
    "UUID",
    "note",
    "created",
    "PasswordModified",
    "EntryModified",
    "LastAccess",
    "expires",
    "email",
    "URL",
    "AutoType",
]


def get_record_attr(record, attr):
    if not attr[0].isupper():
        attr = attr.title()
    bound_method = getattr(record, "get%s" % attr)
    return bound_method()


def match_valid(record, **params):
    if not params:
        return False

    valid = False

    for key, value in list(params.items()):
        if value is None:
            continue
        valid = get_record_attr(record, key) == value
        if not valid:
            return False

    return valid


def get_matching_records(psafe, **params):
    return [r for r in psafe.records if match_valid(r, **params)]


def new_safe(filename, password, username=None, dbname=None, dbdesc=None):
    safe = PWSafe3(filename=filename, password=password, mode="RW")

    # Set details
    safe.setVersion()
    safe.setTimeStampOfLastSave(datetime.datetime.now())
    safe.setUUID()
    safe.setLastSaveApp("psafecli")

    if username:
        safe.setLastSaveUser(username)

    try:
        safe.setLastSaveHost(getfqdn())
    except Exception:
        pass

    if dbname:
        safe.setDbName(dbname)
    if dbdesc:
        safe.setDbDesc(dbdesc)

    safe.save()


def add_or_update_record(psafe, record, options):
    """Adds an entry to the given psafe, Update if it already exists.

    Reloads the psafe data once complete.
    """
    now = datetime.datetime.now()

    if record is None:
        record = Record()
        record.setCreated(now)
    else:
        record.setEntryModified(now)

    if options.username:
        record.setUsername(options.username)

    if options.password:
        record.setPassword(options.password)

    record.setLastAccess(now)
    record.setPasswordModified(now)

    if options.group:
        record.setGroup(options.group)

    if options.title:
        record.setTitle(options.title)

    if options.UUID:
        record.setUUID(options.UUID)

    if options.expires:
        record.setExpires(options.expires)

    if options.url:
        record.setURL(options.url)

    if options.email:
        record.setEmail(options.email)

    psafe.records.append(record)
    psafe.save()
    return record.getUUID()


def collect_record_options(options):
    collected = {}
    potentials = ["group", "title", "username", "UUID"]
    for item in potentials:
        value = getattr(options, item)
        if value is not None:
            collected[item] = value
    return collected


def show_records(records, attributes):
    if not attributes:
        # show all attributes
        attributes = VALID_ATTRIBUTES

    for record in records:
        print("[")
        for i in attributes:
            attr = i
            if not i[0].isupper():
                attr = attr.title()
            print("    %s: %s" % (attr, get_record_attr(record, i)))
        print("]")


def get_safe(filename, password):
    safe = None
    try:
        safe = PWSafe3(filename=filename, password=password, mode="RW")
    except PasswordError:
        raise PWSafeCLIError("Invalid password for safe")
    return safe


class Locked:
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        self.lock.lock()

    def __exit__(self, type, value, tb):
        self.lock.unlock()


def dump_action(options):
    safe = get_safe(options.filename, options.safe_password)

    with Locked(safe):
        if not safe.records:
            raise PWSafeCLIError("No records")

        show_records(safe.records, options.display)


def get_action(options):
    record_options = collect_record_options(options)

    safe = get_safe(options.filename, options.safe_password)

    with Locked(safe):
        records = get_matching_records(safe, **record_options)
        if not records:
            raise PWSafeCLIError("No records matching %s found" % record_options)

        show_records(records, options.display)


def init_action(options):
    new_safe(options.filename, options.safe_password, options.username,
             options.dbname, options.dbdesc)


def add_action(options):
    safe = get_safe(options.filename, options.safe_password)
    with Locked(safe):
        result = add_or_update_record(safe, None, options)
    if options.verbose:
        print(result)


def delete_action(options):
    safe = get_safe(options.filename, options.safe_password)

    with Locked(safe):
        records = get_matching_records(safe, {"UUID": options.UUID})
        count = len(records)
        if count == 0:
            raise PWSafeCLIError("no matching records found")
        elif count > 1:
            raise NotImplementedError("implement multiple record choice")

        safe.records.remove(records[0])
        safe.save()


def update_action(options):
    record_options = collect_record_options(options)

    safe = get_safe(options.filename, options.safe_password)

    with Locked(safe):
        records = get_matching_records(safe, **record_options)
        count = len(records)
        if count == 0:
            raise PWSafeCLIError("No records matching %s found" % record_options)
        elif count > 1:
            raise NotImplementedError("implement multiple record choice")
        add_or_update_record(safe, records[0], options)


def make_parser():
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--debug", action="store_true")

    parser.add_argument("-f", "--file", dest="filename", metavar="FILE", required=True,
                        help="use FILE as PWSafe container")

    common_record_parser = ArgumentParser(add_help=False)
    common_record_parser.add_argument("--email", help="e-mail for contact person of record")
    common_record_parser.add_argument("--group", type=lambda v: v.split("."), help="group of record")
    common_record_parser.add_argument("--title", help="title of record")
    common_record_parser.add_argument("--username", help="user of record")
    common_record_parser.add_argument("--uuid", dest="UUID", type=UUID, help="UUID of record")

    record_parser = ArgumentParser(add_help=False)
    record_parser.add_argument("--expires", type=lambda v: time.strptime(v, "%Y-%m-%d %H:%M"),
                               help="date record expires; ex. 2014-07-03 15:30"),
    record_parser.add_argument("--password", help="password of record (not the safe itself)"),
    record_parser.add_argument("--url", help="URL for Record"),

    display_parser = ArgumentParser(add_help=False)
    display_parser.add_argument("--display", action="append", required=False,
                                choices=VALID_ATTRIBUTES,
                                help="record attributes to display")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    parents = [display_parser]
    sub = subparsers.add_parser("dump", parents=parents, help="dump data")
    sub.set_defaults(action=dump_action)

    parents = [common_record_parser, display_parser]
    sub = subparsers.add_parser("get", parents=parents, help="get a record")
    sub.set_defaults(action=get_action)

    sub = subparsers.add_parser("init", help="initialize a safe")
    sub.add_argument("--dbname", help="name of new db")
    sub.add_argument("--dbdesc", help="description of new db")
    sub.add_argument("--username", help="user of safe")
    sub.set_defaults(action=init_action)

    parents = [common_record_parser, record_parser]
    sub = subparsers.add_parser("add", parents=parents, help="add a record")
    sub.set_defaults(action=add_action)

    sub = subparsers.add_parser("delete", help="delete a record")
    sub.add_argument("--uuid", dest="UUID", type=UUID, required=True,
                     help="UUID of record")
    sub.set_defaults(action=delete_action)

    parents = [common_record_parser, record_parser]
    sub = subparsers.add_parser("update", parents=parents, help="update a record")
    sub.set_defaults(action=update_action)

    return parser


def main():
    parser = make_parser()
    arguments = parser.parse_args()

    try:
        if arguments.command == "get":
            if not any(getattr(arguments, attr) for attr in ["group", "title", "username", "UUID"]):
                raise PWSafeCLIValidationError("one of --group, --title, --username, --uuid must be specified")

        if arguments.command == "add":
            if arguments.title is None:
                raise PWSafeCLIValidationError("--title must be specified")
            if arguments.password is None:
                raise PWSafeCLIValidationError("--password must be specified")

        if arguments.command == "update":
            if arguments.UUID is None:
                raise PWSafeCLIValidationError("--uuid must be specified")
    except PWSafeCLIValidationError as e:
        parser.print_usage()
        print(e, file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("psafe")
    logger.setLevel(logging.DEBUG if arguments.debug else logging.INFO)

    arguments.safe_password = None
    if arguments.safe_password is None:
        arguments.safe_password = getpass("Enter the password for PWSafe3 file: %s\n> " % arguments.filename)

    try:
        arguments.action(arguments)
    except PWSafeCLIError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
