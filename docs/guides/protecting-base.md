# Protect your base environment

Use this guide when you want to keep conda separate from packages you have
installed for your work. Protection moves your working setup into a clone and
makes ordinary conda commands refuse changes to base.

This is not required to create environments or start using Python. For the
reasoning behind it, see {doc}`../motivation`.

## Check before making changes

You need conda 26.1.1 or later and conda-self installed in base. Check that the
command is available, list existing environments, and check protection:

```bash
conda self --version
conda env list
conda doctor -n base base-protection
```

If base is already protected, you do not need to run the fix again.

:::{warning}
Protection uses an environment named `default` for the clone. If that
environment already exists, accepting "Remove and recreate?" deletes it and
replaces it with a clone of base. It does not merge the two environments.

Cancel if you need to keep the existing destination. Preserve it under another
name first, following conda's
[environment-management guide](inv:conda:std:doc#user-guide/tasks/manage-environments).
An existing directory that is not a conda environment produces a separate
confirmation before cloning. Inspect and preserve its contents before proceeding.
:::

Before confirmation, understand what protection changes:

1. It tries to export a recovery snapshot of base in conda's explicit format.
2. It clones base to `default`, including external packages such as those
   installed with pip.
3. It removes unretained conda packages from base. It retains conda, conda-self,
   configured permanent packages, their dependencies, and installed conda
   packages named in an available installer snapshot.
4. It marks base as frozen.
5. It sets `default_activation_env` in your user configuration to the clone's
   path, replacing any previous value while preserving unrelated settings.

Keep your usual backups of project files and external data. Cloning an
environment does not relocate external source directories used by editable
installations or back up everything on your machine. External packages may
no longer work in the reset base environment.

## Enable protection

Run the fix and review its proposed changes before accepting confirmation:

```bash
conda doctor -n base base-protection --fix
```

The recording starts with a disposable Miniforge base containing conda-self
and NumPy. NumPy represents an existing working package, not a prerequisite
you should install in base before protection.

![Protect base, activate the clone, and verify NumPy still works](../../demos/base-protection.gif)

{download}`Watch the MP4 recording <../../demos/base-protection.mp4>`.

## Continue your work

Activate the cloned environment in your current shell:

```bash
conda activate default
```

Check a package you used before protection. For the NumPy example:

```bash
python -c "import numpy; print(numpy.__version__)"
```

The stored default activation target now points to this clone. Whether a new
shell automatically activates it also depends on conda's `auto_activate`
setting. The configuration change does not switch an already-running shell
or change an editor or notebook's selected Python interpreter. Select the
cloned environment there explicitly if necessary.

## Verify protection

```bash
conda doctor -n base base-protection
```

The health check should report that base is protected. Ordinary conda install,
update, and remove commands targeting base now fail with a frozen-environment
error. That is the intended safeguard.

## Install packages after protection

For working packages, activate `default` or another project environment and
use ordinary conda commands:

```bash
conda activate default
conda install numpy
```

Use `conda self update` to maintain conda itself and `conda self install` for
conda plugins. See {doc}`../tutorials/managing-plugins` for a worked example.
Do not use protection overrides as your normal way to install project packages.
Deliberate bypasses and unprotection are documented in
{ref}`overriding-base-protection`.

## Check recovery availability

When export succeeds, the pre-protection conda package snapshot is saved as
`conda-meta/base-protection-state.explicit.txt` in base. Protection can continue
without it if base cannot be exported in explicit format.

If export was skipped, an exact `base-protection` reset is unavailable.
Automatic reset then selects `installer-updated` if an installer snapshot
exists, or `current` otherwise. Neither fallback recreates the exact
pre-protection state. See {doc}`resetting-base` before attempting recovery.
