# Understanding conda-self

## Conda and conda-self

Conda manages the software environments you use for coursework and projects.
Conda-self helps you maintain conda itself. The name `conda self` means
"conda managing itself."

You do not need conda-self to install Python or create an environment. If you
are new to conda, start with its
[getting-started guide](inv:conda:std:doc#user-guide/getting-started).

## Base and your working environments

Conda is installed in a special environment called `base`, together with the
packages it needs to run. Your project can have its own environment containing
Python and any packages your work requires, such as NumPy or pandas.

Keeping these environments separate lets you change your project's packages
without changing conda's dependencies. You can use conda while a project
environment is active. You do not have to return to base to manage another
environment or to run `conda self update`.

| Your goal | Command and target |
| --- | --- |
| Install a package for your work | `conda install numpy` in your active project environment |
| Update conda itself | `conda self update`, which targets the conda installation in base |
| Add an extension to conda | `conda self install conda-spawn`, which installs into base |

`conda self install` does not replace `conda install`. It is for extensions to
conda, not for the packages your Python code imports.

## What is a plugin?

A plugin adds capabilities to conda. For example, conda-spawn adds the
`conda spawn` command for opening a shell in an environment. Other plugins
provide solvers, authentication, or environment-file formats.

A plugin must be installed alongside conda to be discovered. Installing a
plugin in a project environment does not extend the conda executable in base.
This is why "never install anything in base" is incomplete advice: conda and
its extensions still need maintenance.

The {doc}`tutorials/managing-plugins` tutorial demonstrates an extension you
can use. Plugin authors can read conda's
[plugin development guide](inv:conda:std:doc#dev-guide/plugins/index).

## Why protect base?

Installing project packages in base can introduce dependencies that conflict
with conda's own requirements. A damaged conda installation can also be unable
to run the commands needed to repair it.

Base protection makes ordinary conda commands refuse to change base. Conda-self
provides explicit commands for the maintenance operations that still belong
there. This turns advice about keeping environments separate into a safeguard
against accidental changes.

Protection is optional. Conda-self's installation, update, and removal commands
also work without it. Protection is not a security mechanism and does not stop
every program, including pip or a file editor, from modifying base.

## If you already work in base

Adopting conda-self does not by itself move your packages or protect base.
Enabling protection is a separate, deliberate operation.

Protection clones base into an environment named `default`, reduces the conda
package set in base, and marks base as frozen. You can then use the cloned
environment for your existing work. Ordinary package installation in other
environments is unchanged.

There are two important effects to understand before proceeding:

- If an environment named `default` already exists, accepting the replacement
  prompt deletes and recreates it. Protection does not merge environments.
- Protection changes conda's `default_activation_env` setting to the clone's
  path. This replaces any previous value in your user configuration. Your
  current shell still needs explicit activation, and editors or notebooks may
  need their Python environment reselected.

The clone preserves packages, including external packages such as those
installed with pip. This is not a backup of your project files or a guarantee
that external paths used by editable installations move with the environment.
External packages may no longer work in the reset base environment.

Read {doc}`guides/protecting-base` for the procedure and its prerequisites.

## Recovery is a separate task

Conda-self can reset base using a snapshot or a selected set of packages. A
snapshot records conda packages, not the complete state of your machine.
Protection attempts to save a snapshot, but can continue without one if export
is unavailable.

An exact reset can downgrade packages and remove plugins not recorded in the
snapshot, including conda-self. It requires conda to still be runnable and the
required packages to be available. It is not a universal repair command.
See {doc}`guides/resetting-base` before choosing a reset mode.

For implementation choices and project history, see {doc}`features`.
