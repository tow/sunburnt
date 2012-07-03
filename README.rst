Sunburnt
========

Sunburnt is a Python-based interface for working with the `Apache Solr
<http://lucene.apache.org/solr/>`_ search engine.

It was written by Toby White <toby@timetric.com> for use in the `Timetric
platform <http://timetric.com>`_.

Please send queries/comments/suggestions to the `mailing list
<http://groups.google.com/group/python-sunburnt>`_.

Bugs can be filed on the `issue tracker <https://github.com/tow/sunburnt/issues>`_.

It's tested with Solr 1.4.1 and 3.1; previous versions were known to work
with 1.3 and 1.4 as well.

Full documentation can be found at http://opensource.timetric.com/sunburnt/index.html.

Dependencies
============

The requirements for Sunburnt will automatically be downloaded when using
one of the installation methods (if they are not already available).

- Requirements:

  * `httplib2 <http://code.google.com/p/httplib2/>`_
  * `lxml <http://lxml.de>`_

- Strongly recommended:

  * `mx.DateTime <http://www.egenix.com/products/python/mxBase/mxDateTime/>`_

    Sunburnt will happily deal with dates stored either as Python datetime
    objects, or as mx.DateTime objects. The latter are preferable,
    having better semantics and a wider representation range. They will
    be used if present, otherwise sunburnt will fall back to Python
    datetime objects.

  * `pytz <http://pytz.sourceforge.net>`_

    If you're using native Python datetime objects with Solr (rather than
    mx.DateTime objects) you should also have pytz installed to guarantee
    correct timezone handling.

- Optional (only to run the tests)

  * `nose <http://somethingaboutorange.com/mrl/projects/nose/>`_
