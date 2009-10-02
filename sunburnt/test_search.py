from __future__ import absolute_import

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from .schema import SolrSchema
from .search import SolrSearch

schema_string = \
"""<schema name="timetric" version="1.1">
  <types>
    <fieldType name="string" class="solr.StrField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="text" class="solr.TextField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="boolean" class="solr.BoolField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="int" class="solr.IntField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="sint" class="solr.SortableIntField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="long" class="solr.LongField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="slong" class="solr.SortableLongField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="float" class="solr.FloatField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="sfloat" class="solr.SortableFloatField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="double" class="solr.DoubleField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="sdouble" class="solr.SortableDoubleField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="date" class="solr.DateField" sortMissingLast="true" omitNorms="true"/>
  </types>
  <fields>
    <field name="string_field" required="true" type="string"/>
    <field name="text_field" required="true" type="text"/>
    <field name="boolean_field" required="false" type="boolean"/>
    <field name="int_field" required="true" type="int"/>
    <field name="sint_field" type="sint"/>
    <field name="long_field" type="long"/>
    <field name="slong_field" type="slong"/>
    <field name="long_field" type="long"/>
    <field name="slong_field" type="slong"/>
    <field name="float_field" type="float"/>
    <field name="sfloat_field" type="sfloat"/>
    <field name="double_field" type="double"/>
    <field name="sdouble_field" type="sdouble"/>
    <field name="date_field" type="date"/>
  </fields>
  <defaultSearchField>text_field</defaultSearchField>
  <uniqueKey>int_field</uniqueKey>
</schema>"""


class MockInterface(object):
    schema = SolrSchema(StringIO(schema_string))
    def search(self, **kwargs):
        return kwargs


interface = MockInterface()


good_query_data = {
    "query_by_term":(
        (["hello"], {},
         {"q":u"hello"}),
        (["hello"], {"int_field":3},
         {"q":u"hello int_field:3"}),
        (["hello", "world"], {},
         {"q":u"hello world"}),
        # NB this next is not really what we want,
        # probably this should warn
        (["hello world"], {},
         {"q":u"hello world"}),
        ),

    "query_by_phrase":(
        (["hello"], {},
         # Do we actually want this many quotes in here?
         {"q":u"\"hello\""}),
        (["hello"], {"int_field":3},
         {"q":u"int_field:3 \"hello\""}), # Non-text data is always taken to be a term, and terms come before phrases, so order is reversed
        (["hello", "world"], {},
         {"q":u"\"hello\" \"world\""}),
        (["hello world"], {},
         {"q":u"\"hello world\""}),
        ),

    "filter_by_term":(
        (["hello"], {},
         {"fq":u"hello"}),
        (["hello"], {"int_field":3},
         {"fq":u"hello int_field:3"}),
        (["hello", "world"], {},
         {"fq":u"hello world"}),
        # NB this next is not really what we want,
        # probably this should warn
        (["hello world"], {},
         {"fq":u"hello world"}),
        ),

    "filter_by_phrase":(
        (["hello"], {},
         # Do we actually want this many quotes in here?
         {"fq":u"\"hello\""}),
        (["hello"], {"int_field":3},
         {"fq":u"int_field:3 \"hello\""}),
        (["hello", "world"], {},
         {"fq":u"\"hello\" \"world\""}),
        (["hello world"], {},
         {"fq":u"\"hello world\""}),
        ),

    "query":(
        (["hello"], {},
         {"q":u"hello"}),
        (["hello"], {"int_field":3},
         {"q":u"hello int_field:3"}),
        (["hello", "world"], {},
         {"q":u"hello world"}),
        (["hello world"], {},
         {"q":u"\"hello world\""}),
        ),

    "filter":(
        (["hello"], {},
         {"fq":u"hello"}),
        (["hello"], {"int_field":3},
         {"fq":u"hello int_field:3"}),
        (["hello", "world"], {},
         {"fq":u"hello world"}),
        (["hello world"], {},
         {"fq":u"\"hello world\""}),
        ),

    "query":(
        ([], {"boolean_field":True},
         {"q":u"boolean_field:true"}),
        ([], {"sint_field":3},
         {"q":u"sint_field:3"}),
        ([], {"long_field":2**31},
         {"q":u"long_field:2147483648"}),
        ([], {"slong_field":2**31},
         {"q":u"slong_field:2147483648"}),
        ),


    }

def check_query_data(method, args, kwargs, output):
    solr_search = SolrSearch(interface)
    print getattr(solr_search, method)(*args, **kwargs).execute(), output
    assert getattr(solr_search, method)(*args, **kwargs).execute() == output

def test_query_data():
    for method, data in good_query_data.items():
        for args, kwargs, output in data:
            yield check_query_data, method, args, kwargs, output
