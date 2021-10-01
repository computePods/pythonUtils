# The ComputePods Projects Manager component

import yaml

import cputils.yamlLoader

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

    cputils.yamlLoader.loadYamlFrom(self.projectData, aProjectDir, [ '.PYML'])

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

