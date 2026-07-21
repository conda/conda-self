# Installer adapters

Some `conda self` commands must use the installer that created the root prefix.
Constructor, standalone, and system-package-manager installations cannot all be
updated or removed the same way.

conda-self loads providers from its private `conda_self` Pluggy entry-point
group. A provider yields an adapter when it recognizes the root prefix. The
adapter can implement uninstall, launcher update, or both. This interface does
not use conda's plugin API.

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

`uninstall` receives an `UninstallRequest`. Its callback decides what to remove,
handles confirmation and cleanup, and can print package-manager instructions.
If no applicable adapter provides the callback, `conda self uninstall` exits
without removing the installation.

`update_launcher` receives a `LauncherUpdateRequest` and handles a bare
`conda self update`. A package-manager adapter can reject the update and print
the command users should run instead. A standalone adapter can replace its
launcher.

Explicit package operations do not call `update_launcher`:

```bash
conda self update --plugin conda-build
conda self update --all
```

Without an applicable launcher update adapter, a bare `conda self update`
keeps its existing behavior and updates the `conda` package in base.
