'''
This Python module is intended to help troubleshoot problems that arise when building an Apodeixi distribution.

Context

When using conda-build to build Apodeixi, sometimes the build fails with cryptic errors like this:

    ``subprocess.CalledProcessError: Command '['cmd.exe', '/d', '/c', 'conda_build.bat']' returned non-zero exit status 1.``

This happens when Conda launches a second Python process to run ``setup.py install``, using various environment variable settings.
Conda launches this Python process in a particular Conda environment that is created by ``conda-build``. The location of this
environment depends on the location of the environment in which ``conda-build`` runs.

For example, if ``conda-build`` runs in a Conda environment called ``a6i-env``, then ``conda-build`` will create another Conda
environment with a timestamp based name in a a fodler structure like this (``$ANACONDA_HOME`` denotes the folder where Anaconda is
installed)

    ``$ANACONDA_HOME/envs/" + CONDA_BUILD_ENV + "/conda-bld/apodeixi_1645217951806/_h_env

Then ``conda-build`` launches another Python process in that environment and running in a working folder like

    ``$ANACONDA_HOME/envs/" + CONDA_BUILD_ENV + "/conda-bld/apodeixi_1645217951806/work``

and runs ``setup.py install`` in it, after setting up the environment variables in 

    ``$ANACONDA_HOME/envs/" + CONDA_BUILD_ENV + "/conda-bld/apodeixi_1645217951806/work/build_env_setup.bat``

So to reproduce and troubleshoot build failures, the idea for this module is for the user to switch directory to the working
folder that ``conda-build`` created, and then run this Python module in the debugger (i.e., use this module as __main__), 
placing a stop point in the place where the build failed (typically a line of code in the setuptools package).

'''
import os
import sys
import setuptools


# Ensure these are correctly set for your troubleshooting session
#
CONDA_BUILD_ENV             = "a6i-env"
CONDA_BUILD_DIR             = "C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/project/conda-packaging"
ANACONDA_INSTALL            = "C:/Users/aleja/Documents/CodeImages/Technos/Anaconda3"
THIS_BUILD                  =  ANACONDA_INSTALL + "/envs/" + CONDA_BUILD_ENV + "/conda-bld/apodeixi_1645217951806"



def run_install():
    # Simulate the command-line arguments so the setuptools code is called as if one had entered this command in a Bash shell
    # from a working folder that is the root of the project, i.e., where the setup.py file resides:
    #
    #   % python setup.py install
    #
    sys.argv                = ["setup.py", "install"]
    print(f"Arguments count: {len(sys.argv)}")
    for i, arg in enumerate(sys.argv):
        print(f"Argument {i:>6}: {arg}")

    # Set working directory
    os.chdir(THIS_BUILD + "/work")

    os.environ              = os.environ | changed_environment_variables() # The | operator gives precendence to second argument
    setuptools.setup()


def changed_environment_variables():
    '''
    Set the environment variables required to run setuptools the way Conda runs them. These are the ones in 
    ``build_env_setup.bat``. Not all may be needed for a particular troubleshooting investigation, so these are the "typical"
    ones.

    The defaults suggested here were determined by doing a programmatic diff between the ``os.environ`` dictionary and
    a dictionary representation of the contents of ``build_env_setup.bat`
    '''
    new_environ                             = {}

    # These environment variables don't have different values than in the default os.environ, so don't need to be set
    #
    '''
    LANG, ALLUSERSPROFILE, APPDATA, CommonProgramFiles, CommonProgramFiles(x86), CommonProgramW6432, COMPUTERNAME, 
    ComSpec, HOMEDRIVE, HOMEPATH, LOCALAPPDATA, LOGONSERVER, NUMBER_OF_PROCESSORS, PATHEXT, ProgramData, ProgramFiles, 
    ProgramFiles(x86), ProgramW6432, PSModulePath, PUBLIC, SystemDrive, SystemRoot, TEMP, TMP, USERDOMAIN, USERNAME, USERPROFILE,
    windir, PROCESSOR_ARCHITECTURE, PROCESSOR_IDENTIFIER
    '''

    # These environment variables have different values than in the default os.environ, so they need to be set
    #
    new_environ["CONDA_BUILD"]              = "1"
    new_environ["PYTHONNOUSERSITE"]         = "1"
    new_environ["CONDA_DEFAULT_ENV"]        = THIS_BUILD + "/_h_env"
    new_environ["PATH"]                     = THIS_BUILD + "/_h_env" \
                                            + THIS_BUILD + "/_h_env/Library/mingw-w64/bin" \
                                            + THIS_BUILD + "/_h_env/Library/usr/bin;" \
                                            + THIS_BUILD + "/_h_env/Library/bin" \
                                            + THIS_BUILD + "/_h_env/Scripts" \
                                            + THIS_BUILD + "/_h_env/Scripts" \
                                            + THIS_BUILD + "/_h_env" \
                                            + THIS_BUILD + "/_h_env/Library/mingw-w64/bin" \
                                            + THIS_BUILD + "/_h_env/Library/usr/bin;" \
                                            + THIS_BUILD + "/_h_env/Library/bin" \
                                            + THIS_BUILD + "/_h_env/Scripts" \
                                            + THIS_BUILD + "/_h_env/Scripts" \
                                            + os.environ["PATH"] # Append original path at the end

    # These environment variables are new and did not exist in the default os.environ
    # Make sure they match the package (name, version, GIT, etc) whose build you are troubleshooting
    #
    new_environ["RECIPE_DIR"]                       = CONDA_BUILD_DIR
    new_environ["GIT_DESCRIBE_TAG"]                 = "v0.9.0"
    new_environ["GIT_DESCRIBE_NUMBER"]              = "0"
    new_environ["GIT_DESCRIBE_HASH"]                = "gf88cdc4"
    new_environ["GIT_DESCRIBE_TAG_PEP440"]          = "v0.9.0"
    new_environ["GIT_FULL_HASH"]                    = "f88cdc450064102c009a733c75d6b0e8971998a0"
    new_environ["GIT_BUILD_STR"]                    = "0_gf88cdc4"
    new_environ["PKG_NAME"]                         = "apodeixi" #####
    new_environ["PKG_VERSION"]                      = "0.9.0"
    new_environ["PKG_BUILDNUM"]                     = "0"
    new_environ["PKG_BUILD_STRING"]                 = "placeholder"
    new_environ["PKG_HASH"]                         = "1234567"
    new_environ["ARCH"]                             = "64"
    new_environ["SUBDIR"]                           = "win-64"
    new_environ["build_platform"]                   = "win-64"
    new_environ["CPU_COUNT"]                        = "8"
    new_environ["SHLIB_EXT"]                        = ".dll"
    new_environ["CONDA_PY"]                         = "39"
    new_environ["PY3K"]                             = "1"
    new_environ["PY_VER"]                           = "3.9"
    new_environ["NPY_VER"]                          = "1.16"
    new_environ["CONDA_NPY"]                        = "1.16"
    new_environ["NPY_DISTUTILS_APPEND_FLAGS"]       = "1"
    new_environ["PERL_VER"]                         = "5.26"
    new_environ["CONDA_PERL"]                       = "5.26.2"
    new_environ["LUA_VER"]                          = "5"
    new_environ["CONDA_LUA"]                        = "5"
    new_environ["R_VER"]                            = "3.4"
    new_environ["CONDA_R"]                          = "3.4"
    new_environ["SYS_PREFIX"]                       = ANACONDA_INSTALL + "/envs/" + CONDA_BUILD_ENV
    new_environ["SYS_PYTHON"]                       = ANACONDA_INSTALL + "/envs/" + CONDA_BUILD_ENV + "/python.exe"
    new_environ["ROOT"]                             = ANACONDA_INSTALL + "/envs/" + CONDA_BUILD_ENV
    new_environ["PREFIX"]                           = THIS_BUILD + "/_h_env"
    new_environ["BUILD_PREFIX"]                     = THIS_BUILD + "/_h_env"
    new_environ["SRC_DIR"]                          = THIS_BUILD + "/work"
    new_environ["STDLIB_DIR"]                       = THIS_BUILD + "/_h_env/Lib"
    new_environ["SP_DIR"]                           = THIS_BUILD + "/_h_env/Lib/site-packages"
    new_environ["PYTHON"]                           = THIS_BUILD + "/_h_env/python.exe"
    new_environ["SCRIPTS"]                          = THIS_BUILD + "/_h_env/Scripts"
    new_environ["LIBRARY_PREFIX"]                   = THIS_BUILD + "/_h_env/Library"
    new_environ["LIBRARY_BIN"]                      = THIS_BUILD + "/_h_env/Library/bin"
    new_environ["LIBRARY_INC"]                      = THIS_BUILD + "/_h_env/Library/include"

    new_environ["LIBRARY_LIB"]                      = THIS_BUILD + "/_h_env/Library/lib"
    new_environ["CYGWIN_PREFIX"]                    = "/cygdrive/" + THIS_BUILD.replace("C:", "c/")

    new_environ["BUILD"]                            = "amd64-pc-windows-19.0.0"
    new_environ["pin_run_as_build"]                 = "OrderedDict([" \
                                                        + "('python', OrderedDict([('min_pin', 'x.x'), ('max_pin', 'x.x')])), " \
                                                        + "('r-base', OrderedDict([('min_pin', 'x.x'),('max_pin', 'x.x')]))" \
                                                        + "])"

    new_environ["ignore_build_only_deps"]           = "{'python', 'numpy'}"
    new_environ["extend_keys"]                      = "{'pin_run_as_build', 'ignore_build_only_deps', 'ignore_version', 'extend_keys'}"
    new_environ["cxx_compiler"]                     = "vs2017"
    new_environ["fortran_compiler"]                 = "gfortran"
    new_environ["r_base"]                           = "3.4"
    new_environ["target_platform"]                  = "win-64"
    new_environ["cpu_optimization_target"]          = "nocona"
    new_environ["c_compiler"]                       = "vs2017"
    new_environ["cran_mirror"]                      = "https://cran.r-project.org"
    new_environ["vc"]                               = "14"
    new_environ["CONDA_BUILD_STATE"]                = "BUILD"
    new_environ["PIP_NO_BUILD_ISOLATION"]           = "False"
    new_environ["PIP_NO_DEPENDENCIES"]              = "True"
    new_environ["PIP_IGNORE_INSTALLED"]             = "True"
    new_environ["PIP_CACHE_DIR"]                    = THIS_BUILD + "/pip_cache"
    new_environ["PIP_NO_INDEX"]                     = "True"
    new_environ["DISTUTILS_USE_SDK"]                = "1"
    new_environ["MSSdk"]                            = "1"
    new_environ["PY_VCRUNTIME_REDIST"]              = "%LIBRARY_BIN%/vcruntime140.dll"
    new_environ["VS_VERSION"]                       = "14.0"
    new_environ["VS_MAJOR"]                         = "14"
    new_environ["VS_YEAR"]                          = "2015"
    new_environ["CMAKE_GENERATOR"]                  = "Visual Studio 14 2015 Win64"
    new_environ["MSYS2_ARG_CONV_EXCL"]              = "/AI;/AL;/OUT;/out"
    new_environ["MSYS2_ENV_CONV_EXCL"]              = "CL"
    new_environ["INCLUDE"]                          = THIS_BUILD + "/_h_env/Library/include;%INCLUDE%"
    new_environ["LIB"]                              = THIS_BUILD + "/_h_env/Library/lib;%LIB%"

    return new_environ

if __name__ == "__main__":
    run_install()
