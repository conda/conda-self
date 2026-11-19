# Managing plugins

This tutorial covers the complete lifecycle of
[conda plugins](inv:conda:std:doc#dev-guide/plugins/index) in a protected base
environment: installing, updating, and removing them.

## Prerequisites

- conda-self installed in base (`conda install -n base conda-self`)
- Base environment protected (see {doc}`protecting-base`)

## Install a plugin

With conda 26.11.0 or later, target base by name. If the installer protected
base or you protected it in the previous tutorial, add `--override-frozen`
for this installation.

```bash
conda plugins install --name base --override-frozen conda-index
```

Conda checks that the package provides a plugin before installing it. On
older conda versions, use `conda self install conda-index`.

:::{dropdown} Watch an installation with the older command
![Installing a plugin with conda self install](../../demos/install-plugin.gif)
:::

### Multiple plugins at once

```bash
conda plugins install --name base --override-frozen conda-index conda-spawn
```

## Update plugins

![Update demo](../../demos/update.gif)

Update conda:

```bash
conda self update
```

Update a specific plugin:

```bash
conda self update --plugin conda-index
```

Update all installed packages:

```bash
conda self update --all
```

Force reinstall:

```bash
conda self update --force-reinstall
```

## Remove a plugin

![Remove demo](../../demos/remove.gif)

```bash
conda self remove conda-index
```

Conda-self protects conda, conda-self, configured permanent packages, and their
dependencies from direct removal requests unless `--force` is passed. If you
try without `--force`, you will see a `PluginRemoveError`. Conda's own
transaction checks still apply with `--force`.

## Channel configuration

conda-self uses your configured channels. Use
[conda config](inv:conda:std:doc#commands/config) to add or change channels
before installing. To install plugins from a custom channel:

```bash
# Add the channel first
conda config --add channels my-channel -n base

# Then install
conda plugins install --name base --override-frozen my-plugin
```

Configuring the channel also makes it available to later updates. The older
`conda self install` command rejects channel-qualified package specs such as
`conda-forge::my-plugin`.

## Next steps

- {doc}`../guides/resetting-base` -- Restore base from a snapshot
- {doc}`../guides/custom-channels` -- Use custom channels for plugins
- {doc}`../reference/cli` -- Full CLI reference
