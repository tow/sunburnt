#!/usr/bin/env python

import distutils.core, os, re

version_number_re = "\s*__version__\s*=\s*((\"([^\"]|\\\\\")*\"|'([^']|\\\\')*'))"
version_file = os.path.join(os.path.dirname(__file__), 'sunburnt', '__init__.py')
version_number = re.search(version_number_re, open(version_file).read()).groups()[0][1:-1]

distutils.core.setup(
    name='sunburnt',
    version=version_number,
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
