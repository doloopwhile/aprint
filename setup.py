#!/usr/bin/env python3
# coding: utf-8
from setuptools import setup, find_packages
import sys

setup(
    name='aprint',
    version='0.1',
    description='Yet another Pretty Printer inspired by awesome_print in Ruby',
    long_description=open('README.rst').read(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
    ],
    keywords=[''],
    author='OMOTO Kenji',
    author_email='doloopwhile@gmail.com',
    license='MIT',
    install_requires=['colorama'],
    packages=find_packages(),
    test_suite='',
    tests_require=[''],
)
