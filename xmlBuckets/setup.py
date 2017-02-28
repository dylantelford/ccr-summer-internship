#!/usr/bin/env python

from distutils.core import setup

setup(name='runBucket',
      version='1.0.0',
      license='LGPLv3',
      author='Dylan Telford',
      author_email='dylantelford@gmail.com',
      url='https://github.com/ubccr/student-projects/tree/dtelford/dtelford/xmlScripts',
      packages=['runBucket'],
      scripts=['runBucket/runBucket.py'],
      requires=['xml'])
      
