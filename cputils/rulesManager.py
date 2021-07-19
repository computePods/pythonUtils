# The ComputePods Rules Manager component

import pathlib
import yaml

def loadRules(aRulesDir) :
  someRules = pathlib.Path(aRulesDir)
  if someRules.is_dir() :
    for aFile in someRules.iterdir() :
      with open(aFile) as rulesFile :
        print("\n-------------------------------------------------")
        print(f"loading {aFile}")
        rulesData = yaml.safe_load(rulesFile)
        print(yaml.dump(rulesData))
        print("-------------------------------------------------")
