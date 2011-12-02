.. _queryingsolr:

Querying Solr
=============

For the examples in this chapter, I'll be assuming that you've
loaded your server up with the books data supplied with the
example Solr setup.

The data itself you can see at ``$SOLR_SOURCE_DIR/example/exampledocs/books.csv``.
To load it into a server running with the example schema:

::

 cd example/exampledocs
 curl http://localhost:8983/solr/update/csv \
   --data-binary @books.csv \
   -H 'Content-type:text/plain; charset=utf-8'

If you're working through this manual tutorial-stylye, you might
want to keep a copy of the ``books.csv`` file open in an editor
to check the expected results of some of the queries we'll try.

Throughout the examples, I'll assume you've set up a ``SolrInterface`` object
pointing at your server, called ``si``.

::

 si = SolrInterface(SOLR_SERVER_URL)


Searching your solr instance
----------------------------

Sunburnt uses a chaining API, and will hopefully look quite familiar
to anyone who has used the Django ORM.

The ``books.csv`` data uses a schema which looks like this:

+----------------+------------+
| Field          | Field Type |
+================+============+
| ``id``         | string     |
+----------------+------------+
| ``cat``        | string     |
+----------------+------------+
| ``name``       | text       |
+----------------+------------+
| ``price``      | float      |
+----------------+------------+
| ``author_t``   | string     |
+----------------+------------+
| ``series_t``   | text       |
+----------------+------------+
| ``sequence_i`` | integer    |
+----------------+------------+
| ``genre_s``    | string     |
+----------------+------------+

and the default search field is a generated field, called "text" which is generated from ``cat`` and ``name``.

.. note:: Dynamic fields.

 The last four fields are named with a suffix. This is because they are dynamic fields - see :doc:`solrbackground`.

A simple search for one word, in the default search field.

::

 si.query("game") # to search for any books with "game" in the title.

Maybe you want to search in the (non-default) field author_t for authors called Martin

::

 si.query(author_t="martin")

Maybe you want to search for books with "game" in their title, by an author called "Martin".

::

 si.query(name="game", author_t="Martin")

Perhaps your initial, default, search is more complex, and has more than one word in it:

::

 si.query(name="game").query(name="thrones")

.. note:: Sunburnt query strings are not solr query strings

 When you do a simple query like ``query("game")``, this is just a query on
 the default field. It is *not* a solr query string. This means that the
 following query might not do what you expect:

 ``si.query("game thrones")``

 If you're familiar with solr, you might expect that to return any documents
 which contain both "game" and "thrones", somewhere in the default field.
 Actually, it doesn't. This searches for documents containing *exactly* the
 string "``game thrones``"; the two words next to each other, separated only
 by whitespace.

 If you want to search for documents containing both strings but you don't
 care in what order or how close together, then you follow the example
 above and do ``si.query("game").query("thrones")``. If you want to search
 for documents that contain ``game`` ``OR`` ``thrones``, then see :ref:`optional-terms`.


Since queries are chainable, the name/author query above could also be written

::

 si.query(name="game").query(author_t="Martin")

You can keep on adding more and more queries in this way; the effect is to
``AND`` all the queries. The results which come back will fulfil all of the
criteria which are selected. Often it will be simplest to put all the
queries into the same ``query()`` call, but in a more complex environment,
it can be useful to partially construct a query in one part of your program,
then modify it later on in a separate part.


Executing queries and interpreting the response
-----------------------------------------------

Sunburnt is lazy in constructing queries. The examples in the previous section
don’t actually perform the query - they just create a "query object" with the
correct parameters. To actually get the results of the query, you’ll need to execute it:

::

 response = si.query("game").execute()

This will return a ``SolrResponse`` object. If you treat this object as a list,
then each member of the list will be a document, in the form of a Python dictionary
containing the relevant fields:

For example, if you run the first example query above, you should see a response like this:

::

 >>> for result in si.query("game").execute():
 ...    print result

 {'author_t': u'George R.R. Martin',
  'cat': (u'book',),
  'genre_s': u'fantasy',
  'id': u'0553573403',
  'inStock': True,
  'name': u'A Game of Thrones',
  'price': 7.9900000000000002,
  'sequence_i': 1,
  'series_t': u'A Song of Ice and Fire'}
 {'author_t': u'Orson Scott Card',
  'cat': (u'book',),
  'genre_s': u'scifi',
  'id': u'0812550706',
  'inStock': True,
  'name': u"Ender's Game",
  'price': 6.9900000000000002,
  'sequence_i': 1,
  'series_t': u'Ender'}

Solr has returned two results. Each result is a dictionary, containing all the fields which we initially uploaded.

.. note:: Multivalued fields

 Because ``cat`` is declared in the schema as a multivalued field,
 sunburnt has returned the ``cat`` field as a tuple of results -
 albeit in this case both books only have one category assigned to
 them, so the value of the ``cat`` field is a length-one tuple.

.. note:: Floating-point numbers

 In both cases, although we initially provided the price to two
 decimal places, Solr stores the answer as a floating point number.
 When the result comes back, it suffers from the common problem of
 representing decimal numbers in binary, and the answer looks
 slightly unexpected.


Of course, often you don’t want your results in the form of a dictionary,
you want an object.  Perhaps you have the following class defined in your code:

::

 class Book:
     def __init__(self, name, author_t, **other_kwargs):
         self.title = name
         self.author = author_t
         self.other_kwargs = other_kwargs

     def __repr__(self):
         return 'Book("%s", "%s")' % (title, author)


You can tell sunburnt to give you ``Book`` instances back by telling ``execute()`` to use the class as a constructor.

::

 >>> for result in si.query(“game”).execute(constructor=Book):
 ...     print result

 Book("A Game of Thrones", "George R.R. Martin")
 Book("Ender's Game", "Orson Scott Card")

The ``constructor`` argument most often will be a class, but it can be any callable; it will always be called as ``constructor(**response_dict)``.


You can extract more information from the response than simply the list of results. The SolrResponse object has the following attributes:

* ``response.status`` : status of query. (If this is not ‘0’, then something went wrong).
* ``response.QTime`` : how long did the query take in milliseconds.
* ``response.params`` : the params that were used in the query.

and the results themselves are in the following attributes

* ``response.result`` : the results of your main query.
* ``response.facet_counts`` : see `Faceting`_ below.
* ``response.highlighting`` : see `Highlighting`_ below.
* ``response.more_like_these`` : see `More Like This`_ below.

Finally, ``response.result`` itself has the following attributes

* ``response.result.numFound`` : total number of docs in the index which fulfilled the query.
* ``response.result.docs`` : the actual results themselves (more easily extracted as ``list(response)``).
* ``response.result.start`` : if the number of docs is less than numFound, then this is the pagination offset. 


Pagination
----------

By default, Solr will only return the first 10 results
(this is configurable in ``schema.xml``). To get at more
results, you need to tell solr to paginate further through
the results. You do this by applying the ``paginate()`` method,
which takes two parameters, ``start`` and ``rows``:

::

 si.query("black").paginate(start=10, rows=30)

will query for documents containing "black", and then return the
11th to 40th results. Solr starts counting at 0, so ``start=10``
will return the 11th result, and ``rows=30`` will return the next 30 results,
up to the 40th.


Pagination with Django
......................

If you are using sunburnt with `Django
<https://www.djangoproject.com/>`_, you can paginate your query
results with `Django's Paginator
<https://docs.djangoproject.com/en/1.3/topics/pagination/>`_.  For
example, the pagination example above could be wrapped in a Django
Paginator as simply as this:

::

  from django.core.paginator import Paginator

  paginator = Paginator(si.query("black"), 30)    # 30 results per page

The resulting paginator object can then be used in a Django view (or
anywhere else you want to paginate contents) exactly as described in
the `paginator example in the Django documentation
<https://docs.djangoproject.com/en/1.3/topics/pagination/#using-paginator-in-a-view>`_.

.. Note::

  When using a sunburnt query object with a Django paginator, you can
  chain any number of filters or any of the other methods that return
  a :class:`~sunburnt.SolrSearch` instance; however, you should *not*
  call :meth:`~sunburnt.SolrSearch.execute`, as that will execute the
  query and return the result set for the current query; to function
  properly, the paginator needs to be able to query Solr for the total
  number of matches for the query and then add pagination options to
  slice up the results appropriately.

Returning different fields
--------------------------

By default, Solr will return all stored fields in the results. You
might only be interested in a subset of those fields. To restrict
the fields Solr returns, you apply the ``field_limit()`` method.

::

  si.query("game").field_limit("id") # only return the id of each document
  si.query("game").field_limit(["id", "name"]) # only return the id and name of each document

You can use the same option to get hold of the relevancy score that Solr
has calculated for each document in the query:

::

 si.query("game").field_limit(score=True) # Return the score alongside each document
 si.query("game").field_limit("id", score=True") # return just the id and score.

The results appear just like the normal dictionary responses, but with a different
selection of fields.

::

 >>> for result in si.query("game").field_limit("id", score=True"):
 ...     print result

 {'score': 1.1931472000000001, 'id': u'0553573403'}
 {'score': 1.1931472000000001, 'id': u'0812550706'}

  

More complex queries
--------------------

Solr can index not only text fields but numbers, booleans and dates.
As of version 3.1, it can also index spatial points (though sunburnt
does not yet have support for spatial queries). This means you can
refine your textual searches by also querying on associated numbers,
booleans or dates

In our books example, there are two numerical fields - the ``price``
(which is a float) and ``sequence_i`` (which is an integer).
Numerical fields can be queried:

* exactly
* by comparison (``<`` / ``<=`` / ``>=`` / ``>``)
* by range (between two values)

Exact queries
.............

Don’t try and query floats exactly unless you really know what you’re doing (http://download.oracle.com/docs/cd/E19957-01/806-3568/ncg_goldberg.html). Solr will let you, but you almost certainly don’t want to. Querying integers exactly is fine though.

::

 si.query(sequence_i=1) # query for all books which are first in their sequence.

Comparison queries
..................

These use a new syntax:

::

 si.query(price__lt=7) # notice the double-underscore separating “price” from “lt”.

will search for all books whose price is less than 7 (dollars,
I guess - the example leaves currency unspecified!).  You can do similar searches
on any float or integer field, and you can use:

* ``gt`` : greater than, ``>``
* ``gte`` : greater than or equal to, ``>=``
* ``lt`` : less than, ``<``
* ``lte`` : less than or equal to, ``<=``


Range queries
.............

As an extension of a comparison query, you can query for values that are within a
range, ie between two different numbers.

::

 si.query(price__range=(5, 7)) # Search for all books with prices between $5 and $7.

This range query is *inclusive* - it will return prices of books which are priced at
exactly $5 or exactly $7. You can also make an *exclusive* search:

::

 si.query(price__rangeexc=(5, 7))

which will exclude books priced at exactly $5 or $7.

Finally, you can also do a completely open range search:

::

 si.query(price__any=True)

will search for a book which has *any* price. Why would you do this? Well, if
you had a schema where price was optional, then this search would return all
books which had a price - and exclude any books which didn’t have a price.


Date queries
............

You can query on dates the same way as you can query on numbers: exactly, by comparison,
or by range. The example books data doesn’t include any date fields, so we’ll look at
the example hardware data, which includes a ``manufacturedate_dt`` field.

Be warned, though, that exact searching on date suffers from similar problems to exact
searching on floating point numbers. Solr stores all dates to microsecond precision;
exact searching will fail unless the date requested is also correct to microsecond precision.

::

 si.query(manufacturedate_dt=datetime.datetime(2006, 02, 13))

will search for items whose manufacture date is *exactly* zero microseconds after
midnight on the 13th February, 2006.

More likely you’ll want to search by comparison or by range:

::

 # all items manufactured on or after the 1st January 2006
 si.query(manufacturedate_dt__gt=datetime.datetime(2006, 1, 1))

 # all items manufactured in Q1 2006.
 si.query(manufacturedate_dt__range=(datetime.datetime(2006, 1, 1), datetime.datetime(2006, 4, 1))

The argument to a date query can be any object that looks roughly like
a Python ``datetime`` object (so ``mx.DateTime`` objects will also work),
or a string in W3C Datetime notation (http://www.w3.org/TR/NOTE-datetime)

::

 si.query(manufacturedate_dt__gte="2006")
 si.query(manufacturedate_dt__lt="2009-04-13")
 si.query(manufacturedate_dt__range=("2010-03-04 00:34:21", "2011-02-17 09:21:44"))

All of the above queries will work as you expect - bearing in mind that solr will
still be working to microsecond precision. The first query above will return all
results later than, or on, exactly zero microseconds after midnight, 1st January, 2006.


Boolean fields
..............

Boolean fields are flags on a document. In the example hardware specs, documents
carry an ``inStock`` field. We can select on that by doing:

::

 si.query("Samsung", inStock=True) # all Samsung hardware which is in stock


Sorting results
---------------

Unless told otherwise, Solr will return results in “relevancy” order. How
Solr determines relevancy is a complex question, and can depend highly on
your specific setup. However, it’s possible to override this and sort query
results by another field. This field must be sortable, so most likely you’d
use a numerical or date field.

::

 si.query("game").sort_by("price") # Sort by ascending price
 si.query("game").sort_by("-price") # Sort by descending price (because of the minus sign)

You can also sort on multiple factors:

::

 si.query("game").sort_by("-price").sort_by("score")

This query will sort first by descending price, and then by increasing "score" (which is what solr calls relevancy).


Excluding results from queries
------------------------------

In the examples above, we’ve only considered narrowing our search with positive
requirements. What if we want to *exclude* results by some criteria?
Returning to the books data again, we can exclude all
Lloyd Alexander books by doing:

::

 si.exclude(author_t="Lloyd Alexander")

``exclude()`` methods chain in the same way as ``query()`` methodms, so you can mix and match:

::

 si.query(price__gt=7).exclude(author_t="Lloyd Alexander")
 # return all books costing more than $7, except for those authored by Lloyd Alexander.


.. _optional-terms:

Optional terms and combining queries
------------------------------------

Sunburnt queries can be chained together in all sorts of ways, with
query and exclude terms being applied. So far, you’ve only seen
examples which have compulsory terms, either positive (``query()``)
or negative(``exclude()``). What if you want to have *optional* terms?

The syntax for this is a little uglier. Let’s imagine we want books
which *either* have the word "game" *or* the word "black" in their titles.

What we do is construct two *query objects*, one for each condition, and ``OR`` them together.

::

 si.query(si.Q("game") | si.Q("black"))

The ``Q`` object can contain an arbitrary query, and can then be combined using
Boolean logic (here, using ``|``, the OR operator). The result can then be
passed to a normal ``si.query()`` call for execution.

``Q`` objects can be combined using any of the Boolean operators, so
also ``&`` (``AND``) and ``~`` (``NOT``), and can be nested within each
other. You’re unlikely to care about this unless you are constructing queries
programmatically, but it’s possible to express arbitrarily complex queries in this way.

A moderately complex query could be written:

::

 si.query(si.Q(si.Q("game") & ~si.Q(author_t="orson")) \
 | si.Q(si.Q("black" & ~si.Q(author_t="lloyd")))

which will return all results which fulfil the criteria:

* Either (books with "game" in the title which are not by authors called "orson")
* Or (books with "black" in the title which are not by authors called "lloyd")


Wildcard searching
------------------

Sometimes you want to search for partial matches for a word. Depending on how
your Solr schema does stemming, this may be done automatically for you. For
example, in the example schema, if you search for "parse", then documents
containing "parsing" will also be returned, because Solr will reduce both
the search term and the term in the document to their stem, which is "pars".

However, sometimes you need to do partial matches that Solr doesn’t know
about. You can use asterisks and question marks in the normal way, except
that you may not use leading wildcards - ie no wildcards at the beginning
of a term.

Using the books example again:

::

 si.query(name="thr*")

will search for all books which have a word beginning with “Thr” in their title. (So it will return "A Game of Thrones" and "The Book of Three").

::

 si.query(name="b*k")
 # will return "The Black Company", "The Book of Three" and "The Black Cauldron"

The results of a wildcard search are highly dependent on your Solr configuration, and in
particular depend on what text analysis it performs. You may find you need to lowercase
your search term even if the original document was mixed cased, because Solr has
lowercased the document before indexing it. (We have done this here).

If, for some reason, you want to search exactly for a string with an asterisk or a question mark in it then you need to tell Solr to special case it:

::

 si.query(id=RawString(“055323933?*”))

This will search for a document whose id contains *exactly* the string given,
including the question mark and asterisk. (Since there isn't one in our index,
that will return no results.)


Filter queries and caching
--------------------------

Solr implements several internal caching layers, and to some extent you can
control when and how they're used. (This is separate from the :ref:`http-caching` layer).

Often, you find that you can partition your query; one part is run many times
without change, or with very limited change, and another part varies much more.
(See http://wiki.apache.org/solr/FilterQueryGuidance for more guidance.)

You can get Solr to cache the infrequently-varying part of the query by use
of the FilterCache. For example, in the books case, you might provide standard
functionality to filter results by various price ranges: less than $7.50, or greater
than $7.50. This portion of your search will be run identically for nearly
every query, while the main textual part of the query varies lots.

If you separate out these two parts to the query, you can mark the price query
as being cacheable, by doing a *filter query* instead of a normal query for
that part of the search.

If you taking search input from the user, you would write:

::

 si.query(name=user_input).filter(price__lt=7.5)
 si.query(name=user_input).filter(price__gte=7.5)

The ``filter()`` method has the same functionality as the ``query()``
method, in terms of datatypes and query types. However, it also
tells Solr to separate out that part of the query and cache the
results. In this case, Solr will precompute the price portion of
the query and cache the results, so that as the user-driven queries
vary, Solr only has to perform in full the unique portion of the
query, the name query, and the price filter can be applied much more rapidly.

You can filter any sort of query, simply by using ``filter()`` instead
of ``query()``. And if your filtering involves an exclusion, then ``filter_exclude()``
has the same functionality as ``exclude()``.

::

 si.query(title="black").filter_exclude(author_t="lloyd")
 # Might be useful if a substantial portion of your users hate authors called “Lloyd”.

If it’s useful, you can mix and match ``query()`` and ``filter()`` calls as much as
you like while chaining. The resulting filter queries will be combined
and cached together.

::

 si.query(...).filter(...).exclude(...).filter_exclude(...)

and the argument to a ``filter()`` or ``filter_exclude()`` call can be a
Boolean combination of ``si.Q`` objects.


Query boosting
--------------

Solr provides a mechanism for "boosting" results according to the values
of various fields (See http://wiki.apache.org/solr/SolrRelevancyCookbook#Boosting_Ranking_Terms
for a full explanation). This is only useful where you're doing a search with optional terms,
and you want to specify that some of these terms are more important than others.

For example, imagine you are searching for books which either have "black" in the title, or
have an author named "lloyd". Let’s say that although either will do, you care more about
the author than the title. You can express this in sunburnt by raising a ``Q`` object to
a power equivalent to the boost you want.

::

 si.query(si.Q("black") | si.Q(author_t="lloyd")**3)

This boosts the importance of the author field by 3. The number is a fairly arbitrary
parameter, and it’s something of a black art to choose the relevant value.

A more common pattern is that you want all books with "black" in the title *and you have
a preference for those authored by Lloyd Alexander*. This is different from the last query;
the last query would return books by Lloyd Alexander which did not have "black" in the
title. Achieving this in solr is possible, but a little awkward; sunburnt provides a
shortcut for this pattern.

::

 si.query("black").boost_relevancy(3, author_t="lloyd")

This is fully chainable, and ``boost_relevancy`` can take an arbitrary
collection of query objects.


Faceting
--------

For background, see http://wiki.apache.org/solr/SimpleFacetParameters.

Sunburnt lets you apply faceting to any query, with the ``facet_by()`` method, chainable
on a query object. The ``facet_by()`` method needs, at least, a field (or list of fields) to
facet on:

::

 facet_query = si.query("game").facet_by("sequence_i").paginate(rows=0)

The above fragment will search for game with "thrones" in the title,
and facet the results according to the value of ``sequence_i``. It
will also return zero results, just the facet output.

::

 >>> print facet_query.execute().facet_counts.facet_fields

 {'sequence_i': [('1', 2), ('2', 0), ('3', 0)]}

The ``facet_counts`` objects contains several sets of results - here, we're only
interested in the ``facet_fields`` object. This contains a dictionary of results,
keyed by each field where faceting was requested. (In this case, we only requested
faceting on one field). The dictionary value is a list of two-tuples, mapping the 
value of the faceted field (in this case, ``sequence_i`` takes the values '1', '2', or '3')
to the numbers of results for each value.

You can read the above result as saying: 'of all the books which have "game" in their
title, 2 of them have ``sequence_i=1``, 0 of them have ``sequence_i=2``, and 0 of them have
``sequence_i=3``'.

You can facet on more than one field at a time:

:: 

 si.query(...).facet_by(fields=["field1", "field2, ...])

and the ``facet_fields`` dictionary will have more than one key.

Solr supports a number of parameters to the faceting operation. All of the basic options
are exposed through sunburnt:

::

 fields, prefix, sort, limit, offset, mincount, missing, method, enum.cache.minDf

All of these can be used as keyword arguments to the ``facet()`` call, except of course the
last one since it contains periods. To pass keyword arguments with periods in them, you
can use `**` syntax:

::

  facet(**{"enum.cache.minDf":25})

You can also facet on the result of one or more queries, using the ``facet_query()`` method. For example:

::

 >>> fquery = si.query("game").facet_query(price__lt=7).facet_query(price__gte=7)
 >>> print fquery.execute().facet_counts.facet_queries

 [('price:[7.0 TO *]', 1), ('price:{* TO 7.0}', 1)]

This will facet the results according to the two queries specified, so you can see
how many of the results cost less than $7, and how many cost more.

The results come back this time in the ``facet_queries`` object, but have the same form as before.
The facets are shown as a list of tuples, mapping query to number of results. You can read
the above as saying '*of the results, 1 of them fulfilled the first facet-query (price greater than 7) and
1 of them fulfilled the second query-facet (price less than 7)*'.

.. note:: Other types of facet

 Currently, faceting by date and range are not currently supported (but some of their functionality can be replicated by using ``facet_query()``). Nor are LocalParams or pivot faceting.


Highlighting
------------

For background, see http://wiki.apache.org/solr/HighlightingParameters.

Alongside the normal search results, you can ask solr to return fragments of
the documents, with relevant search terms highlighted. You do this with the
chainable ``highlight()`` method. By default this will highlight values in
the default search field. In our books example, the default search field is
a generated field, not returned in the results, so we’ll need to explicitly
specify which field we would like to see highlighted:

::

 >>> highlight_query = si.query("game").highlight("name")
 >>> print highlight_query.execute().highlighting

 {'0553573403': {'name': ['A <em>Game</em> of Thrones']},
  '0812550706': {'name': ["Ender's <em>Game</em>"]}}

The highlighting results live in the ``highlighting`` attribute on the SolrResponse object.
The results are shown as a dictionary of dictionaries. The top-level key is the ID
(or ``uniqueKey``) of each document returned. For each document, you then have a dictionary
mapping field names to fragments of highlighted text. In this case we only asked for
highlighting on the ``name`` field. Multiple fragments might be returned for each field,
though in this case we only get one fragment each. The text is highlighted with HTML, and
the fragments should be suitable for dropping straight into a search
template.

If you are using the default result format (that is, if you are not
specifying a ``constructor`` option when you call
:meth:`~sunburnt.search.SolrSearch.execute`), highlighting results for
a single result can be accessed on the individual result item as a
dictionary in a ``solr_highlights`` field.  For example, with the
highlighted query above, you could access highlight snippets for the
``name`` field on an individual result as
``result['solr_highlights']['name']``.  This is particularly
convenient for displaying highlighted text snippets in a template;
e.g., displaying highlights in a Django template might look like this:

::
    
  {% for snippet in book.solr_highlights.name %}
     <p>... {{ snippet|safe }} ...</p>
  {% endfor %}

.. Note::

  The ``solr_highlights`` field will only be available on a result
  item if highlights were found for that record.


Again, Solr supports a large number of options to the highlighting command,
and all of these are exposed through sunburnt. The full list of supported options is:

::

 fields, snippets, fragsize, mergeContinuous, requireFieldMatch, maxAnalyzedChars,
 alternateField, maxAlternateFieldLength, formatter, simple.pre.simple.post,
 fragmenter, usePhrasehighlighter, hilightMultiTerm, regex.slop, regex.pattern,
 regex.maxAnalyzedChars            

See the note above in `Faceting`_ about using keyword arguments with periods.

.. _standard-query-more-like-this:

More Like This
--------------

For background, see http://wiki.apache.org/solr/MoreLikeThis. Alongside a set of
search results, Solr can suggest other documents that
are similar to each of the documents in the search result.

.. note:: Query handlers

 Sunburnt only supports ``MoreLikeThis`` through the ``StandardQueryHandler``,
 not through the separate ``MoreLikeThisHandler``. That is, it only supports
 more-like-this searches on documents that are already in its index.

More-like-this searches are accomplished with the ``mlt()`` chainable
option. Solr needs to know which fields to consider when deciding similarity;
if you don't make any choice, then the default field (specified by ``schema.xml``)
will be used.

::

 >>> mlt_query = si.query(id="0553573403").mlt("name", mintd=1, mindf=1)
 >>> mlt_results = mlt_query.execute().more_like_these
 >>> print mlt_results

 {'0553573403': <sunburnt.schema.SolrResult object at 0x4b10510>}

 >>> print mlt_results['0553573403'].docs

 [{'author_t': u'Orson Scott Card',
   'cat': (u'book',),
   'genre_s': u'scifi',
   'id': u'0812550706',
   'inStock': True,
   'name': u"Ender's Game",
   'price': 6.9900000000000002,
   'sequence_i': 1,
   'series_t': u'Ender'}]

Here we used ``mlt()`` options to alter the default behaviour (because our
corpus is so small that Solr wouldn't find any similar documents with the
standard behaviour.

The ``SolrResponse`` object has a ``more_like_these`` attribute. This is
a dictionary of ``SolrResult`` objects, one dictionary entry for each
result of the main query. Here, the query only produced one result (because
we searched on the ``uniqueKey``. Inspecting the ``SolrResult`` object, we 
find that it contains only one document.

We can read the above result as saying that under the ``mlt()`` parameters
requested, there was only one document similar to the search result.

In this case, only one document was returned by the original query, In this
case, there is a shortcut attribute: ``more_like_this`` instead of
``more_like_these``.

::

 >>> print mlt_query.execute().more_like_this.docs

 [{'author_t': u'Orson Scott Card',
   ...

to avoid having to do the extra dictionary lookup.

``mlt()`` also takes a list of options (see the Solr documentation for a full explanation);

::

 fields, count, mintf, mindf, minwl, mawl, maxqt, maxntp, boost


Spatial fields
--------------

From version 3.1 of Solr, spatial field-types are supported in the schema. This means
you can have fields on a document representing (latitude, longitude) pairs.
(Indeed, you can have fields representing points in an arbitrary number of dimensions.)

Although sunburnt deals correctly storage and retrieval of such fields, currently
no querying is supported beyond exact matching (including spatial querying).

sunburnt expects spatial fields to be supplied as iterables of length
two, and will always return them as two-tuples.


Binary fields
-------------

From version 3.1 of Solr, fields for binary data are supported in the schema. In
Solr these are stored as base64-encoded blobs, but as a sunburnt user you don’t
have to care about this. Sunburnt will automatically transcode to and from base64
as appropriate, and your results will contain a binary string where appropriate.
(Querying on Binary Fields is not supported, and doesn’t make much sense anyway).

UUID fields
-----------

From version 1.4 of Solr, fields for UUIDs are supported in the schema (see http://wiki.apache.org/solr/UniqueKey).
When retrieving results, Solr will automatically translate any UUID fields into
python UUID objects (see http://docs.python.org/library/uuid.html). When inserting documents, sunburnt will accept values
which are either UUID objects or UUID strings; or the string "NEW", to indicate that
a UUID should be created on ingestion.
