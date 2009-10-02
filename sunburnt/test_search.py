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


class TestTermsAndQueries(object):
    def setUp(self):
        self.solr_search = SolrSearch(interface)

    def test_nothing(self):
        assert not self.solr_search.query_obj \
            and not self.solr_search.filter_obj

    def test_query_by_term(self):
        self.solr_search.query_by_term(None, "hello")
        assert self.solr_search.execute() == {"q":u"hello"}

    def test_query_by_phrase(self):
        self.solr_search.query_by_phrase(None, "hello world")
        assert self.solr_search.execute() == {"q":u"\"hello world\""}

    def test_filter_by_term(self):
        self.solr_search.filter_by_term(None, "hello")
        assert self.solr_search.execute() == {"qf":u"hello"}

    def test_filter_by_phrase(self):
        self.solr_search.filter_by_phrase(None, "hello world")
        assert self.solr_search.execute() == {"qf":u"\"hello world\""}
