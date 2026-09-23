# Resetting the base environment

Use this guide to restore a recorded conda package set or remove packages not
needed by your chosen reset mode. This is a recovery or maintenance task, not
a prerequisite for using Python.

## Choose the outcome first

You need conda and `conda self` to still be runnable. Reset cannot repair an
installation whose conda executable no longer works. Snapshots describe conda
packages, not a complete backup of pip packages, project files, or external data.

| Your goal | Mode |
| --- | --- |
| Restore the conda packages recorded before protection | `base-protection` |
| Restore the original installer's exact conda package set | `installer-exact` |
| Keep installed versions of installer packages and conda tools | `installer-updated` |
| Keep conda, its plugins, and configured permanent packages | `current` |

:::{warning}
Exact modes can downgrade packages and remove plugins or permanent packages
that are absent from the snapshot. This can remove conda-self itself. Preview
the selected mode with `--dry-run`, and review the proposed changes before
accepting confirmation.
:::

## Automatically select a reset mode

```bash
conda self reset --dry-run
conda self reset
```

conda-self selects the first available mode in this order:

1. `base-protection` -- restore the exact snapshot saved by
   [conda doctor -n base base-protection --fix](inv:conda:std:doc#commands/doctor)
2. `installer-updated` -- retain installed conda packages whose names appear
   in the installer snapshot
3. `current` -- retain conda, conda-self, installed conda plugins, configured
   permanent packages, and their dependencies

Snapshot availability is based on whether its file exists. A failure while
applying the selected snapshot is reported instead of switching modes.
Automatic reset does not select `installer-exact`, which may downgrade
packages to the versions shipped by the installer.

## Select a reset mode

### Base-protection snapshot

Restore to the state captured by
`conda doctor -n base base-protection --fix`:

```bash
conda self reset --snapshot base-protection --dry-run
conda self reset --snapshot base-protection
```

This uses `conda-meta/base-protection-state.explicit.txt`.

### Exact installer snapshot

Restore to the original state from the installer (e.g. Miniforge):

```bash
conda self reset --snapshot installer-exact --dry-run
conda self reset --snapshot installer-exact
```

This uses `conda-meta/initial-state.explicit.txt` to restore exactly the conda
packages recorded by the installer and remove conda packages outside that
snapshot. This may downgrade packages that have since been updated.

Use this mode, or a suitable `base-protection` snapshot, when an
accidentally installed plugin must be removed. Not all installers provide
this file.

The recording starts with a disposable Miniforge installation that has its
original installer snapshot and an added conda-spawn plugin. It previews and
applies `installer-exact`, then inspects the remaining conda packages with
ordinary conda commands. It does not rely on conda-self remaining installed.

![Preview an exact installer reset and inspect base afterward](../../demos/reset.gif)

{download}`Watch the MP4 recording <../../demos/reset.mp4>`.

### Retain installed versions of installer packages

Retain currently installed conda packages whose names appear in the installer
snapshot:

```bash
conda self reset --snapshot installer-updated --dry-run
conda self reset --snapshot installer-updated
```

This mode does not update packages or install packages that are missing from
base. It also keeps conda, conda-self, installed conda plugins, packages
configured in `plugins.self_permanent_packages`, and their dependencies. It
does not remove an accidentally installed plugin and does not recreate the
exact installer environment.

### Current mode

Remove all conda packages except conda, conda-self, installed
[conda plugins](inv:conda:std:doc#dev-guide/plugins/index), packages configured
in `plugins.self_permanent_packages`, and their dependencies, without using a
snapshot file:

```bash
conda self reset --snapshot current --dry-run
conda self reset --snapshot current
```

## Migrate commands that use `installer`

`conda self reset --snapshot installer` reports a migration error before
asking for confirmation or changing the environment. Replace `installer` in
your commands and scripts with the mode that matches your intent:

- `installer-exact` restores the exact conda packages recorded in the installer
  snapshot and removes conda packages outside it. This may downgrade packages.
- `installer-updated` retains the currently installed versions of conda
  packages named in the installer snapshot, together with conda, conda-self,
  installed conda plugins, configured permanent packages, and their
  dependencies. It does not update packages or install missing packages.

## Packages required for an exact reset

For `installer-exact` and `base-protection`, conda-self first reuses a conda
package already installed in base when its package URL and any recorded
checksum match the corresponding values in the snapshot. For every other conda
package, conda makes it available in a package cache, downloading, verifying,
and extracting it as needed.

An unavailable snapshot URL does not prevent an exact reset when the matching
package is already installed and does not need to be reinstalled.

Each conda package that must be installed or reinstalled must be present in a
package cache or downloadable from its URL in the snapshot. This can include
noarch Python packages that must be relinked after a Python major or minor
version change. If conda cannot make a required package available in a package
cache, the exact reset stops before the target environment is changed. Packages
downloaded and extracted before the failure may remain in a package cache.

## After a reset

After resetting, your base environment contains the conda packages selected by
the reset mode. [conda list](inv:conda:std:doc#commands/list) shows what is left
in base. Inspect the result with ordinary conda commands:

```bash
conda list -n base
conda --version
```

If the snapshot did not include conda-self, reinstall it before using
`conda self` again. With conda 26.1.1 or later and a channel providing the
package, deliberate recovery of a still-frozen base can use:

```bash
conda install -n base --override-frozen conda-self
```

This is an explicit recovery bypass, not an instruction to install project
packages in base. See {ref}`overriding-base-protection` for its scope. If the
restored conda version predates conda-self's requirements, follow that
version's update instructions before reinstalling the plugin.

Your `default` environment (created during base protection) is
unaffected by resets.
