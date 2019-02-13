#!/usr/bin/env python

#Not sure of this works right now (v.0.2beta)

from distutils.core import setup

setup(name='Sign Recorder',
      version='0.2.1beta',
      description='Program for displaying prompts and recording video responses for sign language experiments',
      author='Jeffrey Sardina',
      packages=['opencv-python', 'Pillow'],
     )