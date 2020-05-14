import sys
from setuptools import setup, find_packages
from circus import __version__

if not hasattr(sys, 'version_info') or sys.version_info < (3, 5, 0, 'final'):
    raise SystemExit("Circus requires Python 3.5 or higher.")


install_requires = ['psutil', 'pyzmq>=17.0', 'tornado>=5.0.2']

try:
    import argparse     # NOQA
except ImportError:
    install_requires.append('argparse')

with open("README.md") as f:
    README = f.read()


setup(name='circus',
      version=__version__,
      packages=find_packages(exclude=["docs", "examples"]),
      description=("Circus is a program that will let you run and watch "
                   " multiple processes and sockets."),
      long_description=README,
      author="Mozilla Foundation & contributors",
      author_email="services-dev@lists.mozila.org",
      include_package_data=True,
      zip_safe=False,
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "License :: OSI Approved :: Apache Software License"
      ],
      install_requires=install_requires,
      extras_require={
        'test': [
            'nose',
            'nose-cov',
            'coverage',
            'mock',
            'circus-web',
            'gevent',
            'papa',
            'PyYAML',
            'pyzmq>=17.0',
            'flake8==2.1.0',
        ],
      },
      test_suite='circus.tests',
      entry_points="""
      [console_scripts]
      circusd = circus.circusd:main
      circusd-stats = circus.stats:main
      circusctl = circus.circusctl:main
      circus-top = circus.stats.client:main
      circus-plugin = circus.plugins:main
      """)
