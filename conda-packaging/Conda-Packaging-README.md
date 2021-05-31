# What is Conda Packaging?
This project produces a PyPI package, as defined by the
file ``setup.cfg`` in the root folder of this project.

This means users can then do commands like

``pip install apodeixi``

However, for peope who use Conda that is non-ideal, as ``pip`` and ``conda`` are different package managers and may on ocassion be in conflict.

So this folder provides the necessary artifacts to turn that PyPI package and produce a Conda package published to Anaconda.

The procedure followed is described in https://conda.io/projects/conda-build/en/latest/user-guide/tutorials/build-pkgs.html#

# Steps to follow

First make sure that all build and run dependencies are up-to-date in ``meta_yaml``. Otherwise obscure error messages will occur and the build will fail.

Then you do the real build on the native platform:

``aleja@CC-Labs-2 MINGW64 ~/Documents/Code/chateauclaudia-labs``
``$ conda-build apodeixi/project/conda-packaging/``
