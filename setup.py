# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from setuptools import setup, find_packages


setup(name='circus',
      version='0.1',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=['pyzmq'],
      entry_points="""
      [console_scripts]
      circusd = circus.server:main
      circusctl = circus.client:main
      """)
