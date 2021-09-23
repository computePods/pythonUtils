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

      if 'dependencies' not in theRule :
        theRule['dependencies'] = []
      if 'secondaryDependencies' not in theRule :
        theRule['secondaryDependencies'] = []
      if 'outputs' not in theRule :
        theRule['outputs'] = []

      addMessageValue(
        rules[ruleName]['dependencies'],
        theRule['dependencies'],
        chefName
      )

      addMessageValue(
        rules[ruleName]['secondaryDependencies'],
        theRule['secondaryDependencies'],
        chefName
      )

      addMessageValue(
        rules[ruleName]['outputs'],
        theRule['outputs'],
        chefName
      )

      def extendType(baseType, *args) :
        args = list(args)
        lastArg = args.pop()
        for anArg in args :
          if anArg not in baseType :
            baseType[anArg] = { }
          baseType = baseType[anArg]
        baseType[lastArg] = True

      for aDependency in theRule['dependencies'] :
        for anOutput in theRule['outputs'] :
          extendType(
           types, aDependency, 'creates',   anOutput,    ruleName, chefName)
          extendType(
           types, anOutput,    'createdBy', aDependency, ruleName, chefName)

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

  def createTupGraphDot(self, dotPath) :
    types = self.types
    print(yaml.dump(types))
    with open(dotPath,'w') as dot :
      dot.write('strict digraph {\n')
      ruleNames = { }
      for fromTypeName, fromType in types.items() :
        if 'creates' in fromType :
          for toTypeName, toType in fromType['creates'].items() :
            for ruleName in toType :
              ruleNames[ruleName] = True
              dot.write("  {} -> {}\n".format(fromTypeName, ruleName))
              dot.write("  {} -> {}\n".format(ruleName,     toTypeName))
      dot.write("\n")
      for ruleName in ruleNames :
        dot.write("  {} [shape=box, style=filled, fillcolor=\"yellow\"]\n".format(ruleName))
      dot.write('}\n')