This folder contains files from the Anaconda distribution that had to be modified for Apodexei.

In particular:

# Failures with '['cmd.exe', '/d', '/c', 'conda_build.bat']' - all because of $ANACONDA_HOME/Lib/py_compile.py

This was causing failures with `setup.py install` that appear to be spurious failures: complaints about
"missing files" that in reality don't correspond to any real file, so it shouldn't be declared as missing in the first place.
This at first manifests with cryptic errors such as this:

```
  File "C:\Users\aleja\Documents\CodeImages\Technos\Anaconda3\lib\site-packages\conda_build\utils.py", line 392, in _func_defaulting_env_to_os_environ
    raise subprocess.CalledProcessError(proc.returncode, _args)
subprocess.CalledProcessError: Command '['cmd.exe', '/d', '/c', 'conda_build.bat']' returned non-zero exit status 1.
```

Upon investigation, the failure in the `conda_build.bat` can be investigated in the debugger, by simply using the temporary
conda environment that is created by the aborted built, based on build ids such as `1623480622393`. Such an environment
lives in folders such as 
`$ANACONDA_HOME\conda-bld\apodeixi_1623480622393\_h_env`, and the working folder of the build has a `setup.py` that is invoked
by the failed `conda_build.bat` above. Thus, one can debug and run
`$ANACONDA_HOME\conda-bld\apodeixi_1623480622393\work\setup.py install`.

This will produce the *real error*, which looks like this:

```
apodeixi.xli.tests_unit.__pycache__.test_breakdown_builder.cpython-39: module references __file__
creating dist
creating 'dist\apodeixi-0.3.0a3-py3.9.egg' and adding 'build\bdist.win-amd64\egg' to it
removing 'build\bdist.win-amd64\egg' (and everything under it)
Processing apodeixi-0.3.0a3-py3.9.egg
removing 'c:\users\aleja\documents\codeimages\technos\anaconda3\conda-bld\apodeixi_1623480622393\_h_env\lib\site-packages\apodeixi-0.3.0a3-py3.9.egg' (and everything under it)
creating c:\users\aleja\documents\codeimages\technos\anaconda3\conda-bld\apodeixi_1623480622393\_h_env\lib\site-packages\apodeixi-0.3.0a3-py3.9.egg
Extracting apodeixi-0.3.0a3-py3.9.egg to c:\users\aleja\documents\codeimages\technos\anaconda3\conda-bld\apodeixi_1623480622393\_h_env\lib\site-packages
error: [Errno 2] No such file or directory: 'c:\\users\\aleja\\documents\\codeimages\\technos\\anaconda3\\conda-bld\\apodeixi_1623480622393\\_h_env\\lib\\site-packages\\apodeixi-0.3.0a3-py3.9.egg\\apodeixi\\controllers\\journeys\\delivery_planning\\tests_unit\\__pycache__\\test_milestones_controller.cpython-39.pyc.2200393665552'

```

This shows that the real problem, that looks like a bug in `$ANACONDA_HOME/Lib/py_compile.py`: while the real file
`test_milestones_controller.cpython-39.pyc` is found without problems, the compiler seems to be looking for
a spurious file `test_milestones_controller.cpython-39.pyc.2200393665552` that shouldn't have to exist in the first place.

The fix is to change this offending line in `py_compile.py`:

```

def compile(file, cfile=None, dfile=None, doraise=False, optimize=-1,
            invalidation_mode=None, quiet=0):

        // Lots of things happening and then:

    mode = importlib._bootstrap_external._calc_mode(file)

    importlib._bootstrap_external._write_atomic(cfile, bytecode, mode)  <<<<< BUILT-IN MODULE THROWS SPURIOUS EXCEPTION
    return cfile

```

My workaround fix was simply to not throw exceptions, so the build did not stop anymore. The resulting distribution works OK,
so this exception was not really a problem. And besides I found in the debugger that the compile was previously done 
successfully, and the offending behavior happened only towards the end of the entire process, when a seemingly unnecessary
second round of building was attempted.

This workaround fixed it, which is an edit I did directly on my local Anaconda distribution, so it needs to be re-applied
if I update Anaconda later:

```
    mode = importlib._bootstrap_external._calc_mode(file)
    try:
        importlib._bootstrap_external._write_atomic(cfile, bytecode, mode)
    except Exception as ex:
        print("................ From Alejandro in <env>/Lib/py_compile.py: found exception " + str(ex))
    return cfile

```

A final twist to the mystery is that even though each virtual environment seems to have a different copy of 
`Lib/py_compile.py`, it appears that they are all **hard links** to each other for a given Python version( 3.x and 2.x are different,
but all the environments for 3.x have the *same file*: you change one of them and the others reflect the change)