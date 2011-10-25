.. _deletingdocuments:

Deleting documents
==================

You can delete documents individually, or delete all documents resulting frmo a query.

To delete documents individually, you need to pass a list of the documents to
sunburnt. You can pass them as dictionaries or objects, as for ``add()``. Note
that in this case, matching will be done by id, not by matching the full document.
If you pass in a document which is different from that in the index, the indexed
document with the same id will be deleted, even if all the other attributes are different.

::

 si.delete(obj) # you can pass a single object (or dictionary)
 si.delete(list_of_objs) # or a list of objects or dictionaries.

You can also simply pass in an id, or list of ids, rather than the whole document

::

 si.delete("0553573403")
 si.delete(["0553573403", "0553579908"])

To delete documents by query, you construct one or more queries from `Q` objects,
in the same way that you construct a query as explained in :ref:`optional-terms`.
You then pass those queries into the ``delete()`` method:

::

 si.delete(queries=si.Q("game")) # or a list of queries

If you need to, you can mix and match individual deletion and deletion by query.

::

 si.delete(docs=list_of_docs, queries=list_of_queries)

To clear the entire index, there is a shortcut which simply deletes every document in the index.

::

 si.delete_all()

Deletions, like additions, only take effect after a commit (or autocommit).

.. note:: Optional arguments to delete:

 ``delete()`` takes additional optional arguments: ``commit``, ``commitWithin``, ``softCommit``, ``expungeDeletes``, ``waitSearcher``, ``optimize``, ``maxSegments``.
  See http://wiki.apache.org/solr/UpdateXmlMessages for details.
