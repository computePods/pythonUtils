# Artefact Manager

The **ArtefactManager** maintains a model of the current build state of
the artefacts relevant to a federation of ComputePods.

The ArtefactManager's primary goal is to identify when an artefact has
changed and so all dependant artefacts need to be rebuilt.

Once the ArtefactManager detects a change, then it requests the
DependencyManager to rebuild any dependent artefacts required for any
current build goals.

The ArtefactManager must also model where in a federation, the most
recently up-to-date version of the artefact is located.


## Questions

- **How do we determine artefact types?**

  - By file extensions

  - By [ripgrep](https://github.com/BurntSushi/ripgrep) or
    [the-silver-searcher](https://github.com/ggreer/the_silver_searcher)
    probes

- **Where do we record these artefact types?**

  - In the rules YAML maintained by the rules manager

- **Who determines the type of an artefact?**

  - The Artefact Manager on CREATE events? (Since this will be run inside
    a ComputePod container so we know either ripgrep or
    the-silver-searcher will be installed)