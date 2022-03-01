import asyncio
import os
import shutil
import unittest
from unittest.mock import patch
import yaml

import json
import inspect

from cputils.natsClient import NatsClient
from cputils.yamlLoader import NoYamlFile, NoYamlDirectory
from cputils.projectsManager import ProjectsManager
from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
  hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestProjectsManager(unittest.TestCase):
  """ Test the Projects Manager. """

  @patch('cputils.yamlLoader.logging')
  def test_loadProjectsWithNoDir(t, mock_logging) :
    """Test loading projects from a directory which does not exist"""

    pm = ProjectsManager('loadProjectsWithNoDir', None)
    with t.assertRaises(NoYamlDirectory) as nrd :
      pm.loadProjectsFrom("/this/directory/does/not/exist")
    t.assertEqual(nrd.exception.yamlPath, "/this/directory/does/not/exist")
    mock_logging.error.assert_called_with(
      'No YAML directory found at [/this/directory/does/not/exist]'
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadProjecstWithBrokenYaml(t, mock_logging) :
    """Test loading projects from a broken YAML file"""

    pm = ProjectsManager('loadProjectsWithBrokenYaml', None)
    with t.assertRaises(NoYamlFile) as nrf :
      pm.loadProjectsFrom("../examples/projectsManager/brokenProject")
    t.assertEqual(nrf.exception.yamlPath, "../examples/projectsManager/brokenProject/shouldNotLoad.pyml")
    t.assertRegex(nrf.exception.message, r"ScannerError.*mapping values")
    t.assertRegex(
      repr(mock_logging.error.call_args_list),
      r"ScannerError.*mapping values"
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadProjects(t, mock_logging) :
    """ When loading a project... """

    pm = ProjectsManager('loadProject', None)
    pm.loadProjectsFrom('../examples/projectsManager/joylol')
    t.assertNotEqual(pm, {})

  ##########################################################################
  # Registering Artefact Types

  @asyncTestOfProcess(None)
  async def test_registerProjects(t) :
    """ Make sure that any new Artefact types are sent to the
    ArtefactManager via NATS. """

    nc = NatsClient("natsTypesListener", 10)
    await nc.connectToServers([
      os.getenv('NATS_SERVER', "nats://localhost:8888")
    ])

    projectsCollection = SettlingDict(timeOut=0.3)
    await natsListener(
      nc, messageCollector(projectsCollection),
      'register.projects'
    )

    pm = ProjectsManager('registerProjects', nc)
    pm.loadProjectsFrom('../examples/projectsManager/joylol')
    await pm.registerProjects()
    await asyncio.sleep(1)
    await projectsCollection.waitUntilSettled()
    t.assertEqual(len(projectsCollection), 1)
    t.assertTrue('register.projects' in projectsCollection)

    testProjects = { "joylolMainDocument" :
      {
        "chefName": "registerTasks",
        "projectName": "joylolMainDocument",
        "theProject": {
          "description": "This ConTeXt project has two primary goals:\n\\n\n1. Document the design of the JoyLoL engine\n2. Build an executable JoyLoL engine\n",
          "targets": {
            "document": {
              "help": "Typeset the JoyLoL document (pdf version)",
              "dependencies": [
                "joylol.tex"
              ],
              "outputs": [
                "joylol.pdf"
              ]
            },
            "html": {
              "help": "Typeset the JoyLoL document (html version)",
              "dependencies": [
                "joylol.tex"
              ],
              "outputs": [
                "joylol.html"
              ]
            },
            "joylol": {
              "help": "Build the JoyLoL engine",
              "dependencies": [
                "joylol.tex"
              ],
              "outputs": [
                "joylol"
              ]
            }
          },
          "directories": [
            "some/where"
          ]
        }
      }
    }
    msgs = projectsCollection['register.projects']
    for aProject in msgs :
      t.assertIn('chefName', aProject)
      t.assertEqual(aProject['chefName'], 'registerProjects')
      t.assertIn('projectName', aProject)
      projectName = aProject['projectName']
      t.assertIn(projectName, testProjects)
      testProject = testProjects[projectName]
      t.assertIn('theProject', aProject)
      theProject = aProject['theProject']
      for testKey in testProject['theProject'] :
        t.assertIn(testKey, theProject)
        for testValue in theProject[testKey] :
          t.assertIn(testValue, testProject['theProject'][testKey])
        for testValue in testProject['theProject'][testKey] :
          t.assertIn(testValue, theProject[testKey])
      for testKey in aProject['theProject'] :
        t.assertIn(testKey, testProject['theProject'])
