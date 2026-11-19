# Quick start

This guide walks you through protecting your base environment and
managing plugins with conda-self.

## Prerequisites

- conda 26.1.1 or later
- conda-self installed in base (`conda install -n base conda-self`)

## Protect your base environment

![Base protection demo](../demos/base-protection.gif)

Using [conda doctor](inv:conda:std:doc#commands/doctor), check whether base is
currently protected:

```bash
conda doctor -n base base-protection
```

If it is not, enable protection:

```bash
conda doctor -n base base-protection --fix
```

This does four things:

1. Tries to save a snapshot of base in conda's explicit format
2. Clones your current base environment to a new `default` environment
3. Removes conda packages other than conda, conda-self, configured permanent
   packages, their dependencies, and installed conda packages named in an
   available installer snapshot
4. Marks base as frozen so regular conda commands refuse to modify it unless
   `--override-frozen` is passed

## Install a plugin

With conda 26.11.0 or later, install `conda-index` into the base environment
you just protected. Conda checks that the package provides a plugin before
installing it.

```bash
conda plugins install --name base --override-frozen conda-index
```

On older conda versions, use `conda self install conda-index`.

## Update all installed packages

```bash
conda self update --all
```

This updates every installed package in the base environment.

## Remove a plugin

![Remove plugin demo](../demos/remove.gif)

```bash
conda self remove conda-index
```

Conda-self protects conda, conda-self, configured permanent packages, and their
dependencies from direct removal requests unless `--force` is passed. Conda's
own transaction checks still apply.

## Reset base

![Reset demo](../demos/reset.gif)

If something goes wrong, automatically select a reset mode:

```bash
conda self reset
```

## Next steps

- {doc}`tutorials/protecting-base` -- A deeper walkthrough of base
  protection and what happens under the hood
- {doc}`tutorials/managing-plugins` -- Install, update, and remove
  plugins with confidence
- {doc}`features` -- How base protection, snapshots, and plugin
  validation work
- {doc}`reference/cli` -- Every command and flag
