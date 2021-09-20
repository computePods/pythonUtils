import yaml

from cputils.settlingTimerMixin import mixinSettlingTimer

class ArtefactManager :
  """ The ComputePods Artefact Manager component. """

  def __init__(self, natsClient) :
    self.types = {}
    self.nc    = natsClient

    mixinSettlingTimer(self)

  async def listenForArtefactMessages(self) :

    async def typesCallback(aSubject, theSubject, theMessage) :
      self.unSettle()

      typeStr = theSubject.removeprefix('artefact.register.type.')
      self.types[typeStr] = {
        'name'       : theMessage['name'],
        'extensions' : theMessage['extensions']
      }
    await self.nc.listenToSubject('artefact.register.type.>', typesCallback)
