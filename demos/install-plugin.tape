Source demos/_settings.tape
Env TMPDIR "/tmp"
Env SHELL "/bin/bash"

Output demos/install-plugin.gif
Output demos/install-plugin.mp4

Hide
Type `source demos/_setup.sh`
Enter
Wait /\$/
Type `conda create --name self-demo python --yes > "$DEMO_ROOT/prepare.log" 2>&1 || exit 1`
Enter
Wait /\$$/
Type `printf 'PS1=%q\n' "$PS1" > "$HOME/.bash_profile"`
Enter
Wait /\$$/
Type "clear"
Enter
Wait /\$/
Show

Type "# Add a command to conda, not a project package"
Enter
Type@60ms "conda self install conda-spawn"
Enter
Wait /Proceed/
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
Type "# Open a child shell in your working environment"
Enter
Type@60ms "conda spawn self-demo"
Enter
Wait /\(self-demo\).*\$$/
Type@60ms "python --version"
Enter
Wait /\$/
Sleep 2s
Type "# Return to the original shell"
Enter
Type@60ms "exit"
Enter
Wait /\$$/
Sleep 3s

Hide
Type `conda run -n self-demo python --version > "$DEMO_ROOT/python.log" && conda spawn --help > "$DEMO_ROOT/plugin.log" || exit 1`
Enter
Wait /\$$/
Type "exit"
Enter
Sleep 1s
