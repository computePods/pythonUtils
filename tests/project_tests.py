import asyncio
import shutil
import unittest
from unittest.mock import patch
import yaml

import inspect

from cputils.natsClient import NatsClient
from cputils.yamlLoader import NoYamlFile, NoYamlDirectory
from cputils.projectManager import ProjectManager
from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
  hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestProjectManager(unittest.TestCase):
  """ Test the Project Manager. """

  @patch('cputils.yamlLoader.logging')
  def test_loadProjectWithNoDir(t, mock_logging) :
    """Test loading a project from a directory which does not exist"""

    pm = ProjectManager('loadProjectithNoDir', None)
    with t.assertRaises(NoYamlDirectory) as nrd :
      pm.loadProjectFrom("/this/directory/does/not/exist")
    t.assertEqual(nrd.exception.yamlPath, "/this/directory/does/not/exist")
    mock_logging.error.assert_called_with(
      'No YAML directory found at [/this/directory/does/not/exist]'
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadProjectWithBrokenYaml(t, mock_logging) :
    """Test loading project from a broken YAML file"""

    pm = ProjectManager('loadProjectWithBrokenYaml', None)
    with t.assertRaises(NoYamlFile) as nrf :
      pm.loadProjectFrom("examples/projectManager/brokenProject")
    t.assertEqual(nrf.exception.yamlPath, "examples/projectManager/brokenProject/shouldNotLoad.pyml")
    t.assertRegex(nrf.exception.message, r"ScannerError.*mapping values")
    t.assertRegex(
      repr(mock_logging.error.call_args_list),
      r"ScannerError.*mapping values"
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadProject(t, mock_logging) :
    """ When loading a project... """

    pm = ProjectManager('loadProject', None)
    pm.loadProjectFrom('examples/projectManager/joylol')
    t.assertNotEqual(pm, {})

  ##########################################################################
  # Registering Artefact Types

  @unittest.skip
  @asyncTestOfProcess(None)
  async def test_registerProject(t) :
    """ Make sure that any new Artefact types are sent to the
    ArtefactManager via NATS. """

    nc = NatsClient("natsTypesListener", 10)
    await nc.connectToServers(["nats://localhost:8888"])
