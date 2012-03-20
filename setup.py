from setuptools import setup, find_packages

with open("README.rst") as f:
    README = f.read()


setup(name='circus',
      version='0.1',
      packages=find_packages(),
      description=("Circus is a program that will let you run and watch "
                   " multiple processes."),
      long_description=README,
      author="Mozilla Foundation & contributors",
      author_email="services-dev@lists.mozila.org",
      include_package_data=True,
      zip_safe=False,
      classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 3 - Alpha"],
      install_requires=['pyzmq', 'psutil', 'nose'],
      test_suite = 'nose.collector',
      entry_points="""
      [console_scripts]
      circusd = circus.circusd:main
      circusctl = circus.circusctl:main
      """)
