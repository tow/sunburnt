.. _connectionconfiguration:

Configuring a connection
========================

Whether you're querying or updating a solr server, you need to set up a
connection to the solr server. Pass the URL of the solr server to a
SolrInterface object.

::

 solr_interface = sunburnt.SolrInterface("http://localhost:8983/solr/")

If you are using `a multicore setup
<http://wiki.apache.org/solr/CoreAdmin>` (which is strongly recommended,
even if you only use a single core), then you need to pass the full URL
to the core in question.

::

 solr_interface = sunburnt.SolrInterface("http://localhost:8983/solr/master/")

The SolrInterface object can take three additional optional
parameters. 

* ``schemadoc``. By default, sunburnt will query the solr instance for its
  currently active schema. If you want to use a different schema for
  any reason, pass in a file object here which yields a schema
  document.
 
  In querying the current active schema, sunburnt will automatically
  understand the available fields and their respective types.  Sunburnt
  has a variety of field helpers that automatically serialize and
  deserialize data types behind the scenes (such as when querying Solr
  and parsing a response).  For instance, this means that if you have a
  field ``quantity`` in your schema with type ``solr.IntField``, Sunburnt
  is aware that values of this field are integers. So, values going to Solr
  in a query will get serialized into an appropriate string, and those coming
  back as strings will be deserialized as ``int`` values.

  Most built-in Solr field types (in the ``solr.*`` namespace) are understood,
  including:

  ========================  ===========
  Field Type                Python Type
  ========================  ===========
  solr.StrField             unicode
  solr.TextField            unicode
  solr.BoolField            bool
  solr.ShortField           int (-32768 to 32767)
  solr.IntField             int
  solr.SortableIntField     int
  solr.TrieIntField         int
  solr.LongField            long
  solr.SortableLongField    long
  solr.TrieLongField        long
  solr.FloatField           float
  solr.SortableFloatField   float
  solr.TrieFloatField       float
  solr.DoubleField          float
  solr.SortableDoubleField  float
  solr.TrieDoubleField      float
  solr.DateField            datetime (or mx.DateTime)
  solr.TrieDateField        datetime (or mx.DateTime)
  solr.RandomSortField      str (default handling)
  solr.UUIDField            uuid.UUID
  solr.BinaryField          unicode (base64 decoded)
  solr.PointType            solr_point (1 dimension)
  solr.LatLonType           solr_point (2 dimensions)
  solr.GeoHashField         solr_point (2 dimensions)
  ========================  =========== 

  If you are using a custom field type that Sunburnt does not
  natively understand, values will be treated as strings.

* ``http_connection``. By default, solr will open a new http connection object
  to talk to the solr instance (either a ``requests.Session`` or
  ``httplib2.Http`` instance depnding on which library is installed). If you
  want to re-use an existing connection, or set up your own Http object with
  different options, etc, then you can pass in your own ``http_connection``
  object (see :ref:`http-caching`)

* ``mode``. A common solr configuration is to use different cores for
  writing or reading - they have very different performance
  characteristics. You can enforce this through sunburnt by setting
  mode='r' or mode='w'. In either case, sunburnt will throw an
  exception if you later try to perform the wrong sort of operation on
  the interface, ie trying to update the index on a read-only core, or
  trying to run queries on a write-only core. By default, all
  ``SolrInterface`` objects will be opened read/write.

* ``retry_timeout``. By default, if sunburnt fails to connect to the Solr
  server, it will fail, throwing a ``sunburnt.http.ConnectionError``. If you
  specify ``retry_timeout`` (as a positive number) then when sunburnt
  encounters a failure, it will wait ``retry_timeout`` seconds before retrying.
  It will only retry once, and then throw the same ``ConnectionError``
  exception if it fails again. This is useful in case you’re in a context where
  access to the Solr server might occasionally and briefly disappear, but you
  don’t want any processes which talk to Solr to fail. For example, if you are
  in control of the Solr server, and want to restart it to reload its
  configuration.
 
.. _http-caching:

HTTP caching
------------

It's generally a sensible idea to not use the default ``http_connection``,
which doesn't do any caching. If you're likely to find your program
making the same requests more than once (because perhaps your users
make the same common searches), then you should use a caching http
connection. Solr does very good internal caching of search results, but
also supports proper HTTP-level caching, and you'll get much better performance
by taking advantage of that.

If you are using ``httplib2`` you can set up your interface object
like so:

::

 solr_url = "http://localhost:8983/solr"
 h = httplib2.Http(cache="/var/tmp/solr_cache")
 solr_interface = SolrInterface(url=solr_url, http_connection=h)


If you are using ``requests`` you will need to use a third-party library to add
caching support e.g. `CacheControl <http://cachecontrol.readthedocs.org/>`_


Schema migrations
-----------------

Sometimes it's necessary to make changes to your Solr schema. You may
want to add new fields, or change the configuration of existing
fields.

There are various ways to approach this. One of the most transparent
ways is to duplicate an existing core, update its schema offline, and
then use Solr's multicore commands to change which core
is exposed. This can be done entirely transparently to any clients
which are currently connected.

However, the SolrInterface object is set up with a single schema when
it's initialized (whether by reading the schema from the Solr
instance, or by the schema being passed in as a parameter). If the
core is changed to have a different schema, the SolrInterface object
will not reflect this change until you tell it to re-read the schema:

::

  si = SolrInterface(solr_server)
  # Elsewhere, restart solr with a different schema
  si.init_schema()
