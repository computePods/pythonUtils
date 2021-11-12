"""
The ComputePods Code Runner component
"""

class CodeRunner :
  """The CodeRunner class"""

  def __init__(self, cwd) :
    self.cwd = cwd

  def run(self, aCommand) :
    print(f"Run: [{aCommand}]")
