from __future__ import absolute_import

import datetime
import math
import operator
import warnings

import lxml.builder
import lxml.etree
import simplejson

try:
    import pytz
except ImportError:
    warnings.warn(
        "pytz not found; cannot do timezone conversions for Solr DateFields",
        ImportWarning)
    pytz = None


E = lxml.builder.ElementMaker()


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
            if pytz:
                self.v = v.astimezone(pytz.utc)
            else:
                raise EnvironmentError("pytz not available, cannot do timezone conversions")
        else:
            self.v = v
        if hasattr(self.v, "microsecond"):
            self.microsecond = self.v.microsecond
        else:
            self.microsecond = int(1000000*math.modf(self.v.second)[0])

    def from_str(self, s):
        self.v = datetime.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        if pytz:
            self.v = pytz.utc.localize(self.v)
        microsecond_string = s[19:-1]
        if microsecond_string:
            self.v = self.v.replace(microsecond=int(1000000*float(s[19:-1])))

    def __repr__(self):
        return repr(self.v)

    def __str__(self):
        """ Serialize a datetime object in the format required
        by Solr. See http://wiki.apache.org/solr/IndexingDates
        """
        return "%s.%sZ" % (self.v.strftime("%Y-%m-%dT%H:%M:%S"),
                           "%06d" % self.microsecond)


class SolrField(object):
    def __init__(self, node, data_type):
        self.name = node.attrib["name"]
        self.multi_valued = node.attrib.get("multiValued") == "true"
        self.type = data_type


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
        fields = {}
        for field in schemadoc.xpath("/schema/fields/field"):
            name = field.attrib['name']
            data_type = field_types[field.attrib['type']]
            fields[name] = SolrField(field, data_type)
        return fields

    def serialize_value(self, k, v):
        try:
            return str(self.fields[k].type(v))
        except KeyError:
            raise SolrError("No such field '%s' in current schema" % k)

    def serialize_values(self, k, values):
        if not k in self.fields:
            raise SolrError("No such field '%s' in current schema" % k)
        if not self.fields[k].multi_valued:
            raise SolrError("'%s' is not a multi-valued field" % k)
        return [self.serialize_value(k, value) for value in values]

    def deserialize_value(self, k, v):
        try:
            return self.fields[k].type(v)
        except KeyError:
            raise SolrError("No such field '%s' in current schema" % k)

    def deserialize_values(self, name, values):
        if self.fields[name].multi_valued:
            return [self.deserialize_value(name, value) for value in values]
        return self.deserialize_value(name, values)

    def make_update(self, docs):
        return SolrUpdate(self, docs)

    def parse_results(self, msg):
        return SolrResults(self, msg)


class SolrUpdate(object):
    ADD = E.add
    DOC = E.doc
    FIELD = E.field

    def __init__(self, schema, docs):
        self.schema = schema
        self.xml = self.add(docs)

    def fields(self, name, values):
        if hasattr(values, "__iter__"):
            return [self.FIELD({'name':name}, value)
                    for value in self.schema.serialize_values(name, values)]
        else:
            return [self.FIELD({'name':name},
                           self.schema.serialize_value(name, values))]

    def doc(self, doc):
        if not doc:
            return self.DOC()
        else:
            return self.DOC(*reduce(operator.add,
                                    [self.fields(name, values)
                                     for name, values in doc.items()]))

    def add(self, docs):
        if hasattr(docs, "items"):
            docs = [docs]
        return self.ADD(*[self.doc(doc) for doc in docs])

    def __str__(self):
        return lxml.etree.tostring(self.xml, encoding='utf-8')


class SolrResults(object):
    response_items = ("numFound", "start", "docs", "facet_counts", "highlighting")
    def __init__(self, schema, msg):
        self.schema = schema
        self.d = simplejson.loads(msg)
        if self.d["responseHeader"]["status"] != 0:
            raise ValueError("Response indicates an error")
        for attr in self.response_items:
            try:
                setattr(self, attr, self.d["response"][attr])
            except KeyError:
                pass
        self.docs = [self.deserialize_fields(doc)
                     for doc in self.d["response"]["docs"]]

    def deserialize_fields(self, doc):
        return dict((k, self.schema.deserialize_values(k, v))
                    for k, v in doc.items())

    def __str__(self):
        return "%(numFound)s results found, starting at #%(start)s\n\n" % self.__dict__ + str(self.docs)
