"""
The NATS client
"""

import asyncio
import json
import logging
import os
import platform
import sys
import yaml

from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers

async def natsClientError(err) :
  """natsClientError is called whenever there is a general erorr
  associated with the NATS client or it connection to the NATS message
  system."""

  print("NatsClient : {}".format(repr(err)))

async def natsClientClosedConn() :
  """natsClientClosedConn is called whenever the NATS client closes its
  connection to the NATS message system."""

  print("NatsClient : connection to NATS server is now closed.")

async def natsClientReconnected() :
  """natsClientRecconnected is called whenever the NATS client reconnects
  to the NATS message system."""

  print("NatsClient : reconnected to NATS server.")

class NatsClient :
  """The NatsClient class manages a connection to the NATS message
  system."""

  def __init__(self, aContainerName, aHeartBeatPeriod) :
    self.nc = NATS()
    self.containerName   = aContainerName
    self.heartBeatPeriod = aHeartBeatPeriod
    self.shutdown        = False
    self.subscriptions   = [ ]

  async def heartBeat(self) :
    """heartBeat is a long running process which periodically sends a
    heart beat message via NATS to the federation of ComputePods. It stops
    running when the NatsClient::shutdown is True (see
    `stopHeardBeat`)."""

    logging.info("NatsClient: starting heartbeat")
    while not self.shutdown :
      logging.debug("NatsClient: heartbeat (shutdown: {})".format(self.shutdown))
      loadAvg = os.getloadavg()
      msg = "hello from {}-{} (1:{} 5:{} 15:{})".format(
        platform.node(), self.containerName,
        loadAvg[0], loadAvg[1], loadAvg[2]
      )
      msgStr = json.dumps(msg)
      await self.nc.publish("heartbeat", bytes(msgStr, 'utf-8'))
      await asyncio.sleep(self.heartBeatPeriod)

  def stopHeartBeat(self) :
    """stopHeartBeat sets the NatsClient::shutdown to True."""
    logging.info("NatsClient: stopping heartbeat")
    self.shutdown = True

  async def sendMessage(self, aSubject, aMsg, sleepTime=None) :
    """sendMessage sends the `aMsg` encoded using JSON, into the NATS
    message system using the subject `aSubject`."""

    msgStr = json.dumps(aMsg)
    await self.nc.publish(aSubject, bytes(msgStr, 'utf-8'))
    if sleepTime is None : sleepTime = 0.01
    if 0 <= sleepTime : await asyncio.sleep(sleepTime)

  def unpackMessage(self, callback) :
    async def callbackWithUnpackedMessage(msg) :
      unpackedSubject = msg.subject.split('.')
      unpackedSubject.insert(0, msg.subject)
      unpackedData    = msg.data.decode()
      if not type(unpackedData) == 'dict' :
        originalUnpackedData = unpackedData
        unpackedData = {
          str(type(originalUnpackedData).__name__) : originalUnpackedData
        }
      print(unpackedSubject[0])
      print(yaml.dump(unpackedSubject))
      print(yaml.dump(unpackedData))
      await callback(unpackedSubject, unpackedData)
    return callbackWithUnpackedMessage

  # A Python decorator (with an argument)
  # which records the subscription and callback
  # in a list for later processing
  #
  def subscribe(self, subscription) :
    def decorator_subscribe(callback) :
      self.subscriptions.append({
        'subscription' : subscription,
        'callback'     : callback
       })
    return decorator_subscribe

  async def listenForMessagesOnDecoratedSubscriptions(self) :
    logging.info("NatsClient: Listening to decorated subscriptions")
    for aSubscription in self.subscriptions :
      await self.nc.subscribe(
        aSubscription['subscription'],
        cb=self.unpackMessage(aSubscription['callback'])
      )

  async def listenToSubject(self, aSubject, aCallback) :
    """listenToSubject registers the callback `aCallback` to listen for
    all NATS messages matching the subject defined by the `aSubject`
    pattern. The received message is decoded from JSON into a Python
    structure.

     The callback `aCallback` must expect three arguments:

    - `aSubject` which is the original subject pattern used to register
      this callback with the NATS message system,

    - `theSubject` which is the actual subject used to send the associated
      message, and

    - `theMsg` which is the message structure which was send (decoded from
      the JSON).

    """

    logging.info("listening to subject [{}]".format(aSubject))

    async def subjectCallback(aNATSMessage) :
      theSubject = aNATSMessage.subject
      theJSONMsg = aNATSMessage.data.decode()
      theMsg = json.loads(theJSONMsg)
      await aCallback(aSubject, theSubject, theMsg)

    await self.nc.subscribe(aSubject, cb=subjectCallback, is_async=True)

  async def connectToServers(self, someServers=None):
    """connectToServers connects the NatsClient to a collection of NATS
    servers."""

    if someServers is None or len(someServers) < 1 :
      someServers=["nats://127.0.0.1:4222"],
    await self.nc.connect(
      servers=someServers,
      error_cb=natsClientError,
      closed_cb=natsClientClosedConn,
      reconnected_cb=natsClientReconnected
    )

  async def closeConnection(self) :
    """closeConnection closes the NatsClient's connection to the NATS
    message system."""

    # Terminate connection to NATS.
    self.shutdown = True
    await asyncio.sleep(1)
    await self.nc.close()
