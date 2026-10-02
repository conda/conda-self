# Using custom channels

How to install plugins from custom or private channels.

## Configure channels first

conda-self uses your configured channels for all operations. Use
[conda config](inv:conda:std:doc#commands/config) to add a custom channel:

```bash
conda config --add channels my-channel -n base
```

Then install normally:

```bash
conda self install my-plugin
```

:::{note}
Channel-qualified specs such as `conda-forge::my-plugin` are not supported by
`conda self install`. Configure the channel first, as above, then use the
package name. See {doc}`../features` for the design rationale.
:::

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
