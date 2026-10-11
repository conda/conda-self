# Configuration

## conda settings

conda-self registers one custom setting via conda's `conda_settings`
[plugin hook](inv:conda:std:doc#dev-guide/plugins/index).

### plugins.self_permanent_packages

A list of package names protected from `conda self remove` and retained by the
`current` and `installer-updated` reset modes. Exact snapshot modes restore the
packages recorded in the snapshot and may remove configured permanent packages
that are absent from it.

Configure in [`.condarc`](inv:conda:std:doc#configuration):

```yaml
plugins:
  self_permanent_packages:
    - pip
    - setuptools
```

The `current` and `installer-updated` reset modes retain these packages and
their dependencies alongside conda, conda-self, installed
[conda plugins](inv:conda:std:doc#dev-guide/plugins/index), and their
dependencies. `conda self remove` refuses to remove a configured permanent
package or one of its dependencies unless `--force` is passed.

## Snapshot files

Snapshots are stored in the base environment's `conda-meta/` directory and use
conda's explicit format. Each file contains an `@EXPLICIT` marker followed by
complete package URLs.

| File | Created by | Purpose |
|------|-----------|---------|
| `base-protection-state.explicit.txt` | `conda doctor -n base base-protection --fix` | Pre-protection state when export succeeds |
| `initial-state.explicit.txt` | Installer (e.g. Miniforge) | Original installer state |

The exact reset modes, `base-protection` and `installer-exact`, use these files
to restore the recorded conda package set without running the solver. They
reuse an installed package only when its package URL and any recorded checksum
match the corresponding values in the snapshot. `installer-updated`
uses `initial-state.explicit.txt` only to select the installed conda package
names to retain. It does not update packages or install missing packages.

Snapshot export during protection is best-effort. If export fails, protection
can complete without creating `base-protection-state.explicit.txt`. Snapshots
do not record the complete state of pip-installed packages or external files.

## Default activation environment

`default_activation_env` is a conda setting, not a conda-self plugin setting.
Successful base protection writes the cloned `default` environment's path to
this setting in the user configuration, replacing any previous value and
preserving unrelated settings.

Bare `conda activate` uses the configured default activation target. Automatic
activation when a new shell starts is separately controlled by conda's
`auto_activate` setting. Changing the target does not switch the current shell
or update an editor's selected interpreter. Activate `default` explicitly to
continue working there after protection.

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_ENV_NAME` | `"default"` | Name of the environment created when cloning base |
| `RESET_FILE_BASE_PROTECTION` | `"base-protection-state.explicit.txt"` | Snapshot filename for base protection |
| `RESET_FILE_INSTALLER` | `"initial-state.explicit.txt"` | Snapshot filename from installer |
| `SELF_PERMANENT_PACKAGES_SETTING` | `"self_permanent_packages"` | Name of the condarc setting |

## Environment variables

conda-self does not define its own environment variables. It respects
all standard conda environment variables, including:

`CONDA_CHANNELS`
: Override configured channels for plugin installation.

`CONDA_DRY_RUN`
: Enable dry-run mode for all operations.

`CONDA_JSON`
: Enable JSON output for all operations.
