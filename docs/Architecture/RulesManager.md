# Rules Manager

The **RulesManager** maintains a collection of "rules" for a specific type
of ComputePod Chef which define both how to build an artefact as well as
what inputs are required for this build.

Since Python is essentially single threaded, all actual "builds" will take
place as distinct OS processes *managed* by Python asyncio subprocesses.

We will use a YAML format similar to
[Sake](http://tonyfischetti.github.io/sake)'s
["patterns"](http://tonyfischetti.github.io/sake/sake-doc.html#Using-Patterns)

The rules manager will listen for "how to build" messages and respond with
"can build from" messages for any artefact for which it has rules.

It will also supply build rules to a given ComputePod Chef when the Chef
determines that an artefact needs to be rebuilt.
