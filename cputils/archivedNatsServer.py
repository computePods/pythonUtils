import aiofiles
import asyncio
import json
import logging
import os
import signal

class NatsServer :

  def __init__(self) :
    self.processObj = None
    self.returnCode = 1
    self.config     = {
      'listen': '0.0.0.0:4222'
    }
    self.routes     = [ "0.0.0.0:4222" ]
    self.shutdown   = False

  async def _writeRoutes(self) :
    """Private: format and write out the nats-server routes table"""
    routesTable = []
    for aRoute in self.routes :
      routesTable.append("nats-routes:://{}".format(aRoute))
    routesDict = { 'cluster' : { 'routes': routesTable } }
    routesConfig = json.dumps(routesDict, sort_keys=True, indent=2)
    async with aiofiles.open('/etc/nats/routes.conf', 'w') as f :
      await f.write(routesConfig)

  async def _writeConfig(self) :
    makedirs = aiofiles.os.wrap(os.makedirs)
    await makedirs('/etc/nats', exist_ok=True)
    await self._writeRoutes()
    async with aiofiles.open('/etc/nats/config.conf', 'w') as f :
      await f.write("\nlisten: \"0.0.0.0:4222\"\ninclude ./routes.conf\n")

  async def runNatsServer(self) :
    """Run the NATS server."""
    logging.info("runNatsServer starting...")
    await self._writeConfig()
    while not self.shutdown :
      self.processObj = await asyncio.create_subprocess_exec(
        "nats-server",
        "-c", "/etc/nats/config.conf",
        "-l", "/tmp/nats.log"
      )
      self.returnCode = None
      self.returnCode = await self.processObj.wait()
    self.processObj = None
    
  async def waitUntilRunning(self, pkgName) :
    logging.info("{} waiting for NatsServer".format(pkgName))
    while not self.isRunning() :
      await asyncio.sleep(1)
    await asyncio.sleep(1)
    logging.info("{} NatsServer started".format(pkgName))

  def isRunning(self) :
    return (self.processObj is not None)  and (self.returnCode is None)

  def getReturnCode(self) :
    return self.returnCode

  def getRoutes(self) :
    """Get the current collection of known routes as <user>:<pwd>@<host>:<port>"""
    return self.routes

  async def updateRoutes(self, routes) :
    """Change config on disk and then reload."""
    logging.info("natServer.updateRoutes starting")
    self.routes = routes
    #
    # write out config in YAML
    #
    self._writeRoutes()
    #
    # Now tell the nats-server to update the configuration
    #
    if self.processObj :
      #
      # see: https://docs.nats.io/nats-server/nats_admin/signals
      #
      self.processObj.send_signal(signal.SIGHUP) 
    logging.info("natServer.updateRoutes finished")

  async def stopServer(self) :
    """Stop the currently running server."""
    logging.info("natsServer.stopServer shutting down nats-server")
    self.shutdown = True
    if self.processObj :
      #
      # see: https://docs.nats.io/nats-server/nats_admin/signals
      #
      self.processObj.send_signal(signal.SIGINT)
      #self.processObj.send_signal(signal.SIGUSR2) 
