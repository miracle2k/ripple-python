#!/usr/bin/env python
# coding: utf-8
import sys
from setuptools import setup, find_packages


install_requires = [
    'ecdsa>=0.10',
    'six>=1.5.2',
    'websocket-client==0.14.0'
]


setup(
    name="ripple-python",
    description="Python routines for the Ripple payment network",
    author='Michael Elsdörfer',
    author_email='michael@elsdoerfer.com',
    version="0.2.9",
    url="https://github.com/miracle2k/ripple-python",
    license='BSD',
    packages=find_packages(),
    zip_safe=True,
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.3',
        'License :: OSI Approved :: BSD License',
    ]
)
