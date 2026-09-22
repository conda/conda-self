[//]: # (current developments)

## 0.3.0 (2026-09-22)

### Enhancements

* Bare and `--plugin` updates now use `conda install --update-deps` so conda can
  update dependencies of the requested package. (#152 via #171)

### Bug fixes

* Reuse an installed conda package when its package URL and any recorded
  checksum match the snapshot and the package does not need to be reinstalled,
  so an unavailable URL does not block the exact reset. (#150 via #177)
* Validate recorded checksums for local snapshot archives and report download,
  extraction, and package-cache lookup failures before changing the target
  environment. (#150 via #177)
* Respect `--json` and `--quiet` when reporting reset progress and completion.
  (#150 via #177)
* Reject the ambiguous `--snapshot installer` option before confirmation or
  environment changes. Explain how to migrate to `installer-exact` to restore
  the recorded conda packages or `installer-updated` to retain their currently
  installed versions without updating or installing missing packages. (#150 via #177)

### Docs

* Correct the documented reset modes, automatic fallback order, installer
  snapshot filename, and exact-reset limitations. (#150 via #177)
* Document how to generate and serve local HTML coverage reports. (#183 via #184)
* Align CLI help, errors, documentation, and recorded demos with Conda
  terminology and the existing behavior of package operations and base
  protection. (#181)
* Update package metadata and documentation links to the conda organization.

### Other

* Add `pytest-cov`, Pixi tasks for line and branch coverage, and Codecov
  uploads to the test workflow. (#183 via #184)
* Exclude local editor and agent files from source distributions.

### Contributors

* @danyeaw
* @jezdez
* @conda-bot
* @dependabot[bot]

## 0.2.1 (2026-07-22)

### Bug fixes

* Make frozen `base` environment errors explain that direct modifications are protected and point to `conda self --help` for supported commands. (#142)
* Keep `conda self update --json` output parseable and forward `--quiet` to the child conda process. (#160)

### Other

* Enable infrastructure-managed Dependabot configuration via conda/infrastructure templates. (#147)

### Contributors

* @danyeaw
* @jezdez
* @kenodegard
* @conda-bot made their first contribution in https://github.com/conda/conda-self/pull/143
* @dependabot[bot]
* @pre-commit-ci[bot]

## 0.2.0 (2026-05-06)

### Enhancements

* Add `conda self reset` to restore the base environment to its installer-provided or post-migration state. (#54, #55 via #83)
* Add `--all` flag to `conda self update` to update conda, all plugins, and all dependencies. (#37 via #79, #80 via #84)
* Add `--yes` support to `conda self remove` and `conda self update` subcommands. (#108)
* Add support for removing non-essential plugins with `conda self remove`, including a `--force` flag to override permanent package protection. (#95, #127)
* Register `base-protection` health check for `conda doctor --fix`. (#88)
* Add configurable `self_permanent_packages` setting. (#116)
* Reject channel specs in `conda self install` (use `.condarc` instead). (#118)
* Split `--snapshot installer` into `installer-exact` and `installer-updated`. Auto-fallback prefers `installer-updated` and no longer downgrades installer-provided packages like `mamba` in Miniforge installs. (#121)
* Build canary packages on merge to `main`. (#90)

### Bug fixes

* Fix `conda self install` bypassing frozen environment protection. (#119)
* Fix `SpecsAreNotPlugins` error for wheel-based conda plugins. (#106)
* Fix missing `context` import in `query.py`. (#128)

### Docs

* Overhaul documentation with [Diátaxis](https://diataxis.fr) structure (tutorials, how-to guides, reference, explanation). (#120)
* Add 6 [VHS](https://github.com/charmbracelet/vhs) terminal demos: quickstart, install-plugin, base-protection, update, remove, reset. (#120)
* Document custom channel configuration for plugin install. (#117)
* Document how to unprotect the base environment. (#115)

### Other

* Remove `conda migrate` subcommand. (#91)
* Bump minimum Python version to 3.10. (#82)
* Add Python 3.14 to test matrix. (#109)
* Speed up test suite with session-scoped environments. (#129)
* Require conda 25.5.0+. (#63)

### Contributors

* @jezdez
* @kenodegard
* @marcoesters

## 0.1.1 (2025-07-21)

### Bug fixes

* Fix `conda self protect` and `conda self remove` help text. (#17)

### Contributors

* @kenodegard

## 0.1.0 (2025-07-17)

Initial release:

```
$ conda self -h
usage: conda self [-V] [-h] {install,protect,remove,reset,update} ...
Manage your conda 'base' environment safely.

options:
  -V, --version         Show the 'conda-self' version number and exit.
  -h, --help            Show this help message and exit.

subcommands:
  {install,protect,remove,reset,update}
    install             Add conda plugins to the 'base' environment.
    protect             Remove conda plugins from the 'base' environment.
    remove              Protect 'base' environment from any further modifications
    reset               Reset 'base' environment to essential packages only.
    update              Update 'conda' and/or its plugins in the 'base' environment.
```

### Contributors

* @jaimergp
* @soapy1
