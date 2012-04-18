from setuptools import setup, find_packages
from circus import __version__

install_requires=['pyzmq', 'psutil']

try:
    import argparse     # NOQA
except ImportError:
    install_requires.append('argparse')

with open("README.rst") as f:
    README = f.read()

with open("CHANGES.rst") as f:
    CHANGES = f.read()


setup(name='circus',
      version=__version__,
      packages=find_packages(),
      description=("Circus is a program that will let you run and watch "
                   " multiple processes."),
      long_description=README + '\n' + CHANGES,
      author="Mozilla Foundation & contributors",
      author_email="services-dev@lists.mozila.org",
      include_package_data=True,
      zip_safe=False,
      classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 3 - Alpha"],
      install_requires=install_requires,
      test_requires=['nose'],
      test_suite = 'nose.collector',
      entry_points="""
      [console_scripts]
      circusd = circus.circusd:main
      circusctl = circus.circusctl:main
      """)
