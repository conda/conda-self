### Enhancements

### Bug fixes

### Deprecations

* Mark `conda self install` as pending deprecation in conda-self 0.4.0. With conda 26.11.0 or later, use `conda plugins install -n base PACKAGE`. The old command delegates plugin validation and the freeze check to native conda when available and continues to work on older conda versions. Warnings can begin in a March or September conda-self release after at least four months and two regular conda releases. Removal is planned for the following deprecation window. (#222)

### Docs

### Other
