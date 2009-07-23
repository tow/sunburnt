#!/usr/bin/env python

import distutils.core

distutils.core.setup(
    name='sunburnt',
    version='0.3',
    description='Python interface to Solr',
    author='Toby White',
    author_email='toby.o.h.white@gmail.com',
    packages=['sunburnt'],
    requires=['httplib2', 'lxml', 'pytz', 'simplejson']
    )
