.. _about:

About Sunburnt
==============

Sunburnt is a library to interface with a Solr instance from Python. It was written by Toby White <toby@timetric.com>, originally for use with the Timetric platform (http://timetric.com).

Sunburnt is designed to provide a high level API for

 * querying Solr in a Pythonic way, without having to understand Solr's query syntax in depth, and
 * inserting Python objects into a Solr index with the minimum of fuss,

and particularly importantly, to provide Python-level error-checking. If you make a mistake, sunburnt will do its best to tell you why, rather than just throwing back an obscure Solr error.

For an overview of the design choices, see http://blog.eaddrinu.se/blog/2010/sunburnt.html.
