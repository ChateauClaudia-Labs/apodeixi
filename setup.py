from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

# Versioning numbers try to follow PEP 440
# https://www.python.org/dev/peps/pep-0440/
setup(name='apodeixi',
      version='0.1.0a1.dev3',
      description='Proof-oriented, reverse Conway domain model and controllers for human organizations, inspired by Kubernetes',
      long_description=long_description,
      long_description_content_type="text/markdown", 
      url='https://github.com/ChateauClaudia-Labs/apodeixi.git',
      author='Alejandro Hernandez',
      author_email='alejandro@chateauclaudia-labs.com',
      license='MIT',
      packages=['apodeixi', 'apodeixi.xli'], 'apodeixi.util',
      zip_safe=False)


'''
Some other fields we might consider using:


      long_description=long_description,
      long_description_content_type="text/markdown",      

      #packages=setuptools.find_packages(),      
      packages=['devanalyst', 'devanalyst-examples'],
      install_requires=[
          'pandas', 'numpy', 'IPython', 'nbformat',
      ],
      setup_requires=["pytest-runner", ],
      tests_require=["pytest",],
      include_package_data=True,

      keywords='development efficiency analysis process simulation',
      classifiers=[
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 2 - Pre-Alpha',
        'Topic :: Software Development',
      ],
      '''