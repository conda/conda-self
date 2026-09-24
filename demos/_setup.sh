#!/usr/bin/env bash
# Source only in a disposable recording shell. Failure terminates that shell.

DEMO_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
DEMO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/conda-self-demo.XXXXXX")" || exit 1
DEMO_ROOT="$(cd "$DEMO_ROOT" && pwd -P)" || exit 1
readonly DEMO_ROOT
trap 'rm -rf -- "$DEMO_ROOT"' EXIT

_setup_demo() {
    local variable hook
    for variable in ${!CONDA_@} ${!_CONDA_@} ${!PIXI_@}; do
        unset "$variable"
    done
    unset -f conda
    export HOME="$DEMO_ROOT/home"
    export XDG_CONFIG_HOME="$HOME/.config"
    export CONDARC="$HOME/.condarc"
    export CONDA_ENVS_PATH="$DEMO_ROOT/envs"
    export CONDA_PKGS_DIRS="$DEMO_ROOT/pkgs"
    export CONDA_CHANNELS=conda-forge
    mkdir -p "$HOME" || return 1
    printf 'channels:\n  - conda-forge\n' > "$CONDARC" || return 1

    MINIFORGE_DIR="$DEMO_ROOT/miniforge"
    DEMO_STAGE=download
    curl -fsSL --retry 2 --max-time 180 -o "$DEMO_ROOT/miniforge.sh" \
        "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname -s)-$(uname -m).sh" || return 1
    DEMO_STAGE=installer
    bash "$DEMO_ROOT/miniforge.sh" -b -p "$MINIFORGE_DIR" \
        > "$DEMO_ROOT/setup.log" 2>&1 || return 1
    DEMO_STAGE=plugin
    "$MINIFORGE_DIR/bin/python" -m pip --isolated install --no-input \
        --index-url https://pypi.org/simple -e "$DEMO_SOURCE" \
        >> "$DEMO_ROOT/setup.log" 2>&1 || return 1

    DEMO_STAGE=activation
    hook="$("$MINIFORGE_DIR/bin/conda" shell.bash hook)" || return 1
    eval "$hook" || return 1
    conda activate base || return 1
    # Refuse to continue if the shell would use a different installation.
    [[ "$(conda info --base)" == "$MINIFORGE_DIR" ]] || return 1
    export PS1="\[\e[1;38;2;67;176;42m\]\$\[\e[0m\] "
}

if ! _setup_demo; then
    printf 'Demo setup failed during %s. Recording stopped.\n' "$DEMO_STAGE" >&2
    exit 1
fi
unset -f _setup_demo
