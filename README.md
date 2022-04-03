# apodeixi
Proof-oriented, reverse Conway domain model for human organizations

# Setting APODEIXI_CONFIG_DIRECTORY environment variable

Apodeixi relies on an environment variable called APODEIXI_CONFIG_DIRECTORY that should be set to a folder containing 
the Apodeixi configuration file to use. The configuration file must be called ApodeixiConfig.toml

An example configuration (for testing purposes) is included in the test distribution (a separate GIT project), 
referencing a test database external to the distribution. This example illustrates setting of the environment variable to that sample configuration:

export APODEIXI_CONFIG_DIRECTORY="C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/test_db"

For interactive testing, it is sometimes convenient to set up a UAT environment, with its dedicated configuration
file, and point Apodeixi to it, as in this example:

export APODEIXI_CONFIG_DIRECTORY="C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/UAT_ENV"

# Using a sandbox in the CLI

You can use the --environment option to use a particular environment.
If you use many commands repeatedly, it may be worth saving the name of the sandbox in an environment variable and using
it in the command.

Example

export SANDBOX="210902.164354_sandbox"

apo get form --environment ${SANDBOX} big-rocks.journeys.a6i my-corp.production

# Sizing up the project

You can use pygcount to get a sense of how much Python code there is. Here is an example of usage:

    aleja@CC-Labs-2 MINGW64 ~/Documents/Code/chateauclaudia-labs/apodeixi/project/src (dev)
    $ pygount --format=summary ./
    Language     Files    %     Code     %     Comment    %
    -------------  -----  ------  -----  ------  -------  ------
    Python           108   27.41  16929   51.27    10977   99.98
    Text only         42   10.66  13605   41.20        0    0.00
    YAML              31    7.87   2474    7.49        0    0.00
    TOML               1    0.25     13    0.04        2    0.02
    __unknown__       35    8.88      0    0.00        0    0.00
    __empty__         40   10.15      0    0.00        0    0.00
    __duplicate__    102   25.89      0    0.00        0    0.00
    __binary__        35    8.88      0    0.00        0    0.00
    -------------  -----  ------  -----  ------  -------  ------
    Sum total        394          33021            10979
    (a6i-env)


# Running the tests

At the root of the project, run `python -m unittest -v` (you may ommit the `-v` option to avoid seeing the results for each individual test case).

*Example*:
 
```
aleja@CC-Labs-2 MINGW64 ~/Documents/Code/chateauclaudia-labs/apodeixi/project (main)
$ python -m unittest -v
test_multi_sheet (apodeixi.xli.tests_unit.test_BreakdownBuilder.Test_MultiSheet) ... ok
test_generateUID (apodeixi.xli.tests_unit.test_UID_Store.Test_UIDStore) ... ok
test_tokenize (apodeixi.xli.tests_unit.test_UID_Store.Test_UIDStore) ... ok
```

To run an individual test, you can do something like this.

```
aleja@CC-Labs-2 MINGW64 ~/Documents/Code/chateauclaudia-labs/apodeixi/project (main)
$ python -m unittest apodeixi.xli.tests_unit.test_BreakdownBuilder.Test_MultiSheet.test_multi_sheet
.
----------------------------------------------------------------------
Ran 1 test in 1.421s

OK
```

To run all tests except a particularly slow test such as `test_aha_importer`, set the `SMOKE_TESTS_ONLY` environment variable:

`SMOKE_TESTS_ONLY=True python -m unittest -v`
