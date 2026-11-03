__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import shutil
import unittest

from amazonauth import conf
from amazonauth.conf import AmazonAuthConfig


class UnitTestCase(unittest.TestCase):
    def setUp(self):
        # Temporarily clear any config set in the environment, so it doesn't interfere with unit tests
        self.cleared_environment = {name: os.environ.pop(name) for name in list(os.environ)
                                    if name.startswith(conf.ENVIRONMENT_VARIABLE_PREFIX)}

        conf.DEFAULT_CONFIG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".config")
        self.test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "output")
        self.test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.json")
        self.test_config = AmazonAuthConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "auth_reattempt_wait": 0,
            "max_auth_retries": 0
        })

        if os.path.exists(self.test_cookie_jar_path):
            os.remove(self.test_cookie_jar_path)

    def tearDown(self):
        if os.path.exists(conf.DEFAULT_CONFIG_DIR):
            shutil.rmtree(conf.DEFAULT_CONFIG_DIR)

        # Reset environment variables that were temporarily cleared
        os.environ.update(self.cleared_environment)
