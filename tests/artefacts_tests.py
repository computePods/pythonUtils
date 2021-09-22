import asyncio
import unittest
import yaml

from cputils.natsClient import NatsClient

from cputils.artefactManager import ArtefactManager
from cputils.rulesManager    import RulesManager

from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
   hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestArtefactsManager(unittest.TestCase) :
  """Test the ArtefactsManager"""

  pass