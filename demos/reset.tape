Source demos/_settings.tape
Env TMPDIR "/tmp"

Output demos/reset.gif
Output demos/reset.mp4

Hide
Type `source demos/_setup.sh`
Enter
Wait /\$/
Type `test -f "$MINIFORGE_DIR/conda-meta/initial-state.explicit.txt" && conda self install --yes conda-spawn > "$DEMO_ROOT/prepare.log" 2>&1 || exit 1`
Enter
Wait /\$$/
Type "clear"
Enter
Wait /\$/
Show

Type "# An added plugin, not part of the installer snapshot"
Enter
Type@60ms "conda list -n base conda-spawn"
Enter
Wait /\$/
Sleep 2s
Type "# Preview the exact installer package set"
Enter
Type@60ms "conda self reset --snapshot installer-exact --dry-run"
Enter
Wait /\$/
Sleep 3s

Hide
Type "clear"
Enter
Wait /\$/
Show
Type "# This can remove plugins and downgrade packages"
Enter
Type@60ms "conda self reset --snapshot installer-exact"
Enter
Wait /\[n\]/
Sleep 3s
Type "y"
Enter
Wait /\$/
Sleep 3s

Hide
Type "clear"
Enter
Wait /\$/
Show
Type "# Inspect the result with ordinary conda"
Enter
Type@60ms "conda list -n base"
Enter
Wait /\$/
Sleep 3s
Hide
Type "clear"
Enter
Wait /\$/
Show
Type@60ms "conda --version"
Enter
Wait /\$/
Sleep 3s

Hide
Type `conda list -n base --json | python -c 'import json, sys; assert all(p["name"] != "conda-spawn" for p in json.load(sys.stdin))' || exit 1`
Enter
Wait /\$$/
Type "exit"
Enter
Sleep 1s
