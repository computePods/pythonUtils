# ComputePods Utilities

<!-- toc -->

## Problem

### Core capabilities

The core of a functioning ComputePod (and so of any federation of
ComputePods) is an information flow between the various specialised Chefs,
the MajorDomo, as well as the user's inotify2nats and either the command
line cpCtrl or browser MajorDomoUI tools.

The **MajorDomo** is responsible for maintaining a model of the
dependencies between artefacts, and determining the order in which these
artefacts can be (re)built. Unlike a typical Make tool, the MajorDomo
*must* be able to rebuild projects with circular dependencies.

The various specialised **Chefs** are each responsible for declaring
dependencies between particular types of artefacts, as well as
understanding how to actually (re)build artefacts.

The user's **inotify2nats** tool is responsible for notifying a federation
of ComputePods of changes to primary artefacts being made by a user in the
file systems *outside* of any ComputePod in the federation.

Finally, the user can use either the **cpCtrl** command line tool or the
browser based **MajorDomoUI** to request that a particular artefact be
(re)built.

### Communication back-planes

Each of these responsibilities represent a core capability which will
"run" in one or more tool. Most importantly, to function, these capabilities
must communicate abilities and needs between themselves.

For any federation of ComputePods, there are three communication channels:

1. Between the user and the ComputePods, there is a **RESTful HTTP
   interface** (using JSON bodies).

2. Between components of one or more ComputePods, JSON messages will be
   sent using a **NATS publish/subscribe** system over various NATS
   subjects.

3. There are also the contents of **files in the file system** transferred
   between ComputePods via **sftp** (as needed).

## Goals

The ComputePods Python Utilities will capture these various core
capabilities in one place so that they can be tested and developed
together.

## Solution sketch

We develop the following Python modules to implement these capabilities:

- The **FSWatcher** monitors the relatively high frequency file system
  changes, and sends the more important changes to the MajorDomo via NATS
  messages.

- The **DependencyManager** maintains a possibly cyclic graph of the
  (build) dependencies, as well as tools to extract the current best build
  tree.

- The **ArtefactManager** monitors the current (build) state of the
  artefacts as they are spread across the ComputePods in a federation.

- The **RulesManager** is used by the ComputePod Chefs to listen for "how
  to build" messages and responde with "can build from" messages. The
  DependencyManager uses these "rules" to build its dependency graph.

We also develop a number of "simple" utilities to support these tools:

- The **restClient** provides a simple interface to send (and receive) the
  RESTful HTTP messages (and translate these message from the "HTTP"
  "wire" format into the corresponding JSON structures).

- The **natsClient** provides a simple interface to send and receive NATS
  messages (and translate these messages from the "wire" format into the
  corresponding JSON structures).

- The **sftpClient** provides a simple interface to move files between
  ComputePods.

## Thoughts

Computing SHA256 of files... Whoever computes these SHA256 needs to keep
an internal model of the file system so that they do not have to bother
shelling out to compute the SHA256 on an non-existent file. I guess we
could use aiofiles.os or aioshutil to check for the existence of a file
*before* we shell-out.

THE primary problem will be computing the SHA256 on a file which is being
continuously written to... How do we detect that? We can do this with a
debounce technique:
https://developpaper.com/throttle-function-and-debounce-function/ However
debouncing will introduce a latency... how much latency will ComputePods
tolerate?

When does the ComputePods want to know that a file has "changed"? Are
there files that need to be tracked closely? AND files for which it does
not matter? If there are... how do we signal that?

A ComputePod federation needs to know whether or not to (re)start a
"compilation" on a given file. That is whether or not a files dependants
need to be recomputed.

To do this, what information does a ComputePod need to know about a file?

  - open/closed/moved
  - (last) modification time
  - file size
  - sha256

do we care about

  - permissions
  - number of links
  - uid/gid

Is it good enough to only compute a SHA256 if the modification time has
changed but the size have not changed? This suggests that, really, a
ComputePod Chef should compute the SHA256 values and only just before
committing to a "re-compile"...

How often does a ComputePod federation want to be told about a "changed"
file? Given the relative length of time it takes for a ComputePod Chef to
"re-build" an artefact, it probably does not care about a slight latency,
AND would rather only be informed of a change if/when the file *stops*
changing. This suggests that FSWatcher needs to keep a *simple* model of
the file system *churn*, so that it can detect when the changes to a given
file *stop* via a *close* event.

However, *log files* DO want to be monitored *while* they are *changing*.
How do we inform FSWatcher of this?

Who can tell the difference between a "build artefact" and a "log file"? A
ComputePod Chef...

In a ComputePods federation, where are FSWatchers needed?

  - in the user's common area (needed since user's file changes are not
    visible *inside* a Pod)

  - in the MajorDomo?
  - in each Chef?