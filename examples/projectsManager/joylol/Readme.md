# JoyLoL example project

In this example we explore the build process to create the JoyLoL engine
from a ConTeXt document.

As part of this process we write out (in long hand) the [ninja
build](https://ninja-build.org/manual.html)
[file](https://ninja-build.org/manual.html#ref_ninja_file) which would be
required to build the JoyLoL engine.

We do this since all of the information in the resulting ninja file will
need to be "found" somewhere in the ComputePods build cycle. Determining
where and when this information becomes available will help us understand
how to architect the ComputePods build system.

We use the ninja file format to do this, because the ninja file format is
very simple, essentially either a `rule` or a `build` statement.

For this example we assume the following ConTeXt document layout:

```yaml

JoyLoL :
  joylol.tex
  memory :
    memory.tex
  parser :
    parser.tex
  base :
    strings.tex
    contexts.tex
    functions.tex
  interpreter :
    interpreter.tex

```

We will assume, for this example, that each of the JoyLoL sub-documents,
generates a similarly named ANSI-C code and header file.

For the sake of ensuring a "generic" example, we will also assume that the
`functions.tex` sub-document generates the following collection of code files:

```yaml
- cFunction.c
- cFunction.h
- luaFunction.c
- luaFunction.j
- joylolFunction.c
- joylolFunction.h
```

Again for the sake of ensuring a "generic" example, we will assume that
the "base" object code *must* be linked *before* the interpreter code.
