import yaml

from cputils.settlingTimerMixin import mixinSettlingTimer

class DependencyManager :
  """ The ComputePods Dependency Manager component """

  def __init__(self, natsClient) :
    self.nc    = natsClient

    mixinSettlingTimer(self)

  async def listenForDependencyMessages(self) :

    async def registeredTypesCallback(aSubject, theSubject, theMessage) :
      self.unSettle()

      for aType in theMessage :
        await self.nc.sendMessage('build.howTo.{}'.format(aType))

    await self.nc.listenToSubject(
      'artefact.registered.types',
      registeredTypesCallback
    )

    async def canBuildFromCallback(aSubject, theSubject, theMessage) :
      self.unSettle()


    await self.nc.listenToSubject(
      "build.from.>",
      canBuildFromCallback
    )