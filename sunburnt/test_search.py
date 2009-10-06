from __future__ import absolute_import

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import datetime
import mx.DateTime

from .schema import SolrSchema, SolrError
from .search import SolrSearch, PaginateOptions, FacetOptions

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

schema = SolrSchema(StringIO(schema_string))

class MockInterface(object):
    schema = schema
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
        ([], {"boolean_field":"false"},
         {"q":u"boolean_field:true"}), # boolean field takes any truth-y value
        ([], {"boolean_field":0},
         {"q":u"boolean_field:false"}),
        ([], {"int_field":3},
         {"q":u"int_field:3"}),
        ([], {"int_field":3.1}, # casting from float should work
         {"q":u"int_field:3"}),
        ([], {"sint_field":3},
         {"q":u"sint_field:3"}),
        ([], {"sint_field":3.1}, # casting from float should work
         {"q":u"sint_field:3"}),
        ([], {"long_field":2**31},
         {"q":u"long_field:2147483648"}),
        ([], {"slong_field":2**31},
         {"q":u"slong_field:2147483648"}),
        ([], {"float_field":3.0},
         {"q":u"float_field:3.0"}),
        ([], {"float_field":3}, # casting from int should work
         {"q":u"float_field:3.0"}),
        ([], {"sfloat_field":3.0},
         {"q":u"sfloat_field:3.0"}),
        ([], {"sfloat_field":3}, # casting from int should work
         {"q":u"sfloat_field:3.0"}),
        ([], {"double_field":3.0},
         {"q":u"double_field:3.0"}),
        ([], {"double_field":3}, # casting from int should work
         {"q":u"double_field:3.0"}),
        ([], {"sdouble_field":3.0},
         {"q":u"sdouble_field:3.0"}),
        ([], {"sdouble_field":3}, # casting from int should work
         {"q":u"sdouble_field:3.0"}),
        ([], {"date_field":datetime.datetime(2009, 1, 1)},
         {"q":u"date_field:2009-01-01T00:00:00.000000Z"}),
        ([], {"date_field":mx.DateTime.DateTime(2009, 1, 1)},
         {"q":u"date_field:2009-01-01T00:00:00.000000Z"}),
        ),
    }

def check_query_data(method, args, kwargs, output):
    solr_search = SolrSearch(interface)
    assert getattr(solr_search, method)(*args, **kwargs).execute() == output

def test_query_data():
    for method, data in good_query_data.items():
        for args, kwargs, output in data:
            yield check_query_data, method, args, kwargs, output

bad_query_data = (
    {"int_field":"a"},
    {"int_field":2**31},
    {"int_field":-(2**31)-1},
    {"long_field":"a"},
    {"long_field":2**63},
    {"long_field":-(2**63)-1},
    {"float_field":"a"},
    {"float_field":2**1000},
    {"float_field":-(2**1000)},
    {"double_field":"a"},
    {"double_field":2**2000},
    {"double_field":-(2**2000)},
)

def check_bad_query_data(kwargs):
    solr_search = SolrSearch(interface)
    try:
        solr_search.query(**kwargs).execute()
    except SolrError:
        pass
    else:
        assert False

def test_bad_query_data():
    for kwargs in bad_query_data:
        yield check_bad_query_data, kwargs


good_paginator_data = (
    ({"start":5, "rows":10},
     {"start":5, "rows":10}),
    ({"start":5, "rows":None},
     {"start":5}),
    ({"start":None, "rows":10},
     {"rows":10}),
)

def check_paginator_data(kwargs, output):
    paginate = PaginateOptions(schema)
    paginate.update(**kwargs)
    assert paginate.options == output

def test_paginator_data():
    for kwargs, output in good_paginator_data:
        yield check_paginator_data, kwargs, output


bad_paginator_data = (
    {"start":-1, "rows":None}, # negative start
    {"start":None, "rows":-1}, # negative rows
)

def check_bad_paginator_data(kwargs):
    paginate = PaginateOptions(schema)
    try:
        paginate.update(**kwargs)
    except SolrError:
        pass
    else:
        assert False

def test_bad_paginator_data():
    for kwargs in bad_paginator_data:
        yield check_bad_paginator_data, kwargs


good_faceter_data = (
    ({"fields":"int_field"},
     {"facet":True, "facet.field":["int_field"]}),
    ({"fields":["int_field", "text_field"]},
     {"facet":True, "facet.field":["int_field","text_field"]}),
    ({"prefix":"abc"},
     {"facet":True, "facet.prefix":"abc"}),
    ({"prefix":"abc", "sort":True, "limit":3, "offset":25, "mincount":1, "missing":False, "method":"enum"},
     {"facet":True, "facet.prefix":"abc", "facet.sort":True, "facet.limit":3, "facet.offset":25, "facet.mincount":1, "facet.missing":False, "facet.method":"enum"}),
)

def check_faceter_data(kwargs, output):
    faceter = FacetOptions(schema)
    faceter.update(**kwargs)
    assert faceter.options == output

def test_faceter_data():
    for kwargs, output in good_faceter_data:
        yield check_faceter_data, kwargs, output


bad_faceter_data = (
    {"fields":"myarse"}, # Undefined field
)

def check_bad_faceter_data(kwargs):
    faceter = FacetOptions(schema)
    try:
        faceter.update(**kwargs)
    except SolrError:
        pass
    else:
        assert False

def test_bad_faceter_data():
    for kwargs in bad_faceter_data:
        yield check_bad_faceter_data, kwargs

