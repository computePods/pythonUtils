# The ComputePods Rules Manager component

import logging
import pathlib
import yaml

class NoRulesFile(Exception) :
  def __init__(self, aPath, msg=None) :
    self.rulesPath = aPath
    self.message   = msg

class NoRulesDirectory(NoRulesFile) :
 def __init__(self, aPath) :
   super().__init__(aPath)

def mergeYamlData(yamlData, newYamlData, thePath) :
  """ This is a generic Python merge. It is a *deep* merge and handles
  both dictionaries and arrays """

  if type(yamlData) is None :
    logging.error("yamlData should NEVER be None ")
    logging.error("Stoping merge at {}".format(thePath))
    return

  if type(yamlData) != type(newYamlData) :
    logging.error("Incompatible types {} and {} while trying to merge YAML data at {}".format(type(yamlData), type(newYamlData), thePath))
    logging.error("Stoping merge at {}".format(thePath))
    return

  if type(yamlData) is dict :
    for key, value in newYamlData.items() :
      if key not in yamlData :
        yamlData[key] = value
      elif type(yamlData[key]) is dict :
        mergeYamlData(yamlData[key], value, thePath+'.'+key)
      elif type(yamlData[key]) is list :
        for aValue in value :
          yamlData[key].append(aValue)
      else :
        yamlData[key] = value
  elif type(yamlData) is list :
    for value in newYamlData :
      yamlData.append(value)
  else :
    logging.error("YamlData MUST be either a dictionary or an array.")
    logging.error("Stoping merge at {}".format(thePath))
    return

class RulesManager :
  """The ComputePods RulesManager loads, parses and maintains the build
  rules for a ComputePod Chef."""

  def __init__(self, chefName, natsClient) :
    self.chefName  = chefName
    self.nc        = natsClient
    self.rulesData = { "types" : {} }

  def loadRulesFrom(self, aRulesDir) :
    """Load rules from YAML files in the directory provided"""

    someRules = pathlib.Path(aRulesDir)
    if not someRules.is_dir() :
      logging.error("No rules directory found at [{}]".format(someRules))
      raise NoRulesDirectory(str(someRules))

    for aFile in someRules.iterdir() :
      if aFile.is_dir() :
        self.loadRulesFrom(aFile)
      else:
        if aFile.suffix.upper() in [ '.YAML', '.YML'] :
          with open(aFile) as rulesFile :
            try :
              logging.info("loading rules from [{}]".format(aFile))
              newRulesData = yaml.safe_load(rulesFile)
              mergeYamlData(self.rulesData, newRulesData, "")

              for aType, value in self.rulesData['types'].items() :
                value['extensions'] = list(dict.fromkeys(value['extensions']))

            except Exception as err :
              logging.error("Could not load rules from [{}]\n{}".format(
                aFile,
                repr(err)
              ))
              raise NoRulesFile(str(aFile), repr(err))

  async def registerTypes(self) :
    theTypes = self.rulesData["types"]
    for aType in theTypes :
      await self.nc.sendMessage(
        "types.register",
        {
          "chefName"   : self.chefName,
          "typeName"   : aType,
          "extensions" : theTypes[aType]['extensions']
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