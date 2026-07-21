# Installer adapters

Some `conda self` operations depend on how the conda distribution was
installed. Removing a Constructor installation, updating a standalone
launcher, and updating an installation owned by a system package manager
require different policy.

conda-self discovers that policy through its private `conda_self` Pluggy
entry-point group. Distribution packages can provide one adapter for a root
prefix. The adapter can implement uninstall, launcher update, or both.

This is separate from conda's plugin API. It is loaded only for operations
that may belong to an installer adapter.

## Provider entry point

Register the provider module in `pyproject.toml`:

```toml
[project.entry-points.conda_self]
my-distribution = "my_distribution.conda_self"
```

The provider yields an adapter only when it owns the requested prefix:

```python
from conda_self.hookspec import hookimpl
from conda_self.models import CondaSelfAdapter


def uninstall(request):
    ...


def update_launcher(request):
    ...


@hookimpl
def conda_self_adapters(prefix):
    if not (prefix / ".my-distribution").is_file():
        return
    yield CondaSelfAdapter(
        name="my-distribution",
        uninstall=uninstall,
        update_launcher=update_launcher,
    )
```

At most one adapter may claim a root prefix. conda-self raises an error if
multiple adapters claim the same installation.

## Operations

`uninstall` receives an `UninstallRequest`. The adapter owns the removal plan,
confirmation, cleanup, and any package-manager guidance. If no applicable
adapter implements it, `conda self uninstall` refuses to guess how to remove
the installation.

`update_launcher` receives a `LauncherUpdateRequest`. When present, it handles
a bare `conda self update`. An externally managed adapter can refuse the update
and show the exact command for the owning package manager. An adapter for a
standalone installation can update its launcher.

Explicit package operations do not call `update_launcher`:

```bash
conda self update --plugin conda-build
conda self update --all
```

Without an applicable launcher update adapter, a bare `conda self update`
keeps its existing behavior and updates the `conda` package in base.
