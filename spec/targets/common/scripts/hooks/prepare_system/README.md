Scripts fixing, configuring, or installing things that are fundamental to the
system or the sdk build; for example, fixing up the python interepreter symlink
that would otherwise prevent subsequent steps (e.g. if scripts have `python3` in
their shebang but there's is no path to the python3 interpreter specifically on
the file system).

The scripts here are run _once_ when setting up the system for the first build.
For scripts that should be called before every build, put them in _`scripts/prebuild_`
instead.
