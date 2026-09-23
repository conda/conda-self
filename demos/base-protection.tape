Source demos/_settings.tape
Env TMPDIR "/tmp"

Output demos/base-protection.gif
Output demos/base-protection.mp4

Hide
Type `source demos/_setup.sh`
Enter
Wait /\$/
Type `conda install -n base --yes numpy > "$DEMO_ROOT/prepare.log" 2>&1 || exit 1`
Enter
Wait /\$$/
Type "clear"
Enter
Wait /\$/
Show

Type "# This example base already contains NumPy"
Enter
Type@60ms "conda env list"
Enter
Wait /\$/
Sleep 2s
Type@60ms "conda doctor -n base base-protection"
Enter
Wait /\$/
Sleep 2s
Type@60ms "conda doctor -n base base-protection --fix"
Enter
Wait /Proceed/
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
Type "# Continue your work in the clone"
Enter
Type@60ms "conda activate default"
Enter
Wait /\$/
Type@60ms `python -c "import numpy; print(numpy.__version__)"`
Enter
Wait /\$/
Sleep 2s
Type@60ms "conda doctor -n base base-protection"
Enter
Wait /\$/
Sleep 3s

Hide
Type `test -f "$MINIFORGE_DIR/conda-meta/frozen" && python -c 'import numpy' || exit 1`
Enter
Wait /\$$/
Type `conda config --show default_activation_env --json | python -c 'import json, os, sys; assert json.load(sys.stdin)["default_activation_env"] == os.environ["CONDA_PREFIX"]' || exit 1`
Enter
Wait /\$$/
Type "exit"
Enter
Sleep 1s
