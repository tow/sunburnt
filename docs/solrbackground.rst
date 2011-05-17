.. _Solrbackground:

Reading a Solr Schema
=====================

This is not the place for a full description of a Solr schema,
but you need to understand certain concepts to use sunburnt.

For a better understanding of what’s going on, start with
http://wiki.apache.org/Solr/SchemaXml and http://wiki.apache.org/solr/SchemaDesign.

The examples in this documentation can be run against the example
data and schema, though you will need to understand the concepts
below.

You can find the example schema at "``$SOLR_SOURCE_DIR/example/solr/conf/schema.xml``".

* documents

 A Solr index lets you search over multiple documents. Each document is composed
 of multiple fields, each field having a fieldtype. The list of available fieldtypes
 and fields defines what a document is for your purposes, and this is specified
 in the Solr ``schema.xml``.

* fieldtypes

 A schema will define several fieldtypes, which for sunburnt's purposes
 are roughly equivalent to data types - you can have booleans,
 numbers (of various precisions), dates, and strings. (As of Solr 3.1, you can also have geographical 
 points and blobs). An important distinction should be made between

 - *strings*, which need not contain human-readable words, and where
   searching will mostly be exact; and

 - *text*, which largely will contain human-readable words, and where
   searching will usually be fuzzier.

 Most of Solr’s cleverness is in making sense of text fields.

* fields

 A document schema consists of defining a number of fields, each of
 which has a name, a fieldtype, plus several options. In contrast to a
 traditional RDBMS schema, most fields in a document schema will be
 optional. Fields also may be *indexed* (ie, you can query on their
 contents) and/or *stored* (ie, when a document is returned from a
 search, a stored field will be part of the result). Fields can be
 any combination of these - eg you can have stored fields that aren’t
 queryable, or queryable fields which won’t be returned in the result.

 Although the latter seems pointless, it’s very often used because
 you can have generated fields; fields that don’t exist in the
 original documents, but are useful for querying. Often you might
 have a default text field, composed of the title, subtitle, and
 contents of a document. You want to search on the combined field,
 but you don’t want to return it in the results - results should
 only have the fields available on the original document.

 - *multivalued*

   Fields can also be *multivalued*. A common pattern might be giving
   tags to a document. One document can have many tags, so the tags
   field is multivalued. When you query on tags, all the tags will be
   searched, and when the document is returned, all the tags will be in the result.

 - *default*

   A schema will usually define a *default* field for the document. This is the
   field which will be searched on if no other field is specified.

 - *uniqueKey*

   A schema will also usually define a *uniqueKey* - this acts as an ID
   field for the document. If this is defined, then every document in
   the index must have a unique value for this field.

 - *dynamic*

   A schema can define *dynamic* fields. These don't have a set name,
   instead they are called, for example "``\*_i``". This means that when
   Solr encounters a document which has any field ending in "``_i``", it
   will use the fieldtype associated with the "``\*_i``" field.
