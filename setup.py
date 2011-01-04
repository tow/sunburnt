#!/usr/bin/env python

import distutils.core

distutils.core.setup(
    name='sunburnt',
    version='0.4',
    description='Python interface to Solr',
    author='Toby White',
    author_email='toby@timetric.com',
    packages=['sunburnt'],
    requires=['httplib2', 'lxml', 'pytz'],
    license='WTFPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: DFSG approved',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Software Development :: Libraries'],
    )
