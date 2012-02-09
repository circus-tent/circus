import os
from setuptools import setup, find_packages



setup(name='circus',
      version='0.1',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=['pyzmq'],
      entry_points="""
      [console_scripts]
      circusd = circus:main
      """)
