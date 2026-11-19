Source demos/_settings.tape
Env TMPDIR "/tmp"

Output demos/quickstart.gif
Output demos/quickstart.mp4

Hide
Type `source demos/_setup.sh`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Show

Type "# A working environment for Python"
Enter
Type@60ms "conda create --name self-demo python"
Enter
Wait /Proceed/
Sleep 1s
Enter
Wait /\$/
Type@60ms "conda activate self-demo"
Enter
Wait /\$/
Sleep 1s

Type "# Install a package for your work"
Enter
Type@60ms "conda install numpy"
Enter
Wait /Proceed/
Sleep 1s
Enter
Wait /\$/
Hide
Type "clear"
Enter
Wait /\$/
Show
Type@60ms `python -c "import numpy; print(numpy.__version__)"`
Enter
Wait /\$/
Sleep 2s

Hide
Type `conda list -n self-demo --explicit > "$DEMO_ROOT/before.txt"`
Enter
Wait /\$$/
Type "clear"
Enter
Wait /\$$/
Show

Type "# Preview maintenance of conda, not self-demo"
Enter
Type@60ms "conda self update --dry-run"
Enter
Wait /\$/
Sleep 2s
Type@60ms "conda self update"
Enter
Wait /Proceed|All requested packages already installed/
Sleep 1s
Enter
Wait /\$/
Sleep 2s

Hide
Type "clear"
Enter
Wait /\$/
Show
Type "# Your working environment is unchanged"
Enter
Type@60ms `python -c "import numpy; print(numpy.__version__)"`
Enter
Wait /\$/
Sleep 3s

Hide
Type `conda list -n self-demo --explicit > "$DEMO_ROOT/after.txt" && diff "$DEMO_ROOT/before.txt" "$DEMO_ROOT/after.txt" || exit 1`
Enter
Wait /\$$/
Type "exit"
Enter
Sleep 1s
