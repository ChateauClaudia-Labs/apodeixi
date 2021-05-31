# What is Conda Packaging?
This project produces a PyPI package, as defined by the
file ``setup.cfg`` in the root folder of this project.

This means users can then do commands like

``pip install apodeixi``

However, for peope who use Conda that is non-ideal, as ``pip`` and ``conda`` are different package managers and may on ocassion be in conflict.

So this folder provides the necessary artifacts to turn that PyPI package and produce a Conda package published to Anaconda.

The procedure followed is described in https://conda.io/projects/conda-build/en/latest/user-guide/tutorials/build-pkgs.html#
