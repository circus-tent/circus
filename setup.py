from setuptools import setup, find_packages


setup(name='circus',
      version='0.1',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License"],
      install_requires=['pyzmq', 'psutil', 'nose'],
      test_suite = 'nose.collector',
      entry_points="""
      [console_scripts]
      circusd = circus.server:main
      circusctl = circus.client:main
      """)
