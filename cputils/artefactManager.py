import yaml

from cputils.settlingTimerMixin import mixinSettlingTimer

class ArtefactManager :
  """ The ComputePods Artefact Manager component. """

  def __init__(self, natsClient) :
    self.artefacts = { }
    self.tasks     = { }
    self.nc        = natsClient

    mixinSettlingTimer(self)
    self.addSettlingTimer(
      'taskRegistration', 0.5, self.taskRegistrationSettled
    )

  def getArtefactNames(self) :
    return sorted(self.artefacts.keys())

  def getTaskNames(self) :
    return sorted(self.tasks.keys())

  async def taskRegistrationSettled(self) :

    await self.nc.sendMessage(
      'registered.artefacts',
      self.getArtefactNames()
    )

    await self.nc.sendMessage(
      'registered.tasks',
      self.getTaskNames()
    )

  async def listenForTaskMessages(self) :

    def addMessageValue(values, msgValues, chefName) :
      for aValue in msgValues :
        if aValue not in values :
          values[aValue] = { }
        values[aValue][chefName] = True

    async def tasksCallback(aSubject, theSubject, theMessage) :
      await self.unSettle('taskRegistration')
      artefacts = self.artefacts
      tasks     = self.tasks

      chefName = theMessage['chefName']
      taskName = theMessage['taskName']
      theTask  = theMessage['theTask']

      if taskName not in tasks :
        tasks[taskName] = {
          'taskName'              : taskName,
          'rule'                  : { },
          'dependencies'          : { },
          'secondaryDependencies' : { },
          'outputs'               : { }
        }

      if 'dependencies' not in theTask :
        theTask['dependencies'] = []
      if 'secondaryDependencies' not in theTask :
        theTask['secondaryDependencies'] = []
      if 'outputs' not in theTask :
        theTask['outputs'] = []

      if 'rule' in theTask :
        theRule = theTask['rule']
        if theRule not in tasks[taskName]['rule'] :
          tasks[taskName]['rule'][theRule] = { }
        tasks[taskName]['rule'][theRule][chefName] = True

      addMessageValue(
        tasks[taskName]['dependencies'],
        theTask['dependencies'],
        chefName
      )

      addMessageValue(
        tasks[taskName]['secondaryDependencies'],
        theTask['secondaryDependencies'],
        chefName
      )

      addMessageValue(
        tasks[taskName]['outputs'],
        theTask['outputs'],
        chefName
      )

      def extendArtefact(baseType, *args) :
        args = list(args)
        lastArg = args.pop()
        for anArg in args :
          if anArg not in baseType :
            baseType[anArg] = { }
          baseType = baseType[anArg]
        baseType[lastArg] = True

      for aDependency in theTask['dependencies'] :
        for anOutput in theTask['outputs'] :
          extendArtefact(
           artefacts, aDependency, 'creates',   anOutput,    taskName, chefName)
          extendArtefact(
           artefacts, anOutput,    'createdBy', aDependency, taskName, chefName)

      for aDependency in theTask['secondaryDependencies'] :
        for anOutput in theTask['outputs'] :
          extendArtefact(
           artefacts, aDependency, 'usedBy', anOutput,    taskName, chefName)
          extendArtefact(
           artefacts, anOutput,    'uses',   aDependency, taskName, chefName)

    await self.nc.listenToSubject('register.tasks', tasksCallback)

  def createTupGraphDot(self, dotPath) :
    artefacts = self.artefacts
    with open(dotPath,'w') as dot :
      dot.write('strict digraph {\n')
      taskNames = { }
      for fromArtefactName, fromArtefact in artefacts.items() :
        if 'creates' in fromArtefact :
          for toArtefactName, toArtefact in fromArtefact['creates'].items() :
            for taskName in toArtefact :
              taskNames[taskName] = True
              dot.write("  \"{}\" -> \"{}\"\n".format(fromArtefactName, taskName))
              dot.write("  \"{}\" -> \"{}\"\n".format(taskName,         toArtefactName))
        if 'usedBy' in fromArtefact :
          for toArtefactName, toArtefact in fromArtefact['usedBy'].items() :
            for taskName in toArtefact :
              taskNames[taskName] = True
              dot.write("  \"{}\" -> \"{}\"\n".format(fromArtefactName, taskName))
              dot.write("  \"{}\" -> \"{}\"\n".format(taskName,         toArtefactName))
      dot.write("\n")
      for taskName in taskNames :
        dot.write("  \"{}\" [shape=box, style=filled, fillcolor=\"yellow\"]\n".format(taskName))
      dot.write('}\n')
