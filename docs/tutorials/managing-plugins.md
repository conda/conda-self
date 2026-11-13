# Managing plugins

In this tutorial, you will add a command to conda, use it, and remove it again.
The example is [conda-spawn](https://conda.github.io/conda-spawn/), which opens
a child shell in a conda environment. It is an optional convenience, not a
requirement for using `conda activate` or running Python.

## Before you start

You need conda-self installed in base and configured channels providing
conda-spawn. Base may be protected or unprotected. Protection is not required
for plugin management.

Use the `self-demo` environment from the {doc}`../quickstart` tutorial. If you
are starting here, create it with Python and accept the proposed installation:

```bash
conda create --name self-demo python
```

If you already have an unrelated environment with that name, choose an unused
name and substitute it throughout. For channel setup, see
{doc}`../guides/custom-channels`.

## Install and use an extension

Install conda-spawn into the conda installation:

```bash
conda self install conda-spawn
```

Review and accept conda's proposed changes. Conda-self checks that the requested
package registers a conda plugin. You now have a new `conda spawn` command.

![Install conda-spawn and open a shell in self-demo](../../demos/install-plugin.gif)

{download}`Watch the MP4 recording <../../demos/install-plugin.mp4>`.

Open a child shell in your working environment:

```bash
conda spawn self-demo
```

Your prompt normally shows `(self-demo)`. In that shell, check Python:

```bash
python --version
```

The version is the Python installed in `self-demo`. Leave the child shell to
return to your original shell:

```bash
exit
```

## Update the plugin

Back in your original shell, request an update to this plugin:

```bash
conda self update --plugin conda-spawn
```

Review and accept any proposed changes. If the plugin is already current,
conda reports that the requested packages are already installed. That is a
successful result, not an error.

![Request an update to conda-spawn in base](../../demos/update.gif)

{download}`Watch the MP4 recording <../../demos/update.mp4>`.

This operation targets the plugin and its dependencies in base, not Python
in `self-demo`.

## Remove the extension, keep your environment

When you no longer want the added command, remove its plugin:

```bash
conda self remove conda-spawn
```

Review and accept the removal. The `conda spawn` command is no longer available,
but your working environment still exists. Use ordinary conda to run Python:

```bash
conda run -n self-demo python --version
```

![Remove conda-spawn and verify Python still runs in self-demo](../../demos/remove.gif)

{download}`Watch the MP4 recording <../../demos/remove.mp4>`.

For multiple-plugin operations, update scope, force flags, validation failures,
and protected-package removal rules, use the {doc}`../reference/cli`.
For the reasoning behind the distinction, see {doc}`../motivation`.
