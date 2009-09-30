from __future__ import absolute_import

import cStringIO as StringIO
import datetime

import mx.DateTime
import pytz

from .schema import solr_date, SolrSchema

not_utc = pytz.timezone('Etc/GMT-3')

samples_from_pydatetimes = {
    "2009-07-23T03:24:34.000376Z":
        [datetime.datetime(2009, 07, 23, 3, 24, 34, 376),
         datetime.datetime(2009, 07, 23, 3, 24, 34, 376, pytz.utc)],
    "2009-07-23T00:24:34.000376Z":
        [not_utc.localize(datetime.datetime(2009, 07, 23, 3, 24, 34, 376)),
         datetime.datetime(2009, 07, 23, 0, 24, 34, 376, pytz.utc)],
    "2009-07-23T03:24:34.000000Z":
        [datetime.datetime(2009, 07, 23, 3, 24, 34),
         datetime.datetime(2009, 07, 23, 3, 24, 34, tzinfo=pytz.utc)],
    "2009-07-23T00:24:34.000000Z":
        [not_utc.localize(datetime.datetime(2009, 07, 23, 3, 24, 34)),
         datetime.datetime(2009, 07, 23, 0, 24, 34, tzinfo=pytz.utc)]
    }

samples_from_mxdatetimes = {
    "2009-07-23T03:24:34.000376Z":
        [mx.DateTime.DateTime(2009, 07, 23, 3, 24, 34.000376),
         datetime.datetime(2009, 07, 23, 3, 24, 34, 376, pytz.utc)],
    "2009-07-23T03:24:34.000000Z":
        [mx.DateTime.DateTime(2009, 07, 23, 3, 24, 34),
         datetime.datetime(2009, 07, 23, 3, 24, 34, tzinfo=pytz.utc)],
    }


samples_from_strings = {
    # These will not have been serialized by us, but we should deal with them
    "2009-07-23T03:24:34Z":
        datetime.datetime(2009, 07, 23, 3, 24, 34, tzinfo=pytz.utc),
    "2009-07-23T03:24:34.1Z":
        datetime.datetime(2009, 07, 23, 3, 24, 34, 100000, pytz.utc),
    "2009-07-23T03:24:34.123Z":
        datetime.datetime(2009, 07, 23, 3, 24, 34, 123000, pytz.utc)
    }

def check_solr_date_from_date(s, date, canonical_date):
    assert str(solr_date(date)) == s
    check_solr_date_from_string(s, canonical_date)

def check_solr_date_from_string(s, date):
    assert solr_date(s).v == date


def test_solr_date_from_pydatetimes():
    for k, v in samples_from_pydatetimes.items():
        yield check_solr_date_from_date, k, v[0], v[1]

def test_solr_date_from_mxdatetimes():
    for k, v in samples_from_mxdatetimes.items():
        yield check_solr_date_from_date, k, v[0], v[1]

def test_solr_date_from_strings():
    for k, v in samples_from_strings.items():
        yield check_solr_date_from_string, k, v


schema = \
"""
<schema name="timetric" version="1.1">
  <types>
    <fieldType name="sint" class="solr.SortableIntField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="string" class="solr.StrField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="boolean" class="solr.BoolField" sortMissingLast="true" omitNorms="true"/>
  </types>
  <fields>
    <field name="int_field" required="true" type="sint"/>
    <field name="text_field" required="true" type="string"/>
    <field name="boolean_field" required="false" type="boolean"/>
  </fields>
  <defaultSearchField>text_field</defaultSearchField>
  <uniqueKey>int_field</uniqueKey>
 </schema>
"""

class TestReadingSchema(object):
    def setUp(self):
        self.schema = StringIO.StringIO(schema)

    def test_read_schema(self):
        """ Test that we can read in a schema correctly,
        that we get the right set of fields, the right
        default field, and the right unique key"""
        s = SolrSchema(self.schema)
        assert sorted(s.fields.keys()) == ['boolean_field', 'int_field', 'text_field']
        assert s.default_field == 'text_field'
        assert s.unique_key == 'int_field'

    def test_serialize_dict(self):
        """ Test that each of the fields will serialize the relevant
        datatype appropriately."""
        s = SolrSchema(self.schema)
        for k, v, v2 in (('int_field', 1, u'1'),
                         ('text_field', 'text', u'text'),
                         ('text_field', u'text', u'text'),
                         ('boolean_field', True, u'true')):
                             assert s.serialize_value(k, v) == v2
