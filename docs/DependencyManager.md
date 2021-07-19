# ComputePods Utilities Dependency Manager

<!-- toc -->

The **DependencyManager** maintains a possibly cyclic graph of the
*current* build dependencies for a federation of ComputePods.

The dependency manager maintains a (small) collection of build goals, and
by sending out a succession of "how to build" messages, accumulates a
dependency graph sufficient to build these goals.

The "how to build" messages contain a list of currently known artefact
types as well as a small collection of goal artefact types.

In response one or more Chefs, respond with "can build from" messages
which contain one goal artefact type together with a list of required
input artefact types.

**Definitions**

  - **Dependency**: An artefact `A` is a dependency of artefact `B` if `A`
    is required to build `B`. The *dependency relation* answers the
    question: "What do I need to build this"?

  - **Dependant**: An artefact `A` is a dependant of artefact `B` if when
    artefact `B` is changed, artefact `A` must be rebuilt. The *dependant
    relation* answers the question: "If this is changed what needs to be
    rebuilt"?

Note that the *dependency relation* is the opposite of the *dependant
relation*.

We build the dependency graph from goals to available artefacts via the
*dependency relationship*. We build artefacts from changed artefacts to
goals via the *dependant relationship*. (See:
[`tup`](http://gittup.org/tup/)'s
[architecture](http://gittup.org/tup/build_system_rules_and_algorithms.pdf))

This means that the dependency graph must be implemented so that it is
easy to traverse the graph in either direction. The dependency graph will
be implemented as a Python dictionary which contains individual nodes each
of which have at least a `dependencies` and a `dependants` properties. The
`dependencies` and `dependant` properties are each lists of the respective
nodes. Following `tup`, nodes will represent both file artefacts as well
as Chef types.

# Dependency analysis

## Problem

While each ComputePod worker will have default knowledge of how to build
objects in its area of speciality, this will often not be enough to build a
large complex project which spans the domains of multiple workers.

**How do we supplement the "default" dependency knowledge?**

### Examples

For example, ConTeXt document collections have a definite suggested
structure using the [ConTeXt Project
structures](https://wiki.contextgarden.net/Project_structure).

Unfortunately, this "default" directory structure (and their associated
ConTeXt declarations) does not include information about what diSimplex
Code objects these ConTeXt documents might produce. The names of these
code objects might have no relationship with, for example, the names of
the containing ConTeXt documents. This means that, by default, the
ComputePod workers will have no obvious way to infer that the request to
build a given Code object, requires the typesetting of the associated
ConTeXt documents.

## Requirements

We need a simple text format in which to specify these *high-level*
dependencies. This format also needs to be readable by multiple
programming/scripting languages. This text format needs to support the
specification of *"simple"* rules for associating artefacts with
dependencies.

Generally generic and/or details of dynamically generated dependencies
*should* be located in the worker's associated ComputePod Chef plugins
(and not the "high-level" project descriptions).

## Solution

We will use a YAML format based upon the
[Sake](https://github.com/tonyfischetti/sake) format to describe the
dependencies in a *project*. This description should be sufficient to
start the dependency analysis phase. We expect the worker's ComputePod
Chefs to be able to fill in the fine dependency details as well as the
rules required to build each (micro) step. The project description file
will be located in the *top-level* of the project file directories.

Project descriptions *will* *not* contain Python or Lua (or any Turing
complete) code. They *may* contain wildcards describing other project
files (which could be additional (sub)project description files).

### Potential formats

- **Our own format** This would require a parser etc... ;-(

- **YAML** This is a nice format which is easily human readable, and which
  allows comments. There are Python, GoLang, and ANSI-C parsers, but
  unfortunately there is no *pure* Lua *parser* (see
  [lua-tinyyaml](https://github.com/peposso/lua-tinyyaml)). Generation of
  these high-level project description files *should* be fairly easy in
  most languages.

  The use of (standard) "wildcard" characters ('*', '%', etc) in YAML
  strings tends to confuse YAML parsers. Which means that users *must* put
  "rules" inside quoted strings.

- **JSON** This format is machine readable but can be rather wordy, and
  does not allow comments. There are parsers in Python, GoLang, ANSI-C and
  (pure) Lua (at least in ConTeXt's version).

- **Lua** Pure Lua source code could be used as a text format. It can be
  embedded in both ANSI-C, Python and GoLang. Unfortunately it is rather
  *over* powered (being Turing Complete).

- **Python** Pure Python source code could be used as a text format. It
  could only be used in ANSI-C(?) and Python. Again, it is rather *over*
  powered.

## Questions

1. What sorts of dependency rules are used in build systems?

  - see: [Sake](http://tonyfischetti.github.io/sake/) for a YAML example

  - see: [tup](http://gittup.org/tup/) for an example of a simple
    non-standard format.

  - see: [Rake](https://ruby.github.io/rake/doc/rakefile_rdoc.html) for an
    example of a Ruby DSL (which is ultimately Turing complete).

2. How should we include more complex dependency rules? Should/could we
   use Python or Lua code? (Is this not too overpowered and a security
   risk?)

   **A**: We will NOT include any Turing complete "code". Any such code
   must be contained in the worker's Chef plugins (as python code), which
   is "installed" at pod build time (rather than pod runtime).

