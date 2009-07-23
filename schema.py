from __future__ import absolute_import

import datetime
import math
import operator

import lxml.builder
import lxml.etree
import pytz


E = lxml.builder.ElementMaker()
ADD = E.add
DOC = E.doc
FIELD = E.field


class SolrError(Exception):
    pass


class solr_date(object):
    """This class can be initialized from either native python datetime
    objects and mx.DateTime objects, and will serialize to a format
    appropriate for Solr"""
    def __init__(self, v):
        if isinstance(v, basestring):
            self.from_str(v)
        else:
            self.from_date(v)

    def from_date(self, v):
        # Python datetime objects may include timezone information
        if hasattr(v, 'tzinfo') and v.tzinfo:
            # but Solr requires UTC times.
            self.v = v.astimezone(pytz.utc)
        else:
            self.v = v
        if hasattr(self.v, "microsecond"):
            self.microsecond = str(self.v.microsecond)
        else:
            self.microsecond = str(math.modf(self.v.second)[0])[1:]

    def from_str(self, s):
        self.v = datetime.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        self.v.replace(microsecond=1000000*float(s[19:-1]))

    def __repr__(self):
        return repr(self.v)

    def __str__(self):
        """ Serialize a datetime object in the format required
        by Solr. See http://wiki.apache.org/solr/IndexingDates
        """
        return "%s.%sZ" % (self.v.strftime("%Y-%m-%dT%H:%M:%S"),
                           self.microsecond)


class SolrSchema(object):
    solr_data_types = {
        'solr.StrField':str,
        'solr.TextField':str,
        'solr.BoolField':bool,
        'solr.IntField':int,
        'solr.SortableIntField':int,
        'solr.LongField':long,
        'solr.SortableLongField':long,
        'solr.FloatField':float,
        'solr.SortableFloatField':float,
        'solr.DoubleField':float,
        'solr.SortableDoubleField':float,
        'solr.DateField':solr_date
        }

    def __init__(self, f):
        """initialize a schema object from a
        filename or file-like object."""
        self.fields = self.schema_parse(f)

    def schema_parse(self, f):
        schemadoc = lxml.etree.parse(f)
        field_types = {}
        for data_type, t in self.solr_data_types.items():
            for field_type in schemadoc.xpath("/schema/types/fieldType[@class='%s']/@name" % data_type):
                field_types[field_type] = t
        return dict((field.attrib['name'],
                     field_types.get(field.attrib['type'], 'UNKNOWN'))
                    for field in schemadoc.xpath("/schema/fields/field"))

    def serialize_value(self, k, v):
        try:
            return str(self.fields[k](v))
        except KeyError:
            raise SolrError("No such field '%s' in current schema" % k)

    def deserialize_value(self, k, v):
        try:
            return self.fields[k](v)
        except KeyError:
            raise SolrError("No such field '%s' in current schema" % k)

    def deserialize_values(self, name, values):
        if hasattr(values, "__iter__"):
            return [self.deserialize_value(name, value) for value in values]
        return self.deserialize_value(name, values)

    def make_update_fields(self, name, values):
        if not hasattr(values, "__iter__"):
            values = [values]
        return [FIELD({'name':name}, self.serialize_value(name, value))
                for value in values]

    def make_update_doc(self, doc):
        if not doc:
            return DOC()
        else:
            return DOC(*reduce(operator.add,
                               [self.make_update_fields(name, values)
                                for name, values in doc.items()]))

    def make_update_message(self, docs):
        if hasattr(docs, "items"):
            docs = [docs]
        message_xml = ADD(*[self.make_update_doc(doc) for doc in docs])
        return lxml.etree.tostring(message_xml, encoding='utf-8')


class SolrResults(object):
    response_items = ("numFound", "start", "docs", "facet_counts", "highlighting")
    def __init__(self, schema, d):
        self.schema = schema
        if isinstance(d, basestring):
            self.d = simplejson.loads(d)
        else:
            self.d = d
        if self.d["responseHeader"]["status"] != 0:
            raise ValueError("Response indicates an error")
        for attr in self.response_items:
            try:
                setattr(self, attr, self.d["response"][attr])
            except KeyError:
                pass
        self.docs = [self.deserialize_fields(doc)
                     for doc in d["response"]["docs"]]

    def deserialize_fields(self, doc):
        return dict((k, self.schema.deserialize_values(k, v))
                    for k, v in doc.items())

    def __str__(self):
        return "%(numFound)s results found, starting at #%(start)s\n\n" % self.__dict__ + str(self.docs)
