#!/usr/bin/env python

from setuptools import setup

version = '0.8.1lu.dev0'

setup(
    name='sunburnt',
    version=version,
    description='Python interface to Solr',
    author='Toby White',
    author_email='toby@timetric.com',
    packages=['sunburnt'],
    install_requires=['httplib2', 'lxml', 'pytz', 'setuptools'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Software Development :: Libraries'],
    )
