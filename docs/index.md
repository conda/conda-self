# conda-self

Maintain conda itself, separately from the Python and packages you use for
your work.

Conda-self provides commands for updating conda and managing its extensions,
called plugins. It also helps protect the `base` environment where conda is
installed from accidental changes.

You do not need conda-self to create an environment or start using Python.
If you are new to conda, begin with its
[getting-started guide](inv:conda:std:doc#user-guide/getting-started).

## Install

Use conda 26.1.1 or later and a configured channel providing conda-self:

```bash
conda install -n base conda-self
```

Installation does not automatically protect base or move packages. If you
already use base for your work, read {doc}`tutorials/protecting-base` before
enabling protection.

## Project packages and conda maintenance

Use regular conda commands to install Python and packages in a working
environment. Use `conda self` to maintain conda and its plugins in base.
`conda self install` is not a replacement for `conda install`.

![Create a working environment, use NumPy, and update conda separately](../demos/quickstart.gif)

{download}`Watch the MP4 recording <../demos/quickstart.mp4>` or follow the
copyable commands in the {doc}`quickstart` tutorial.

## Find your next step

::::::{grid} 1 1 2 2
:gutter: 3

:::::{grid-item-card} Tutorials
:link: tutorials/index
:link-type: doc

Learn to maintain conda separately from your work, then try a conda plugin.
:::::

:::::{grid-item-card} How-to guides
:link: tutorials/protecting-base
:link-type: doc

Protect an existing base environment and continue using your packages.
:::::

:::::{grid-item-card} Reference
:link: reference/cli
:link-type: doc

Look up command options, exact behavior, settings, and limitations.
:::::

:::::{grid-item-card} Explanation
:link: motivation
:link-type: doc

Understand base, working environments, plugins, and the reasons for protection.
:::::

::::::

For other maintenance tasks, see {doc}`guides/custom-channels` and
{doc}`guides/resetting-base`. These are not prerequisites for getting started.

```{toctree}
:hidden:
:caption: Tutorials

tutorials/index
```

```{toctree}
:hidden:
:caption: How-to guides

guides/resetting-base
guides/custom-channels
```

```{toctree}
:hidden:
:caption: Reference

reference/cli
configuration
```

```{toctree}
:hidden:
:caption: Explanation

motivation
features
```

```{toctree}
:hidden:
:caption: Project

changelog
```
