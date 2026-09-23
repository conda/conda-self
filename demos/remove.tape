Source demos/_settings.tape
Env TMPDIR "/tmp"

Output demos/remove.gif
Output demos/remove.mp4

Hide
Type `source demos/_setup.sh`
Enter
Wait /\$/
Type `conda create --name self-demo python --yes > "$DEMO_ROOT/prepare.log" 2>&1 && conda self install --yes conda-spawn >> "$DEMO_ROOT/prepare.log" 2>&1 || exit 1`
Enter
Wait /\$$/
Type "clear"
Enter
Wait /\$/
Show

Type "# Remove the extension to conda"
Enter
Type@60ms "conda self remove conda-spawn"
Enter
Wait /\[n\]/
Sleep 2s
Type "y"
Enter
Wait /\$/
Sleep 2s

Hide
Type "clear"
Enter
Wait /\$/
Show
Type "# Your working environment is still available"
Enter
Type@60ms "conda run -n self-demo python --version"
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
