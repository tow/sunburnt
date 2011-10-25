.. _indexmanagement:

Managing your index
===================

Committing changes
------------------

We mentioned the use of ``commit()`` above. It takes three optional arguments:

* ``waitSearcher``
* ``expungeDeletes``
* ``softCommit``

See http://wiki.apache.org/solr/UpdateXmlMessages for details.

Optimizing
----------

After updating an index with new data, it becomes fragmented and performance
suffers. This means that you need to optimize the index. When and how
often you do this is something you need to decide on a case by case basis.
If you only add data infrequently, you should optimize after every new update;
if you trickle in data on a frequent basis, you need to think more about it.
See http://wiki.apache.org/solr/SolrPerformanceFactors#Optimization_Considerations.

Either way, to optimize an index, simply call:

::

 si.optimize()

A Solr optimize also performs a commit, so if you’re about to ``optimize()`` anyway,
you can leave off the preceding ``commit()``. It doesn’t particularly hurt to do both though.

``optimize()`` takes two optional arguments:

* ``waitSearcher``
* ``maxSegments``

See http://wiki.apache.org/solr/UpdateXmlMessages for details.

Rollback
--------

If you haven’t yet added/deleted documents since the last commit, you can issue a rollback to revert the index state to that of the last commit.

::

 si.rollback()
