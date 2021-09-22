import yaml

from cputils.settlingTimerMixin import mixinSettlingTimer

class TypesManager :
  """ The ComputePods Types Manager component """

  def __init__(self, natsClient) :
    self.types = { }
    self.nc    = natsClient

    mixinSettlingTimer(self)
    self.addSettlingTimer(
      'typeRegistration', 0.5, self.typeRegistrationSettled
    )

  def getTypeNames(self) :
    return sorted(self.types.keys())

  async def listenForTypeMessages(self) :

    async def typesCallback(aSubject, theSubject, theMessage) :
      await self.unSettle('typeRegistration')
      types = self.types

      chefName       = theMessage['chefName']
      typeName       = theMessage['typeName']
      typeExtensions = theMessage['extensions']

      if typeName not in self.types :
        types[typeName] = {
          'typeName'   : typeName,
          'extensions' : { }
        }

      extensions = types[typeName]['extensions']
      for anExtension in typeExtensions :
        if anExtension not in extensions :
          extensions[anExtension] = { }
        extensions[anExtension][chefName] = True

    await self.nc.listenToSubject('types.register', typesCallback)

  async def typeRegistrationSettled(self) :
    await self.nc.sendMessage(
      'types.registered',
      self.getTypeNames()
    )

  async def listenForDependencyMessages(self) :

    async def registeredTypesCallback(aSubject, theSubject, theMessage) :
      self.unSettle()

      for aType in theMessage :
        await self.nc.sendMessage('build.howTo.{}'.format(aType))

    await self.nc.listenToSubject(
      'types.register',
      registeredTypesCallback
    )
