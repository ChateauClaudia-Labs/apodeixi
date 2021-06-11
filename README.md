# apodeixi
Proof-oriented, reverse Conway domain model for human organizations

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
