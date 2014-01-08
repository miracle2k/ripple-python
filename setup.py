#!/usr/bin/env python
# coding: utf-8
from setuptools import setup

setup(
    name="ripple-python",
    description="Python routines for the Ripple payment network",
    author='Michael Elsdörfer',
    author_email='michael@elsdoerfer.com',
    version="1.1.1",
    url="https://github.com/miracle2k/ripple-python",
    license='BSD',
    py_modules=['rippletools'],
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ]
)
