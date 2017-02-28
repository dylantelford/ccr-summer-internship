#!/usr/bin/env python

from distutils.core import setup

setup(name='monitorLogs',
      version='1.0.0',
      license='LGPLv3',
      author='DylanTelford',
      author_email='dylantelford@gmail.com',
      url='https://github.com/ubccr/student-projects/tree/dtelford/dtelford/vmlogs',
      packages=['monitorLogs'],
      scripts=['monitorLogs/monitorLogs.py'],
      requires=['inotify'])
