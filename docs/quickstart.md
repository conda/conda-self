# Quick start

This guide uses native conda to install a plugin and conda-self to protect
and maintain base.

## Prerequisites

- For native plugin installation, use conda 26.11.0 or later.
- For the base-protection check, update, remove, and reset steps, use
  conda-self installed in base with conda 26.1.1 or later.

## Protect your base environment

![Base protection demo](../demos/base-protection.gif)

If your installer already protected base, skip to {ref}`quickstart-install-plugin`.
Otherwise, check whether base is protected with
[conda doctor](inv:conda:std:doc#commands/doctor).

```bash
conda doctor -n base base-protection
```

For an unprotected base, enable protection with this command.

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

(quickstart-install-plugin)=
## Install a plugin

With conda 26.11.0 or later, install `conda-index` into the protected base
environment. Conda checks that the package provides a plugin before
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
