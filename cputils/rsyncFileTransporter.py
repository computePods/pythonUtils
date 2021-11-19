# The ComputePods Rsync over SSH file transporter component

import aiofiles
import os

async def runCmdNoUser(*cmd) :
  """Runs a command (with no user interaction) and returns the return
  code, stdout, and stderr as a tuple. Based upon the Python asyncio
  subprocesses documentation. """

  proc = await asyncio.create_subprocess_shell(
    cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE)

  stdout, stderr = await proc.communicate()

  if stdout: stdout = stdout.decode()
  if stderr: stderr = stderr.decode()

  return (proc.returncode, stdout, stderr)

async def runCmdWithUser(*cmd) :
  """Runs a command allowing the users to interact with the command and
  then returns the return code. Based upon the Python asyncio subprocesses
  documentation. """

  proc = await asyncio.create_subprocess_exec(*cmd, stdout=None, stderr=None)

  await proc.wait()

  return proc.returncode

defaultSshConfig = {
  'addCmd'         : '/usr/bin/ssh-add',
  'agentCmd'       : '/usr/bin/ssh-agent',
  'keyGenCmd'      : '/usr/bin/ssh-keygen',
  'dir'            : '~/.ssh',
  'authorizedKeys' : 'authorized_keys',
}

class RsyncFileTransporter :
  """The ComputePods Rsync over SSH file transporter component.

  To ensure secure and authenticated communication, this transporter
  component also includes SSH key management to manage the ssh keys
  required for the use of rsync on the user's behalf. This ssh key manager
  uses a combination of `ssh-agent`, `ssh-add`, and direct access to a
  given `authorized_keys` file. """

  def __init__(self, config) :
    """Setup the required configuration."""

    federationName = 'computePods'
    if 'federationName' in config :
      federationName = config['federationName']

    self.computePodsRsyncTag = f'{federationName}-rsync'

    timeNow = datetime.datetime.now().strftime("%Y.%m.%d-%H.%M.%S")
    self.keyComment = f'{timeNow}-{federationName}-rsync'

    sshConfig = { }
    if 'ssh' in config : sshConfig = config['ssh']
    mergYamlData(defaultSshConfig, sshConfig, '.')
    sshConfig = defaultSshConfig

    self.sshAddCmd    = sshConfig['addCmd']
    self.sshAgentCmd  = sshConfig['agentCmd']
    self.sshKeyGenCmd = sshConfig['keyGenCmd']

    self.sshDir = os.path.abspath(
      os.path.expanduser(sshConfig['dir'])
    )
    self.authKeyPath = os.path.join(
      self.sshDir, sshConfig['authorizedKeys']
    )

    self.computePodsDir = os.path.join(
      self.sshDir, 'computePods', federationName
    )
    if 'coomputePodsDir' in sshConfig :
      self.computePodsDir = os.path.abspath(
        os.path.expanduser(sshConfig['computePods'])
      )

    self.sshAgentSocket = os.path.join(
      self.computePodsDir, 'sshAgent.socket'
    )
    if 'agentSocket' in sshConfig :
      self.sshAgentSocket = os.path.abspath(
        os.path.expanduser(sshConfig['agentSocket'])
      )

    self.sshPrivateKeyPath = os.path.join(
      self.computePodsDir, 'rsync-rsa'
    )
    if 'privateKeyPath' in sshConfig :
      self.sshPrivateKeyPath = os.path.abspath(
        os.path.expanduser(sshConfig['privateKeyPath'])
      )

    self.sshPublicKeyPath = self.sshPrivateKeyPath+'.pub'

  ######################################################################
  # create a new key

  async def createdKey(self, config) :
    """Uses ssh-keygen to create a new key for a user. """

    retCode = await runCmdWithUser([
      self.sshKeyGenCmd,
      '-b=2048',
      '-t=rsa',
      '-C={}'.format(self.keyComment),
      '-f={}'.format(self.sshPrivateKey)
    ])

    return retCode == 0

  ######################################################################
  # work with an ssh-agent

  async def isSshAgentRunning(self) :
    """Check to see if the computePods ssh-agent is running. """

    retCode, stdout, stderr = await runCmdNoUser([
      self.sshAddCmd,
      '-q'
    ])

    return retCode == 0 and stderr

  async def isSshKeyLoaded(self) :
    """Check that the user's ComputePod key has been loaded. """

    retCode, stdout, _ = await runCmdNoUser([
      self.sshAddCmd,
      '-L'
    ])

    if retCode == 0 and stdout.endswith(keyPath) : return True
    return False

  async def startAgent(self) :
    """Setup and start an ssh-agent dedicated for the use of
    ComputePods."""

    if self.isSshAgentRunning() : return True

    retCode, _, _ = await runCmdNoUser([
      self.sshAgentCmd,
      '-a={}'.format(self.sshAgentSocket),
    ])

    return retCode == 0

  async def loadKey(self, config) :
    """Loads a given ssh key into the ComputePods ssh-agent."""

    if not self.isSshAgentRunning() : return False

    if self.isSshKeyLoaded() : return True

    retCode = await runCmdWithUser([
      self.sshAddCmd,
      self.sshPrivateKeyPath
    ])

    return retCode == 0

  async def unloadKey(self) :
    """Unloads a given ssh key from the ComputePods ssh-agent."""

    if not self.isSshAgentRunning() : return False

    retCode, _, _ = await runCmdNoUser([
      self.sshAddCmd,
      '-D'
    ])

    return retCode == 0

  ######################################################################
  # manipulation of a user's authorized_keys file

  async def enableKey(self, addKey=True) :
    """Add a specific key to a user's authorized_keys file."""

    # Get the current authorized_keys file contents (as an array of lines)
    #
    authKeys = None
    try :
      with aiofiles.open(self.authKeyPath, 'r') as authKeyFile :
        authKeys = await authKeyFile.readlines()
    except :
      pass

    if authKeys is None :
      print(f"Could not open the ssh authorized_keys file ({authKeyPath})")
      return False

    # Copy all the non-rsyncCtl keys to a new list of keys
    #
    newAuthKeys = []
    for aKey in authKeys :
      aKey = aKey.strip()
      if not aKey.endswith(self.computePodsRsyncTag) :
        newAuthKeys.append(aKey)

    # Add the rsyncCtl key to this new list of keys
    #
    if addKey :
      try :
        with aiofiles.open(self.sshPublicKeyPath, 'r') as publicKeyFile :
          publicKey = await publicKeyFile.readall()
      except :
        pass

      if publicKey :
        authKeyLine = "command=\"{} {}\" {}".format(
          rsyncCmd, rsyncDir, publicKey
        )
        newAuthKeys.append(authKeyLine)

    # Backup the existing authorized_keys file
    #
    timeNow = datetime.datetime.now().strftime("%Y.%m.%d-%H.%M.%S")
    await aiofiles.os.rename(
      self.authKeyPath, self.authKeyPath+'_cpBackup_'+timeNow
    )

    # Save the new authorized_keys file
    #
    with await aiofiles.open(self.authKeyPath, "w") as authKeyFile :
      await authKeyFile.write("\n".join(newAuthKeys))

  async def disableKey(self) :
    """Remove a specific key from a user's authorized_keys file."""

    return await self.enableKey(addKey=False)

  ######################################################################
  # provided command templates to use a user's private key

  def getPrivateKeyPath(self) :
    """Returns the path to a user's ComputePods private ssh key for use by
    other commands."""

    return self.sshPrivateKeyPath

  def getPublicKeyPath(self) :
    """Returns the path to a user's ComputePods public ssh key for use by
    other commands."""

    return self.sshPublicKeyPath

  def getSshCmd(self) :
    """Get an ssh cmd string using the user's ssh key and ssh-agent."""

    return ""

  def getScpCmd(self) :
    """Get an scph cmd string using the user's ssh key and ssh-agent."""

    return ""

  def getRsyncCmd(self) :
    """Get an rsync cmd string using the user's ssh key and ssh-agent."""

    return ""
