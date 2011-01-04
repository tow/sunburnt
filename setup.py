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
    )
