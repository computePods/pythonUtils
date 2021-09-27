# The ComputePods TasksFile Manager component

import cputils.yamlLoader

class TasksManager :
  """The ComputePods TasksManager loads, parses and maintains the build
  tasks for a ComputePod Chef."""

  def __init__(self, chefName, natsClient) :
    self.chefName  = chefName
    self.nc        = natsClient
    self.tasksData = {
      "tasks" : {}
    }

  def loadTasksFrom(self, aProjectDir) :
    """Load build tasks from YAML files in the directory provided"""

    cputils.yamlLoader.loadYamlFrom(self.tasksData, aProjectDir, [ '.TYML'])

  async def registerTasks(self) :
    theTasks = self.tasksData['tasks']
    for aTask in theTasks :
      theTask = theTasks[aTask]
      await self.nc.sendMessage(
      "register.tasks",
      {
        "chefName" : self.chefName,
        "taskName" : aTask,
        "theTask"  : theTask
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