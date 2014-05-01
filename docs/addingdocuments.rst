.. _addingdocuments:

Adding documents
================

The easiest way to add data to the sunburnt instance is to do so using a Python dictionary, of exactly the same form as a query result. The dictionary keys are the names of the fields, and the dictionary values are the values of the corresponding fields.

::

 document = {"id":"0553573403",
             "cat":"book",
             "name":"A Game of Thrones",
             "price":7.99,
             "inStock": True,
             "author_t":
             "George R.R. Martin",
             "series_t":"A Song of Ice and Fire",
             "sequence_i":1,
             "genre_s":"fantasy"}

 si.add(document)

You can add lists of dictionaries in the same way. Given the example "books.csv" file, you could feed it to sunburnt like so:

::

 lines = csv.reader(”books.csv”)
 field_names = lines.next()
 documents = [dict(zip(field_names, line) for line in lines]
 si.add(documents)
 si.commit()

.. note:: Committing changes

 Solr separates out the act of adding documents to the index (with ``add()`` above)
 and committing them (with ``commit()``). Only after they are committed will they
 be searchable. However, you can set your Solr instance up to *autocommit* after
 adding documents, so that you don’t need to do a separate commit step. See
 http://wiki.apache.org/solr/SolrConfigXml#Update_Handler_Section. For simple Solr
 instances, this is probably the easiest approach. For heavily used instances, you
 should think carefully about your committing strategy.

If your data is coming from somewhere else, though, you may not already have it in the
form of a dictionary. So sunburnt will accept arbitrary Python objects as input to ``add()``.
To extract the fields, it will inspect the objects for attributes or methods corresponding
to field names, and use the values of the attributes (or, the result of calling the methods) as values.

So in the case above, we might have an object that looked like this:

::

 class Book(object):
     name = “A Game of Thrones”
     author_t = “George R.R. Martin”
     id = “0553573403”
     series_t = “A Song of Ice and Fire”
     sequence_i = 1

     def price(self):
         return check_current_price(self)

     def inStock(self):
         return check_stock_levels(self) > 0


Adding this to the Solr index is as simple as:

::

 si.add(Book())

(and you can add a list of books in the same way)

This is particularly powerful if you’re using something like Django,
which provides you with ORM objects - you can drop these ORM objects
straight into Solr. Given a Django ``Book`` model, you could add the
whole contents of your database with the single call:

::

 si.add(Book.objects.all())

When adding very large quantities of data, you might have a source
which is lazily constructed. With Django, you'd really rather construct
an ORM iterator, and have sunburnt work its way through the iterator
lazily, in multiple updates, rather than try and construct a single
huge update POST. You can do this by doing:

::

 si.add(Book.objects.iterator(), chunk=1000)

where ``chunk`` controls how many documents are put into each update chunk.

.. note:: Multi-valued fields:

Often, a particular document can
have more than one instance of some fields - for instance, a book may
have more than one author.  To include more than one value for a given
field, simply use a list of values rather than a single value:

::

 game_of_thrones_graphic_novel['author_t'] = [
    'George R.R. Martin',
    'Daniel Abraham'
 ]

Even single-valued fields can have values enclosed in lists of length one,
this doesn't hurt anything.

When constructing a ``dict`` with ``list`` values, it's often useful to
use the built-in class ``collections.defaultdict``:

::

 import collections
 book_to_insert = collections.defaultdict(list)
 book_to_insert['author_t'].append('Albert Einstein')
 book_to_insert['author_t'].append('Linus Torvalds')


.. note:: Optional arguments to add:

 ``add()`` takes additional optional arguments: ``commit``, ``commitWithin``, ``softCommit``, ``expungeDeletes``, ``waitSearcher``, ``optimize``, ``maxSegments``.
 See http://wiki.apache.org/solr/UpdateXmlMessages for details.
