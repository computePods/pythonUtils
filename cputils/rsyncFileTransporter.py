# The ComputePods Rsync over SSH file transporter component

from aiofiles.os import wrap
import aiofiles
import asyncio
import datetime
import os
import yaml

from cputils.yamlLoader import mergeYamlData

async def runCmdNoUser(cmd, addToEnv=None) :
  """Runs a command (with no user interaction) and returns the return
  code, stdout, and stderr as a tuple. Based upon the Python asyncio
  subprocesses documentation. """

  if addToEnv is not None :
    for aKey, aValue in addToEnv.items() :
      os.environ[aKey] = aValue

  proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
  )

  stdout, stderr = await proc.communicate()

  if stdout: stdout = stdout.decode()
  if stderr: stderr = stderr.decode()

  return (proc.returncode, stdout, stderr)

async def runCmdWithUser(cmd, addToEnv=None) :
  """Runs a command allowing the users to interact with the command and
  then returns the return code. Based upon the Python asyncio subprocesses
  documentation. """

  if addToEnv is not None :
    for aKey, aValue in addToEnv.items() :
      os.environ[aKey] = aValue

  proc = await asyncio.create_subprocess_exec(
    *cmd, stdout=None, stderr=None
  )

  await proc.wait()

  return proc.returncode

defaultSshConfig = {
  'addCmd'         : '/usr/bin/ssh-add',
  'agentCmd'       : '/usr/bin/ssh-agent',
  'keyGenCmd'      : '/usr/bin/ssh-keygen',
  'killCmd'        : '/usr/bin/kill',
  'cprsyncCtlCmd'  : '~/.local/bin/cprsyncctl',
  'rsyncCmd'       : '/usr/bin/rsync',
  'sshCmd'         : '/usr/bin/ssh',
  'dir'            : '~/.ssh',
  'authorizedKeys' : 'authorized_keys',
}

fileExists = wrap(os.path.exists)
makeDirs   = wrap(os.makedirs)
removeFile = wrap(os.remove)

class RsyncFileTransporter :
  """The ComputePods Rsync over SSH file transporter component.

  To ensure secure and authenticated communication, this transporter
  component also includes SSH key management to manage the ssh keys
  required for the use of rsync on the user's behalf. This ssh key manager
  uses a combination of `ssh-agent`, `ssh-add`, and direct access to a
  given `authorized_keys` file. """

  def __init__(self, config) :
    """Setup the required configuration."""

    self.verbosity = 0
    if 'config' in config and 'verbosity' in config['config'] :
      self.verbosity = config['config']['verbosity']

    federationName = 'computePods'
    if 'federationName' in config :
      federationName = config['federationName']

    self.computePodsRsyncTag = f'{federationName}-rsync'

    timeNow = datetime.datetime.now().strftime("%Y.%m.%d-%H.%M.%S")
    self.keyComment = f'{timeNow}-{federationName}-rsync'

    sshConfig = { }
    if 'ssh' in config : sshConfig = config['ssh']
    mergeYamlData(defaultSshConfig, sshConfig, '.')
    sshConfig = defaultSshConfig

    self.sshAddCmd     = sshConfig['addCmd']
    self.sshAgentCmd   = sshConfig['agentCmd']
    self.sshKeyGenCmd  = sshConfig['keyGenCmd']
    self.killCmd       = sshConfig['killCmd']
    self.sshCmd        = sshConfig['sshCmd']
    self.rsyncCmd      = sshConfig['rsyncCmd']

    self.cprsyncCtlCmd = os.path.abspath(
      os.path.expanduser(sshConfig['cprsyncCtlCmd'])
    )
    if 'cprsyncCtlDir' in sshConfig :
      self.cprsyncCtlCmd = self.cprsyncCtlCmd + ' -d ' + sshConfig['cprsyncCtlDir']

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

    self.sshAgentPid = self.sshAgentSocket.removesuffix('.socket')+'.pid'

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

  async def keyExists(self) :
    """Return True if the ssh key for this ComputePod already exists."""

    return await fileExists(self.sshPrivateKeyPath)

  async def createdKey(self) :
    """Uses ssh-keygen to create a new key for a user. """

    if await self.keyExists() : return True

    await makeDirs(
      os.path.dirname(self.sshPrivateKeyPath),
      mode=0o700, exist_ok=True
    )

    retCode = await runCmdWithUser([
      self.sshKeyGenCmd,
      '-b', '2048',
      '-t', 'rsa',
      '-C', self.keyComment,
      '-f', self.sshPrivateKeyPath
    ])

    return retCode == 0

  ######################################################################
  # work with an ssh-agent

  async def isSshAgentRunning(self) :
    """Check to see if the computePods ssh-agent is running. """

    retCode, stdout, stderr = await runCmdNoUser([
      self.sshAddCmd,
      '-q'
    ],
    addToEnv = {
      'SSH_AUTH_SOCK' : self.sshAgentSocket
    })

    return retCode == 1 and not stderr

  async def startedAgent(self) :
    """Setup and start an ssh-agent dedicated for the use of
    ComputePods."""

    if await self.isSshAgentRunning() : return True

    retCode, cmdStdout, _ = await runCmdNoUser([
      self.sshAgentCmd,
      '-a', self.sshAgentSocket,
      '-c'
    ])

    lines = cmdStdout.splitlines()
    if len(lines) < 1 :
      print("Could not (re)start the ssh-agent")
      print("Try stopping it using cpcli stopsshagent")
      return False

    agentPid = lines.pop().split().pop().rstrip(';')
    async with aiofiles.open(self.sshAgentPid, mode='w') as f :
      await f.write(agentPid)

    return retCode == 0

  async def stopAgent(self) :
    """Find and stop any existing ssh-agents for use by this
    computePod."""

    pid = 0
    if await fileExists(self.sshAgentPid) :
      async with aiofiles.open(self.sshAgentPid, mode='r') as f :
        pid = int(await f.read())
      await removeFile(self.sshAgentPid)

    if 0 < pid :
      await runCmdNoUser([self.killCmd, '-9', str(pid)])

    if await fileExists(self.sshAgentSocket) :
      await removeFile(self.sshAgentSocket)

  async def isSshKeyLoaded(self) :
    """Check that the user's ComputePod key has been loaded. """

    retCode, stdout, stderr = await runCmdNoUser([
      self.sshAddCmd,
      '-L'
    ],
    addToEnv = {
      'SSH_AUTH_SOCK' : self.sshAgentSocket
    })

    if retCode == 0 and stdout.endswith(self.computePodsRsyncTag+'\n') :
      return True

    return False

  async def loadedKey(self) :
    """Loads a given ssh key into the ComputePods ssh-agent."""

    if not await self.isSshAgentRunning() :
      print("No ComputePods ssh-agent running")
      print("Try starting one using: cpcli startsshagent")
      return False

    if await self.isSshKeyLoaded() : return True

    retCode = await runCmdWithUser([
      self.sshAddCmd,
      self.sshPrivateKeyPath
    ])

    return retCode == 0

  async def unloadedKey(self) :
    """Unloads a given ssh key from the ComputePods ssh-agent."""

    if not self.isSshAgentRunning() : return False

    retCode, _, _ = await runCmdNoUser([
      self.sshAddCmd,
      '-D'
    ],
    addToEnv = {
      'SSH_AUTH_SOCK' : self.sshAgentSocket
    })

    return retCode == 0

  ######################################################################
  # manipulation of a user's authorized_keys file

  async def enableKey(self, addKey=True) :
    """Add a specific key to a user's authorized_keys file."""

    # Get the current authorized_keys file contents (as an array of lines)
    #
    authKeys = None
    try :
      async with aiofiles.open(self.authKeyPath, mode='r') as authKeyFile :
        authKeys = await authKeyFile.readlines()
    except Exception as err :
      print(repr(err))

    if authKeys is None :
      print(f"Could not open the ssh authorized_keys file ({self.authKeyPath})")
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
      publicKey = ""
      try :
        async with aiofiles.open(self.sshPublicKeyPath, mode='r') as publicKeyFile :
          publicKey = await publicKeyFile.read()
      except Exception as err:
        print(repr(err))

      if publicKey :
        authKeyLine = f"command=\"{self.cprsyncCtlCmd}\" {publicKey}"
        newAuthKeys.append(authKeyLine)

    if newAuthKeys :
      # Backup the existing authorized_keys file
      #
      timeNow = datetime.datetime.now().strftime("%Y.%m.%d-%H.%M.%S")
      await aiofiles.os.rename(
        self.authKeyPath, self.authKeyPath+'_cpBackup_'+timeNow
      )

      # Save the new authorized_keys file
      #
      async with aiofiles.open(self.authKeyPath, mode="w") as authKeyFile :
        await authKeyFile.write("\n".join(newAuthKeys))

      return True

  async def disableKey(self) :
    """Remove a specific key from a user's authorized_keys file."""

    return await self.enableKey(addKey=False)

  ######################################################################
  # rsync files

  async def rsyncedFiles(self, fromPath, toPath) :
    """Rsync files from `fromPath` to `toPath`"""

    if not await self.isSshKeyLoaded() :
      return False

    if fromPath.find(':') < 0 :
      fromPath = os.path.abspath(
        os.path.expanduser(fromPath)
      )

    if toPath.find(':') < 0 :
      toPath = os.path.abspath(
        os.path.expanduser(toPath)
      )

    retCode, stdout, stderr = await runCmdNoUser([
      self.rsyncCmd,
      '-av',
      fromPath,
      toPath
    ],
    addToEnv = {
      'SSH_AUTH_SOCK' : self.sshAgentSocket,
      'RSYNC_RSH'     : self.sshCmd + ' -v ' \
        + ' -F /dev/null ' \
        + ' -i ' + self.sshPrivateKeyPath
    })

    if 0 < self.verbosity :
      print("------------------------------------------------------------")
      print(retCode)
      print("------------------------------------------------------------")
      print(stdout)
      print("------------------------------------------------------------")
      print(stderr)
      print("------------------------------------------------------------")

    return retCode == 0
