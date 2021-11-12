""" The **codeManager_tests** module collects various tests of the
**CodeRunner**. """

import asyncio
import os
import shutil
import unittest
from unittest.mock import patch
import yaml

from cputils.natsClient import NatsClient
from cputils.codeRunner import CodeRunner
from tests.testUtils import asyncTestOfProcess

cputilsTestDir    = '/tmp/cputils-tests-codeRunner'

class TestCodeRunner(unittest.TestCase):
  """ Test the Code Runner. """


  # Create a simple directory structure, cputilsTestDir, in /tmp which we
  # can use in our tests.
  #
  def setUpClass() :
    """ Setup the tests by creating a private directory in /tmp """

    os.makedirs(os.path.join(cputilsTestDir, 'test01'), exist_ok=True)
    os.system("tree "+ cputilsTestDir)
    with open(os.path.join(cputilsTestDir, 'test01', 'silly.txt'), 'w') as f :
      f.write("This is a test")

  # Remove the cputilsTestDir directories
  #
  def tearDownClass() :
    """ Tear down the private directory in /tmp """

    shutil.rmtree(cputilsTestDir)

  def test_runningBashScript(t) :
    """Test running a simple bash script"""

    resultFile = "{}/test_runningBashScript".format(cputilsTestDir)

    cr = CodeRunner('.')
    cr.run("cp /etc/hosts {}".format(resultFile))
    # assert that the result file now exists

