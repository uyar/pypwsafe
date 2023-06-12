from pytest import fixture

import logging
from pathlib import Path
from shutil import copyfile, rmtree
from tempfile import mkdtemp

from pypwsafe import PWSafe3


logging.basicConfig(level=logging.DEBUG, filename="/tmp/pypwsafe_tests.log",
                    filemode="w")


TEST_SAFES = Path(__file__).parent / "test_safes"

TEST_PASSWORD = "bogus12345"


@fixture()
def test_safe():
    """Function for opening a given test safe in a given mode."""
    safe_dir = mkdtemp(prefix="pypwsafe_test_")

    def _get_safe(name, mode):
        safe_path = TEST_SAFES / name
        safe_copy = Path(safe_dir) / name
        copyfile(safe_path, safe_copy)
        return PWSafe3(filename=safe_copy, password=TEST_PASSWORD, mode=mode)

    yield _get_safe

    rmtree(safe_dir)
