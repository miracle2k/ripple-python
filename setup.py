#!/usr/bin/env python
# coding: utf-8
from setuptools import setup, find_packages

setup(
    name="ripple-python",
    description="Python routines for the Ripple payment network",
    author='Michael Elsdörfer',
    author_email='michael@elsdoerfer.com',
    version="0.2.1",
    url="https://github.com/miracle2k/ripple-python",
    license='BSD',
    packages = find_packages(),
    zip_safe=True,
    install_requires=[
        'ecdsa>=0.10',
        'websocket-client>=0.12'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ]
)
