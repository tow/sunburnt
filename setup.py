#!/usr/bin/env python

import distutils.core, os, re

version = '0.8.dev0'

distutils.core.setup(
    name='sunburnt',
    version=version,
    description='Python interface to Solr',
    author='Toby White',
    author_email='toby@timetric.com',
    packages=['sunburnt'],
    requires=['httplib2', 'lxml', 'pytz'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Software Development :: Libraries'],
    )
