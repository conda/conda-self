Source demos/_settings.tape
Env TMPDIR "/tmp"

Output demos/update.gif
Output demos/update.mp4

Hide
Type `source demos/_setup.sh`
Enter
Wait /\$/
Type `conda self install --yes conda-spawn > "$DEMO_ROOT/prepare.log" 2>&1 || exit 1`
Enter
Wait /\$$/
Type "clear"
Enter
Wait /\$/
Show

Type "# Maintain this conda plugin in base"
Enter
Type@60ms "conda self update --plugin conda-spawn"
Enter
Wait /Proceed|\$$/
Sleep 2s
Enter
Wait /\$$/
Sleep 4s

Hide
Type `conda spawn --help > "$DEMO_ROOT/plugin.log" || exit 1`
Enter
Wait /\$$/
Type "exit"
Enter
Sleep 1s
