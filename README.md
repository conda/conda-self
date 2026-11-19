# conda-self

Commands to manage your `base` environment safely.

## `conda self`

Manage conda and its plugins in the base environment.

```
$ conda self
usage: conda self [-V] [-h] {install,remove,reset,update} ...

Manage conda and its plugins in the base environment.

options:
  -V, --version         Show the 'conda-self' version number and exit.
  -h, --help            Show this help message and exit.

subcommands:
  {install,remove,reset,update}
    install             Install conda plugins in base (pending deprecation).
                        Use conda plugins install --name base with conda 26.11
                        or later.
    remove              Remove conda plugins from the base environment.
    reset               Reset the base environment.
    update              Update conda, one conda plugin, or all packages in the
                        base environment.
```

### Installing plugins

With conda 26.11.0 or later, install plugins directly into base.

```bash
conda plugins install --name base conda-index
```

If you or your installer froze base, add `--override-frozen` for that installation.
On older conda versions, use `conda self install conda-index`.

### Custom channels

To use a custom channel for both plugin installation and later updates, add
it to your configuration before installing the plugin.

```
conda config --add channels my-channel -n base
conda plugins install --name base my-plugin
```

The older `conda self install` command rejects channel-qualified package
specs such as `conda-forge::my-plugin`.

## Base Environment Protection

To check if your base environment is protected, run:

```
conda doctor -n base base-protection
```

To protect your base environment, run:

```
conda doctor -n base base-protection --fix
```

This will:

1. Try to save a snapshot of base in conda's explicit format
2. Clone your current base environment to a new "default" environment
3. Remove conda packages other than conda, conda-self, configured permanent
   packages, their dependencies, and installed conda packages named in an
   available installer snapshot
4. Mark the base environment as frozen so conda refuses modifications by
   default

To see all available health checks, run:

```
conda doctor --list
```

### Unprotecting base

To remove protection entirely, delete the `conda-meta/frozen` environment
marker file:

```
rm "$(conda info --base)/conda-meta/frozen"
```

To bypass protection for a single command, pass `--override-frozen`. To disable
frozen-environment checks through configuration, set
`CONDA_PROTECT_FROZEN_ENVS=false` or add `protect_frozen_envs: false` to your
`.condarc`.

## Configuration

### Permanent packages

The `current` and `installer-updated` reset modes retain `conda`, `conda-self`,
installed conda plugins, configured permanent packages, and their dependencies.
To configure additional permanent packages, add them to the
`plugins.self_permanent_packages` setting in your `.condarc`:

```yaml
plugins:
  self_permanent_packages:
    - anaconda-anon-usage
```

Or use `conda config`:

```bash
conda config --add plugins.self_permanent_packages anaconda-anon-usage
```

## Installation

1. `conda install -n base conda-self`
2. `conda self --help`

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md)
