# conda-self

Maintain conda itself, separately from the Python and packages you use for
your work.

Conda-self provides commands for updating conda and managing its extensions,
called plugins. It also helps protect the `base` environment where conda is
installed from accidental changes.

You do not need conda-self to create an environment or start using Python.
New to conda? Start with
[conda's getting-started guide](https://docs.conda.io/projects/conda/en/stable/user-guide/getting-started.html).

## Install

With conda 26.1.1 or later and a configured channel providing conda-self:

```bash
conda install -n base conda-self
conda self --help
```

Installing conda-self does not automatically protect base or move existing
packages. Protection is a separate operation.

## Update conda

You can maintain conda while a project environment is active:

```bash
conda self update --dry-run
conda self update
```

These commands target conda in base, not the packages in your active project
environment. Continue using regular `conda install` commands for project
packages. `conda self install` is for conda plugins, not ordinary Python packages.

## Documentation

- [Quick start](https://conda.github.io/conda-self/quickstart/): learn to keep project packages separate from conda maintenance.
- [Understanding conda-self](https://conda.github.io/conda-self/motivation/): base environments, plugins, and why protection exists.
- [Protecting base](https://conda.github.io/conda-self/guides/protecting-base/): understand the changes before migrating existing work.
- [CLI reference](https://conda.github.io/conda-self/reference/cli/) and [configuration](https://conda.github.io/conda-self/configuration/): command options, settings, and limitations.
- [Resetting base](https://conda.github.io/conda-self/guides/resetting-base/): choose a recovery operation deliberately.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md), including how to record the VHS demos.
