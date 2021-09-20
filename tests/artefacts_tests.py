import asyncio
import unittest
import yaml

from cputils.natsClient import NatsClient

from cputils.artefactManager import ArtefactManager
from cputils.rulesManager    import RulesManager

from tests.testUtils import asyncTestOfProcess

class TestArtefactsManager(unittest.TestCase) :
  """Test the ArtefactsManager"""

  def artefactTypeTests(t, am, name, extensions) :
    at = am.types
    t.assertTrue(name in at)
    aType = at[name]
    t.assertTrue('name' in aType)
    t.assertEqual(aType['name'], name)
    t.assertTrue('extensions' in aType)
    t.assertEqual(aType['extensions'], extensions)
    del at[name]

  @asyncTestOfProcess(None)
  async def test_listenForTypes(t) :
    """Test the ArtefactManager's ability to listen for types messages."""

    nc = NatsClient("artefactTypesListener", 10)
    await nc.connectToServers(["nats://localhost:8888"])

    am = ArtefactManager(nc)
    await am.listenForArtefactMessages()

    rm = RulesManager()
    rm.loadRulesFrom('examples/rulesManager')
    await rm.registerTypes(nc)
    await asyncio.sleep(1)
    await am.waitUntilSettled()

    t.artefactTypeTests(
      am,
      'cCodeFile',
      [ "*.c" ]
    )
    t.artefactTypeTests(
      am,
      'cHeaderFile',
      [ "*.h" ]
    )
    t.artefactTypeTests(
      am,
      'contextDocument',
      [ "*.tex" ]
    )
    t.artefactTypeTests(
      am,
      'pdfFile',
      [ "*.pdf" ]
    )
    t.assertEqual(len(am.types), 0)