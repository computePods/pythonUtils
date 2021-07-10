import asyncio
import json
import logging
import os
import platform

from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers

async def natsClientError(err) :
  logging.error("NatsClient : {err}".format(err=err))

async def natsClientClosedConn() :
  logging.warn("NatsClient : connection to NATS server is now closed.")

async def natsClientReconnected() :
  logging.info("NatsClient : reconnected to NATS server.")

class NatsClient :

  def __init__(self, aContainerName, aHeartBeatPeriod) :
    self.nc = NATS()
    self.containerName = aContainerName
    self.heartBeatPeriod = aHeartBeatPeriod
    self.shutdown   = False

  async def heartBeat(self) :
    logging.info("NatsClient: starting heartbeat")
    while not self.shutdown :
      logging.debug("NatsClient: heartbeat")
      loadAvg = os.getloadavg()
      msg = "hello from {}-{} (1:{} 5:{} 15:{})".format(
        platform.node(), self.containerName,
        loadAvg[0], loadAvg[1], loadAvg[2]
      )
      await self.nc.publish("heartbeat", bytes(msg, 'utf-8'))
      await asyncio.sleep(self.heartBeatPeriod)

  async def sendMessage(self, aSubject, aMsg) :
    msgStr = json.dumps(aMsg)
    await self.nc.publish(aSubject, bytes(msgStr, 'utf-8'))

  async def listenToSubject(self, aSubject, aCallback) :
    print("listening to subject [{}]".format(aSubject))

    def subjectCallback(aNATSMessage) :
      theSubject = aNATSMessage.subject
      theJSONMsg = aNATSMessage.data
      theMsg = json.loads(theJSONMsg)
      aCallback(aSubject, theSubject, theMsg)

    await self.nc.subscribe(aSubject, cb=subjectCallback)

  async def connectToServers(self):
    await self.nc.connect(
      servers=["nats://127.0.0.1:4222"],
      error_cb=natsClientError,
      closed_cb=natsClientClosedConn,
      reconnected_cb=natsClientReconnected
    )

  async def closeConnection(self) :
    # Terminate connection to NATS.
    self.shutdown = True
    await asyncio.sleep(1)
    await self.nc.close()
