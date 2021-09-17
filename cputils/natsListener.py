"""
A NATS listener and checker.
"""

import asyncio

def filterSubjects(subjectList, filterUsing='equals') :
  """Return a natsListener filter which will filter NATS messages on the
  subjects by returning True on any one of three conditions:

    - `equals`: return True if the message subject is equal to any subject
    in the subjectList.

    - `startsWith`: return True if the message subject starts with any
    subject in the subjectList.

   """

  if not subjectList :
    return None

  if filterUsing == 'equals' :
    def filterMessage(theSubject, theMessage) :
      return theSubject in subjectList
    return filterMessage

  if filterUsing == 'startsWith' :
    def filterMessage(theSubject, theMessage) :
      for aSubject in subjectList :
        if theSubject.startswith(aSubject) :
          return True
      return False
    return filterMessage

  return None

def messageCollector(collectedMessages) :
  """Return a natsListener message collector to collect NATS messages into
  the `collectedMessages` dict provided.

  NATS messages stored in an list associated with each distinct message
  subject. """

  if collectedMessages is None :
    return None

  if type(collectedMessages) != dict :
    return None

  def collectMessage(aSubject, theSubject, theMessage) :
    """Collect all messages from all subjects for later analysis.

    Messages are collected into a list for each distinct theSubject.
    """

    if theSubject not in collectedMessages :
      collectedMessages[theSubject] = []
    theSubjectMessages = collectedMessages[theSubject]

    theSubjectMessages.append(theMessage)

  return collectMessage

def hasMessage(messageCollection, aSubject=None, aMessage=None) :
  """Return True if the messageCollection provided has a message
  associated with the theSubject provided. """

  if aSubject is None :
    return False

  if aSubject not in messageCollection :
    return False

  if aMessage is None :
    return True

  return aMessage in messageCollection[aSubject]

def getMessages(messageCollection, aSubject=None) :
  """Return a list of all messages with a given subject."""

  theMessages = []

  if aSubject is None :
    for aSubjectKey, aSubjectValue in messageCollection.items() :
      for aMessage in aSubjectValue :
        theMessages.append({
          'aSubject'   : aSubjectKey,
          'aMessage'   : aMessage
        })
    return theMessages

  if aSubject not in messageCollection :
    return theMessages

  for aMessage in messageCollection[aSubject] :
    theMessages.append({
      'aSubject'   : aSubject,
      'aMessage'   : aMessage
    })
  return theMessages

def numMessages(messageCollection, aSubject=None) :
  """Return the number of messages associated with a given subject."""

  return len(getMessages(messageCollection, aSubject))

async def natsListener(
  natsClient,
  aCollector=None,
  subjectToListenTo='>',
  aFilter=None
) :
  """Register a message collector and (potentially a) filter to listen to
  *all* NATS messages."""

  if aCollector :
    if aFilter :
      def filteredListener(aSubject, theSubject, theMessage) :
        if aFilter(theSubject, theMessage) :
          aCollector(aSubject, theSubject, theMessage)
      await natsClient.listenToSubject(subjectToListenTo, filteredListener)
    else :
      await natsClient.listenToSubject(subjectToListenTo, aCollector)
