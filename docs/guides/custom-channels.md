# Using custom channels

How to install plugins from custom or private channels.

## Select channels for one installation

Pass `--channel` to install a plugin from an additional channel without
changing your configuration:

```bash
conda self install --channel https://packages.example.org/team my-plugin
```

Repeat `--channel` to supply multiple channels. Add `--override-channels` to
search only those channels, for example when setting up an installation that
has no channel configuration yet:

```bash
conda self install --override-channels --channel conda-forge conda-index
```

These options apply to this package transaction only. They do not change
`.condarc`, runtime update sources, or the channels used by `conda self update`.
Conda still enforces channel policies, authentication, and repository terms.

## Configure channels for future operations

conda-self uses your configured channels unless overridden for an installation. Use
[conda config](inv:conda:std:doc#commands/config) to add a custom channel:

```bash
conda config --add channels my-channel -n base
```

Then install normally:

```bash
conda self install my-plugin
```

## Why channel-qualified package specs are rejected

`conda self install conda-forge::my-plugin` is not supported.
Use `--channel` to select the channels for an installation and its dependencies.
Configure channels in `.condarc` when future installs and updates should use
the same channels.

## Channel priority

Channels are searched in the order they appear in your configuration. With
strict channel priority, packages from lower-priority channels are not
considered when a package with the same name exists in a higher-priority
channel. With flexible priority, the solver may use lower-priority channels to
satisfy dependencies.

You can inspect channels with [conda info](inv:conda:std:doc#commands/info) or
by showing configuration values:

```bash
conda config --show channels
conda config --show channel_priority
```

## Private channels

For private channels that require authentication, follow your channel
provider's instructions to configure authentication for conda.
conda-self invokes conda for package operations, so the same authentication
configuration applies.

## Multiple channels

With strict channel priority, if a plugin is available on multiple channels,
conda will use the one with highest priority:

```bash
conda config --add channels conda-forge -n base
conda config --add channels my-company-channel -n base

# my-company-channel has higher priority (added last)
conda self install my-plugin
```
