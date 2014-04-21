#!/usr/bin/env python
# coding: utf-8
import sys
from setuptools import setup, find_packages


install_requires = [
    'ecdsa>=0.10',
    'six>=1.5.2',
    'websocket-client==dev'
]
dependency_links = [
    # dependency_links will be gone in pip 1.6, but by that time
    # websocket-client on PyPI should have Python3 support.
    'https://github.com/ralphbean/websocket-client/archive/master.zip#egg=websocket-client-dev'
]


setup(
    name="ripple-python",
    description="Python routines for the Ripple payment network",
    author='Michael Elsdörfer',
    author_email='michael@elsdoerfer.com',
    version="0.2.4",
    url="https://github.com/miracle2k/ripple-python",
    license='BSD',
    packages=find_packages(),
    zip_safe=True,
    install_requires=install_requires,
    dependency_links=dependency_links,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ]
)
