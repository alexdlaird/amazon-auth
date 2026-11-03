__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import re
import unittest

import amazonauth


class TestPackage(unittest.TestCase):
    def test_version_is_semantic(self):
        # GIVEN
        semantic_version = re.compile(r"^\d+\.\d+\.\d+$")

        # WHEN
        version = amazonauth.__version__

        # THEN
        self.assertRegex(version, semantic_version)
