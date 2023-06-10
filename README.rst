Introduction
============

A Python library that can read and write Password Safe v3 files.
It includes full support for almost all current Password Safe v3
database headers and record headers.

History
=======

The original library was initially written by Paulson McIntyre
for Symantec in 2009.
It was later released by Symantec under the GPLv2 in 2011.
Changes and updates have been made since by Paulson McIntyre (GpMidi),
Evan Deaubl (evandeaubl), and Sean Perry (shaleh).
Rony Shapiro (ronys) maintains the project page and acts as gate keeper
for new patches.

Turgut Uyar forked the code in 2023 and is updating it for Python 3.

Known Issues
============ 

* Lack of documentation

* Unit tests are out-of-date

* There MAY be an issue with the order that NonDefaultPrefsHeader
  serializes preferences for HMAC validation.
  Although the library validates HMACs fine at the moment, so who knows. 

Dependencies
============

* pygcrypt (requires libgcrypt development files and cffi)

TODO
====

* Add support for using a pure-Python TwoFish algorithm.
* Update against the latest version of the official psafe format v3 doc.
