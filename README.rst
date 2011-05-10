Sunburnt
========

Sunburnt is a Python-based interface for working with the Solr
(http://lucene.apache.org/solr/) search engine.

It was written by Toby White <toby@timetric.com> for use in the Timetric
(http://timetric.com) platform.

Please send queries/comments/suggestions to:
http://groups.google.com/group/python-sunburnt

It's tested with Solr 1.4/1.4.1; previous versions were known to work
with 1.3 as well. It should work with newer versions of Solr as well,
but will not support any newer features.

The API is not fixed yet, but is mostly
stable. Examples of its use can be found at
http://blog.timetric.com/2010/02/08/sunburnt-a-python-solr-interface/


Dependencies
============

- Requirements:

  * httplib2
  * lxml

- Strongly recommended:

  * mx.DateTime

    Sunburnt will happily deal with dates stored either as Python datetime
    objects, or as mx.DateTime objects. The latter are preferable,
    having better semantics and a wider representation range. They will
    be used if present, otherwise sunburnt will fall back to Python
    datetime objects.

  * pytz

    Solr DateFields must be in UTC. If using native Python datetime
    objects, you should also have pytz installed to guarantee correct
    timezone handling.

- Optional (only to run the tests)

  * nose
