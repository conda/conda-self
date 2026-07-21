# CLI reference

All commands are available as `conda self <cmd>`.

---

## self install

Add conda plugins to the base environment.

```
conda self install <specs>... [--force-reinstall] [--dry-run] [--yes] [--json] [--quiet]
```

`specs`
: One or more package names to install. Inline channel specs
  (`channel::pkg`) are rejected -- use [conda config](inv:conda:std:doc#commands/config) instead.

`--force-reinstall`
: Reinstall the plugin even if it is already installed.

`--dry-run`
: Show what would be installed without making changes.

`--yes`
: Skip confirmation prompts.

`--json`
: Output in JSON format.

`--quiet`
: Suppress non-essential output.

```bash
# Install a plugin
conda self install conda-index

# Force reinstall
conda self install --force-reinstall conda-index
```

After installation, conda-self validates that the package registers
a `conda` entry point. If it does not, the package is automatically
uninstalled and a `SpecsAreNotPlugins` error is raised.

---

## self remove

Remove conda plugins from the base environment.

```
conda self remove <specs>... [--dry-run] [--yes] [--json] [--quiet]
```

`specs`
: One or more package names to remove.

`--dry-run`
: Show what would be removed without making changes.

`--yes`
: Skip confirmation prompts.

Essential packages (conda, its core dependencies, and anything in
`self_permanent_packages`) cannot be removed. Attempting to do so
raises a `SpecsCanNotBeRemoved` error.

```bash
conda self remove conda-index
```

---

## self update

Update the conda installation or its plugins.

```
conda self update [--plugin <name> | --all] [--force-reinstall] [--dry-run] [--yes] [--json] [--quiet]
```

`--plugin`
: Update one installed conda plugin together with conda.

`--all`
: Update conda, all installed conda plugins, and dependencies.

`--force-reinstall`
: Force reinstall of all packages.

`--dry-run`
: Show what would change without making modifications.

`--yes`
: Skip confirmation prompts.

```bash
# Update the installation
conda self update

# Update one plugin
conda self update --plugin conda-index

# Update all plugins and dependencies
conda self update --all

# Force reinstall
conda self update --force-reinstall
```

A distribution-provided [installer adapter](installer-adapters) may handle a
bare `conda self update` when it owns the launcher. Without one, the command
updates the `conda` package in base as before. Explicit `--plugin` and `--all`
operations always use conda package management.

---

## self uninstall

Uninstall the conda installation through its installer or package manager.

```
conda self uninstall [--dry-run] [--yes] [--json] [--quiet]
```

An [installer adapter](installer-adapters) handles confirmation, cleanup, and
package-manager instructions. If no adapter supports uninstalling the root
prefix, the command exits without removing it.

---

## self reset

Reset the base environment to essential packages only.

```
conda self reset [--snapshot <type>] [--dry-run] [--yes] [--json] [--quiet]
```

`--snapshot`
: Which snapshot to reset to. Options:

  `current`
  : Remove all packages except conda, its plugins, and their
    dependencies.

  `installer`
  : Reset to the snapshot saved by the installer
    (`conda-meta/installer-state.explicit.txt`).

  `base-protection`
  : Reset to the snapshot saved by `conda doctor --fix`
    (`conda-meta/base-protection-state.explicit.txt`).

  If not specified, conda-self tries `base-protection` first, then
  `installer`, and falls back to `current`.

```bash
# Auto-detect best snapshot
conda self reset

# Reset to installer state
conda self reset --snapshot installer

# Reset to base-protection snapshot
conda self reset --snapshot base-protection

# Strip to current essentials
conda self reset --snapshot current
```

---

## conda doctor base-protection

Check and fix the base environment protection status. This is a
health check registered via conda's `conda_health_checks`
[plugin hook](inv:conda:std:doc#dev-guide/plugins/index). See also
[conda doctor](inv:conda:std:doc#commands/doctor) for how health checks work.

```
conda doctor base-protection [--fix] [--dry-run]
```

`--fix`
: Enable base protection. This:
  1. Clones the current base environment to `default`
  2. Saves a snapshot to `conda-meta/base-protection-state.explicit.txt`
  3. Resets base to essential packages
  4. Freezes base via `PREFIX_FROZEN_FILE`

Without `--fix`, reports whether base is currently protected.

```bash
# Check status
conda doctor base-protection

# Enable protection
conda doctor base-protection --fix

# See all available health checks
conda doctor --list
```

:::{warning}
If your base environment contains non-conda packages (e.g. pip-installed),
`--fix` will warn you before proceeding. These packages are preserved
in the cloned `default` environment but will become non-functional
in the reset base.
:::
