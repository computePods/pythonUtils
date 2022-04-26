# The ComputePods Projects Manager component

import yaml

import cputils.yamlLoader

def fixUpProjDir(configData, yamlPath, newYamlData) :
  if 'projects' not in newYamlData : return
  for projName, projDesc in newYamlData['projects'].items() :
    if 'targets' not in projDesc : continue
    targets = projDesc['targets']
    if 'defaults' not in targets: targets['defaults'] = {}
    defaults = targets['defaults']
    if 'projectDir' not in defaults :
      defaults['projectDir'] = str(yamlPath.parent)

class ProjectsManager :
  """The ComputePods ProjectsManager loads, parse and maintains the project
  details for a user's use of a federation of ComputePods."""

  def __init__(self, chefName, natsClient) :
    self.chefName  = chefName
    self.nc        = natsClient
    self.projectData = {
      'projects' : {}
    }

  def loadProjectsFrom(self, aProjectDir) :
    """Load project from YAML files in the directory provided"""

    cputils.yamlLoader.loadYamlFrom(
      self.projectData,
      aProjectDir,
      [ '.PYML'],
      fixUpProjDir
    )

  async def registerProjects(self) :
    theProjects = self.projectData['projects']
    for aProject, theProject in theProjects.items() :
      await self.nc.sendMessage(
      "register.projects",
      {
        "chefName"    : self.chefName,
        "projectName" : aProject,
        "theProject"  : theProject
      },
        0.1
      )

