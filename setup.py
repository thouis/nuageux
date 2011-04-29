import os.path
from distutils.core import setup

# from http://packages.python.org/an_example_pypi_project/setuptools.html
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='nuageux',
      version='0.1',
      keywords='dsitributed computing twisted',
      package_dir={'nuageux': 'src'},
      packages=['nuageux'],
      long_description=read('README'),
      url="https://github.com/thouis/nuageux",
      description="lightweight distributed computing library",
      author="Thouis (Ray) Jones",
      author_email="thouis.jones@curie.fr",
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: System :: Distributed Computing',
        'Framework :: Twisted'])
