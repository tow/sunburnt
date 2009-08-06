from __future__ import absolute_import

import datetime
import math
import operator
import warnings

import lxml.builder
import lxml.etree

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
        self.required = node.attrib.get("required") == "true"
        self.type = data_type


class SolrSchema(object):
    solr_data_types = {
        'solr.StrField':unicode,
        'solr.TextField':unicode,
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
        self.fields, self.default_field = self.schema_parse(f)

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
        default = schemadoc.xpath("/schema/defaultSearchField")
        default_field = default[0].text if default else None
        return fields, default_field

    def missing_fields(self, field_names):
        return [name for name in set(self.fields.keys()) - set(field_names)
                if self.fields[name].required]

    def serialize_value(self, k, v):
        try:
            value = self.fields[k].type(v)
        except KeyError:
            raise SolrError("No such field '%s' in current schema" % k)
        if not isinstance(value, unicode):
            value = unicode(value)
        return value

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
        missing_fields = self.schema.missing_fields(doc.keys())
        if missing_fields:
            raise SolrError("These required fields are unspecified:\n %s" %
                            missing_fields)
        if not doc:
            return self.DOC()
        else:
            return self.DOC(*reduce(operator.add,
                                    [self.fields(name, values)
                                     for name, values in doc.items()]))

    def add(self, docs):
        if hasattr(docs, "items") or not hasattr(docs, "__iter__"):
            docs = [docs]
        docs = [(doc if hasattr(doc, "items")
                 else object_to_dict(doc, self.schema.fields.keys()))
                for doc in docs]
        return self.ADD(*[self.doc(doc) for doc in docs])

    def __str__(self):
        return lxml.etree.tostring(self.xml, encoding='utf-8')


class SolrFacetCounts(object):
    members= ["facet_dates", "facet_fields", "facet_queries"]
    def __init__(self, **kwargs):
        for member in self.members:
            setattr(self, member, kwargs.get(member, ()))
        self.facet_fields = dict(self.facet_fields)

    @classmethod
    def from_response(cls, response):
        facet_counts_dict = dict(response.get("facet_counts", {}))
        return SolrFacetCounts(**facet_counts_dict)


class SolrResults(object):
    def __init__(self, schema, xmlmsg):
        self.schema = schema
        doc = lxml.etree.fromstring(xmlmsg)
        details = dict(value_from_node(n) for n in doc.xpath("/response/lst"))
        details['responseHeader'] = dict(details['responseHeader'])
        for attr in ["QTime", "params", "status"]:
            setattr(self, attr, details['responseHeader'].get(attr))
        if self.status != 0:
            raise ValueError("Response indicates an error")
        result = doc.xpath("/response/result")[0]
        self.numFound = result.attrib['numFound']
        self.start = result.attrib['start']
        self.docs = [value_from_node(n) for n in result.xpath("doc")]
        self.facet_counts = SolrFacetCounts.from_response(details)
        self.highlighting = dict((k, dict(v))
                                 for k, v in details.get("highlighting", ()))

    def __str__(self):
        return "%(numFound)s results found, starting at #%(start)s\n\n" % self.__dict__ + str(self.docs)


def object_to_dict(o, names):
    return dict((name, getattr(o, name)) for name in names
                 if hasattr(o, name))

def value_from_node(node):
    name = node.attrib.get('name')
    if node.tag in ('lst', 'arr'):
        value = [value_from_node(n) for n in node.getchildren()]
    if node.tag in 'doc':
        value = dict(value_from_node(n) for n in node.getchildren())
    elif node.tag == 'null':
        value = None
    elif node.tag in ('str', 'byte'):
        value = node.text
    elif node.tag in ('short', 'int'):
        value = int(node.text)
    elif node.tag == 'long':
        value = long(node.text)
    elif node.tag == 'bool':
        value = True if node.text == "true" else False
    elif node.tag in ('float', 'double'):
        value = float(node.text)
    elif node.tag == 'date':
        value = solr_date(node.text)
    if name is not None:
        return name, value
    else:
        return value
