import yaml

from cputils.settlingTimerMixin import mixinSettlingTimer

class TypesManager :
  """ The ComputePods Types Manager component """

  def __init__(self, natsClient) :
    self.types = { }
    self.rules = { }
    self.nc    = natsClient

    mixinSettlingTimer(self)
    self.addSettlingTimer(
      'typeRegistration', 0.5, self.typeRegistrationSettled
    )
    self.addSettlingTimer(
      'rulesRegistration', 0.5, self.ruleRegistrationSettled
    )

  def getTypeNames(self) :
    return sorted(self.types.keys())

  def getRuleNames(self) :
    return sorted(self.rules.keys())

  async def listenForTypeMessages(self) :

    def addMessageValue(values, msgValues, chefName) :
      for aValue in msgValues :
        if aValue not in values :
          values[aValue] = { }
        values[aValue][chefName] = True

    async def typesCallback(aSubject, theSubject, theMessage) :
      await self.unSettle('typeRegistration')
      types = self.types

      chefName       = theMessage['chefName']
      typeName       = theMessage['typeName']
      typeExtensions = theMessage['extensions']

      if typeName not in types :
        types[typeName] = {
          'typeName'   : typeName,
          'extensions' : { }
        }

      addMessageValue(
        types[typeName]['extensions'],
        typeExtensions,
        chefName
      )
#      extensions = types[typeName]['extensions']
#      for anExtension in typeExtensions :
#        if anExtension not in extensions :
#          extensions[anExtension] = { }
#        extensions[anExtension][chefName] = True

    await self.nc.listenToSubject('register.types', typesCallback)

    async def rulesCallback(aSubject, theSubject, theMessage) :
      await self.unSettle('ruleRegistration')
      types = self.types
      rules = self.rules

      chefName = theMessage['chefName']
      ruleName = theMessage['ruleName']
      theRule  = theMessage['theRule']

      if ruleName not in rules :
        rules[ruleName] = {
          'ruleName'              : ruleName,
          'dependencies'          : { },
          'secondaryDependencies' : { },
          'outputs'               : { }
        }

      if 'dependencies' in theRule :
        addMessageValue(
          rules[ruleName]['dependencies'],
          theRule['dependencies'],
          chefName
        )

      if 'secondaryDependencies' in theRule :
        addMessageValue(
          rules[ruleName]['secondaryDependencies'],
          theRule['secondaryDependencies'],
          chefName
        )

      if 'outputs' in theRule :
        addMessageValue(
          rules[ruleName]['outputs'],
          theRule['outputs'],
          chefName
        )

    await self.nc.listenToSubject('register.rules', rulesCallback)

  async def typeRegistrationSettled(self) :
    await self.nc.sendMessage(
      'registered.types',
      self.getTypeNames()
    )

  async def ruleRegistrationSettled(self) :
    await self.nc.sendMessage(
      'registered.rules',
      self.getRuleNames()
    )


#  async def listenForDependencyMessages(self) :
#
#    async def registeredTypesCallback(aSubject, theSubject, theMessage) :
#      self.unSettle()
#
#      for aType in theMessage :
#        await self.nc.sendMessage('build.howTo.{}'.format(aType))
#
#    await self.nc.listenToSubject(
#      'types.register',
#      registeredTypesCallback
#    )
