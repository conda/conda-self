# How conda-self works

This page explains the implementation choices behind conda-self. For the
distinction between conda, project environments, and plugins, start with
{doc}`motivation`. Exact command behavior is documented in {doc}`reference/cli`.

## Base environment protection

Protection combines a best-effort recovery snapshot, a clone for continued
work, removal of unretained conda packages, and a frozen-environment marker.
The installer snapshot, when available, helps preserve packages provided by
the original distribution. Protection also changes conda's configured default
activation target to the clone's path.

Freezing uses conda's existing environment protection mechanism rather than a
second permission system. Ordinary conda commands refuse modifications and
the marker's message points readers to `conda self --help`. Explicit overrides
remain possible. Programs that do not use conda's checks can still modify files.

See {doc}`guides/protecting-base` for the procedure and
{doc}`configuration` for settings and snapshot files.

## Subprocesses and conda's checks

Conda-self delegates package operations to conda subprocesses rather than
calling the solver directly. The subprocess uses the Python executable running
conda and targets that installation's prefix, independently of an activated
project environment.

The install, update, and remove commands pass `--override-frozen` to allow their
intended maintenance operations. Conda's other transaction checks, dependency
resolution, channel settings, and reporting still apply. This also works when
base has not been frozen.

This choice keeps frozen-environment handling in conda's CLI, where it is
implemented. See [issue #15](https://github.com/conda/conda-self/issues/15) for
the original discussion.

## Plugin validation

After installation, conda-self checks whether the requested distribution
registers a `conda` entry point. Names are compared case-insensitively, treating
hyphens and underscores as equivalent. Checking installed metadata supports
third-party plugins without maintaining an allowlist of package names.

If validation fails, conda-self removes the requested package and reports an
error. Dependencies installed with it may remain. This is not a transaction
that restores every package to its previous state, nor a security audit of
plugin code.

## Snapshots and reset

Snapshots use conda's explicit format, containing complete package URLs and
an `@EXPLICIT` marker. Exact reset modes restore the recorded conda package
set without asking the solver to choose new versions. They can reuse matching
installed packages or retrieve required packages from caches and recorded URLs.

The other reset modes retain selected installed packages instead of restoring
an exact snapshot. In particular, `installer-updated` does not update anything
or install missing packages. It retains installed versions of installer
packages, together with conda, conda-self, plugins, permanent packages, and
their dependencies.

Automatic mode selection avoids an exact installer reset because it may
downgrade packages. Exact modes may also remove plugins or permanent packages
absent from their snapshot. The {doc}`guides/resetting-base` guide helps choose
the appropriate operation. {doc}`reference/cli` describes mode selection and
failure behavior precisely.

## Channel configuration

Plugin installation and updates use configured channels. Conda-self rejects
channel-qualified specs such as `conda-forge::my-plugin` rather than accepting
a channel choice for one installation that would not configure later updates.
The {doc}`guides/custom-channels` guide explains how to configure the channels
used by subsequent operations.

## Health check integration

Base protection is registered with `conda doctor`, alongside other environment
health checks. This reuses conda's inspection and repair workflow rather than
adding a separate top-level migration command.
