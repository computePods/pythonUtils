import yaml

from cputils.settlingTimerMixin import mixinSettlingTimer

class ArtefactManager :
  """ The ComputePods Artefact Manager component. """

  def __init__(self, natsClient) :
    self.nc    = natsClient

    mixinSettlingTimer(self)
