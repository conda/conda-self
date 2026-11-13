# Quick start

In this tutorial, you will install a package in a working environment and then
maintain conda separately. By the end, you will know which commands affect your
work and which affect conda itself.

## Before you start

You need conda 26.1.1 or later in a terminal with conda's shell integration
enabled. If this is your first time using conda, follow its
[getting-started guide](inv:conda:std:doc#user-guide/getting-started) first.

Install conda-self in base using a configured channel that provides it:

```bash
conda install -n base conda-self
```

This tutorial uses a new environment named `self-demo`. If you already have
one with that name, choose an unused name and substitute it throughout.
You do not need to protect base or move any existing packages for this tutorial.

![Install NumPy in self-demo and maintain conda without changing the working environment](../demos/quickstart.gif)

{download}`Watch the MP4 recording <../demos/quickstart.mp4>`.

## Create a place for your work

Create an environment containing Python:

```bash
conda create --name self-demo python
```

Conda shows the packages it will install. Review the list and accept the
confirmation prompt. Then activate your new environment:

```bash
conda activate self-demo
```

Your prompt normally shows `(self-demo)`. Commands such as `python` now use
this environment rather than base.

## Install a project package

Use an ordinary conda command to install NumPy:

```bash
conda install numpy
```

Accept the proposed installation, then check that Python can import it:

```bash
python -c "import numpy; print(numpy.__version__)"
```

You should see a NumPy version number. Its exact value depends on the packages
available from your configured channels.

## Maintain conda itself

Leave `self-demo` active. Preview an update to conda:

```bash
conda self update --dry-run
```

This targets conda in base and may update its dependencies. It does not update
the packages in `self-demo`. Review the proposed changes, then run the update:

```bash
conda self update
```

Accept the confirmation if conda proposes changes. A message saying the
requested packages are already installed is also a successful result.

## Check your working environment

Run the same Python command again:

```bash
python -c "import numpy; print(numpy.__version__)"
```

NumPy still imports in `self-demo`, with the same version as before. You used
`conda install` for your working environment and `conda self update` for the
conda installation. You can continue using `self-demo` for experiments.

To learn about extending conda, follow {doc}`tutorials/managing-plugins`.
If you previously worked in base, read {doc}`tutorials/protecting-base` before
enabling protection. For more context, see {doc}`motivation`.
