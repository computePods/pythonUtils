# The ComputePods Project Manager component

import yaml

import cputils.yamlLoader

class ProjectManager :
  """The ComputePods ProjectManager loads, parse and maintains the project
  details for a user's use of a federation of ComputePods."""

  def __init__(self, chefName, natsClient) :
    self.chefName  = chefName
    self.nc        = natsClient
    self.projectData = {
    }

  def loadProjectFrom(self, aProjectDir) :
    """Load project from YAML files in the directory provided"""

    cputils.yamlLoader.loadYamlFrom(self.projectData, aProjectDir, [ '.PYML'])
