# The ComputePods Rules Manager component

import cputils.yamlLoader

class RulesManager :
  """The ComputePods RulesManager loads, parses and maintains the build
  rules for a ComputePod Chef."""

  def __init__(self, chefName, natsClient) :
    self.chefName  = chefName
    self.nc        = natsClient
    self.rulesData = {
      "types" : {},
      "rules" : {}
    }

  def loadRulesFrom(self, aRulesDir) :
    """Load rules from YAML files in the directory provided"""

    cputils.yamlLoader.loadYamlFrom(self.rulesData, aRulesDir)

    for aType, value in self.rulesData['types'].items() :
      value['extensions'] = list(dict.fromkeys(value['extensions']))

  async def registerRules(self) :
    theTypes = self.rulesData["types"]
    for aType in theTypes :
      await self.nc.sendMessage(
        "register.types",
        {
          "chefName"   : self.chefName,
          "typeName"   : aType,
          "extensions" : theTypes[aType]['extensions']
        },
        0.1
      )
    theRules = self.rulesData['rules']
    for aRule in theRules :
      origRule = theRules[aRule]
      theRule  = { }
      if 'dependencies' in origRule :
        theRule['dependencies'] = origRule['dependencies']
      if 'secondaryDependencies' in origRule :
        theRule['secondaryDependencies'] = origRule['secondaryDependencies']
      if 'outputs' in origRule :
        theRule['outputs'] = origRule['outputs']
      await self.nc.sendMessage(
      "register.rules",
      {
        "chefName" : self.chefName,
        "ruleName" : aRule,
        "theRule"  : theRule
      },
        0.1
      )

  async def listenForDependencyMessages(self, nc) :
    pass

    async def buildCallback(aSubject, theSubject, theMessage) :
      self.unSettle()

      typeStr = theSubject.removeprefix('build.howTo.')
      print("-----------------------------------------------------")
      print(yaml.dump(theMessage))
      print("-----------------------------------------------------")

    await nc.listenToSubject('build.howTo..>', buildCallback)