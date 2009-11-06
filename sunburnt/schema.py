from __future__ import absolute_import

import datetime
import math
import operator
import warnings

import lxml.builder
import lxml.etree

from . import dates

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
        if isinstance(v, solr_date):
            self._dt_obj = v._dt_obj
        elif isinstance(v, basestring):
            try:
                self._dt_obj = dates.datetime_from_w3_datestring(v)
            except ValueError, e:
                raise SolrError(*e.args)
        elif hasattr(v, "strftime"):
            self._dt_obj = self.from_date(v)
        else:
            raise SolrError("Cannot initialize solr_date from %s object"
                            % type(v))

    @staticmethod
    def from_date(dt_obj):
        # Python datetime objects may include timezone information
        if hasattr(dt_obj, 'tzinfo') and dt_obj.tzinfo:
            # but Solr requires UTC times.
            if pytz:
                return dt_obj.astimezone(pytz.utc)
            else:
                raise EnvironmentError("pytz not available, cannot do timezone conversions")
        else:
            return dt_obj

    @property
    def microsecond(self):
        if hasattr(self._dt_obj, "microsecond"):
            return self._dt_obj.microsecond
        else:
            return int(1000000*math.modf(self._dt_obj.second)[0])

    def __repr__(self):
        return repr(self._dt_obj)

    def __unicode__(self):
        """ Serialize a datetime object in the format required
        by Solr. See http://wiki.apache.org/solr/IndexingDates
        """
        return u"%s.%sZ" % (self._dt_obj.strftime("%Y-%m-%dT%H:%M:%S"),
                            "%06d" % self.microsecond)


class SolrField(object):
    def __init__(self, node):
        self.name = node.attrib["name"]
        self.multi_valued = node.attrib.get("multiValued") == "true"
        self.required = node.attrib.get("required") == "true"

    def serialize(self, value):
        if hasattr(value, "__iter__"):
            if not self.multi_valued:
                raise SolrError("'%s' is not a multi-valued field" % self.name)
            return [self.serialize(v) for v in value]
        return self.as_unicode(self.normalize(value))

    def as_unicode(self, value):
        return unicode(value)


class SolrUnicodeField(SolrField):
    def normalize(self, value):
        try:
            return unicode(value)
        except UnicodeError:
            raise SolrError("%s could not be coerced to unicode" % value)

    def as_unicode(self, value):
        return value


class SolrBooleanField(SolrField):
    def normalize(self, value):
        return bool(value)

    def as_unicode(self, value):
        return u"true" if value else u"false"


class SolrNumericalField(SolrField):
    def normalize(self, value):
        try:
            v = self.base_type(value)
        except (OverflowError, ValueError):
            raise SolrError("%s is invalid value for %s" % (value, self.__class__))
        if v < self.min or v > self.max:
            raise SolrError("%s out of range for a %s" % (value, self.__class__))
        return v


class SolrShortField(SolrNumericalField):
    base_type = int
    min = -(2**15)
    max = 2**15-1


class SolrIntField(SolrNumericalField):
    base_type = int
    min = -(2**31)
    max = 2**31-1


class SolrLongField(SolrNumericalField):
    base_type = long
    min = -(2**63)
    max = 2**63-1


class SolrFloatField(SolrNumericalField):
    base_type = float
    max = (2.0-2.0**(-23)) * 2.0**127
    min = -max


class SolrDoubleField(SolrNumericalField):
    base_type = float
    max = (2.0-2.0**(-52)) * 2.0**1023
    min = -max


class SolrDateField(SolrField):
    def normalize(self, v):
        return solr_date(v)


class SolrSchema(object):
    solr_data_types = {
        'solr.StrField':SolrUnicodeField,
        'solr.TextField':SolrUnicodeField,
        'solr.BoolField':SolrBooleanField,
        'solr.ShortField':SolrShortField,
        'solr.IntField':SolrIntField,
        'solr.SortableIntField':SolrIntField,
        'solr.TrieIntField':SolrIntField,
        'solr.LongField':SolrLongField,
        'solr.SortableLongField':SolrLongField,
        'solr.TrieLongField':SolrLongField,
        'solr.FloatField':SolrFloatField,
        'solr.SortableFloatField':SolrFloatField,
        'solr.TrieFloatField':SolrFloatField,
        'solr.DoubleField':SolrDoubleField,
        'solr.SortableDoubleField':SolrDoubleField,
        'solr.TrieDoubleField':SolrDoubleField,
        'solr.DateField':SolrDateField,
        }

    def __init__(self, f):
        """initialize a schema object from a
        filename or file-like object."""
        self.fields, self.default_field_name, self.unique_key \
            = self.schema_parse(f)
        self.default_field = self.fields[self.default_field_name] \
            if self.default_field_name else None
        self.unique_field = self.fields[self.unique_key] \
            if self.unique_key else None

    def schema_parse(self, f):
        try:
            schemadoc = lxml.etree.parse(f)
        except lxml.etree.XMLSyntaxError, e:
            raise SolrError("Invalid XML in schema:\n%s" % e.args[0])
        field_types = {}
        for data_type, field_class in self.solr_data_types.items():
            for field_type in schemadoc.xpath("/schema/types/fieldType[@class='%s']/@name" % data_type):
                field_types[field_type] = field_class
        fields = {}
        for field_node in schemadoc.xpath("/schema/fields/field"):
            try:
                name, type = field_node.attrib['name'], field_node.attrib['type']
            except KeyError, e:
                raise SolrError("Invalid schema.xml: missing %s attribute on field" % e.message)
            try:
                field_class = field_types[type]
            except KeyError, e:
                raise SolrError("Invalid schema.xml: %s field_type undefined" % type)
            fields[name] = field_class(field_node)
        default_field_name = schemadoc.xpath("/schema/defaultSearchField")
        default_field_name = default_field_name[0].text \
            if default_field_name else None
        unique_key = schemadoc.xpath("/schema/uniqueKey")
        unique_key = unique_key[0].text if unique_key else None
        return fields, default_field_name, unique_key

    def missing_fields(self, field_names):
        return [name for name in set(self.fields.keys()) - set(field_names)
                if self.fields[name].required]

    def check_fields(self, field_names):
        if isinstance(field_names, basestring):
            field_names = [field_names]
        undefined_fields = set(field_names) - set(self.fields.keys())
        if undefined_fields:
            raise SolrError("Fields not defined in schema: %s" % list(undefined_fields))

    def serialize_value(self, k, v):
        if not k in self.fields:
            raise SolrError("No such field '%s' in current schema" % k)
        return self.fields[k].serialize(v)

    def get_id_for_doc(self, doc):
        if not self.unique_key:
            raise SolrError("Schema has no unique key")
        if self.unique_key not in doc:
            raise SolrError("doc doesn't contain unique_key %s"
                            % self.unique_key)
        id = doc[self.unique_key]
        return self.unique_field.serialize(id)

    def make_update(self, docs):
        return SolrUpdate(self, docs)

    def make_delete(self, docs, query):
        return SolrDelete(self, docs, query)

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
        values = self.schema.serialize_value(name, values)
        # Distinguish lists and strings
        if isinstance(values, basestring):
            values = [values]
        return [self.FIELD({'name':name}, value) for value in values]

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
        schema_fields = self.schema.fields.keys()
        docs = [(doc if hasattr(doc, "items")
                 else object_to_dict(doc, schema_fields))
                for doc in docs]
        return self.ADD(*[self.doc(doc) for doc in docs])

    def __str__(self):
        return lxml.etree.tostring(self.xml, encoding='utf-8')


class SolrDelete(object):
    DELETE = E.delete
    ID = E.id
    QUERY = E.query
    def __init__(self, schema, docs=None, queries=None):
        self.schema = schema
        deletions = self.delete_docs(docs)
        deletions += self.delete_queries(queries)
        self.xml = self.DELETE(*deletions)

    def delete_docs(self, docs):
        if not self.schema.unique_key:
            raise SolrError("This schema has no unique key - you can only delete by query")
        if docs is None:
            docs = []
        deletions = []
        for doc in docs:
            # Really this next should check the expected type of unique key
            if isinstance(doc, (basestring, int, long, float)):
                # and what about dates?
                v = self.schema.unique_field.serialize(doc)
                deletions.append(self.ID(v))
            else:
                doc = doc if hasattr(doc, "items") \
                    else object_to_dict(doc, self.schema.fields.keys())
                deletions.append(self.ID(self.schema.get_id_for_doc(doc)))
        return deletions

    def delete_queries(self, queries):
        if queries is None:
            return []
        if isinstance(queries, basestring):
            queries = [queries]
        return [self.QUERY(query) for query in queries]

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
        details = dict(value_from_node(n) for n in
                       doc.xpath("/response/lst[@name!='moreLikeThis']"))
        details['responseHeader'] = dict(details['responseHeader'])
        for attr in ["QTime", "params", "status"]:
            setattr(self, attr, details['responseHeader'].get(attr))
        if self.status != 0:
            raise ValueError("Response indicates an error")
        result_node = doc.xpath("/response/result")[0]
        self.result = SolrResult(result_node)
        self.facet_counts = SolrFacetCounts.from_response(details)
        self.highlighting = dict((k, dict(v))
                                 for k, v in details.get("highlighting", ()))
        more_like_these_nodes = \
            doc.xpath("/response/lst[@name='moreLikeThis']/result")
        more_like_these_results = [SolrResult(node)
                                  for node in more_like_these_nodes]
        self.more_like_these = dict((n.name, n)
                                         for n in more_like_these_results)
        if len(self.more_like_these) == 1:
            self.more_like_this = self.more_like_these.values()[0]
        else:
            self.more_like_this = None

    def __str__(self):
        return str(self.result)

    def __len__(self):
        return len(self.result.docs)

    def __getitem__(self, key):
        return self.result.docs[key]


class SolrResult(object):
    def __init__(self, node):
        self.name = node.attrib['name']
        self.numFound = node.attrib['numFound']
        self.start = node.attrib['start']
        self.docs = [value_from_node(n) for n in node.xpath("doc")]

    def __str__(self):
        return "%(numFound)s results found, starting at #%(start)s\n\n" % self.__dict__ + str(self.docs)


def object_to_dict(o, names):
    return dict((name, getattr(o, name)) for name in names
                 if (hasattr(o, name) and getattr(o, name) is not None))

# This is over twice the speed of the shorter one immediately above.
# apparently hasattr is really slow; try/except is faster.
def object_to_dict(o, names):
    d = {}
    for name in names:
         try:
             a = getattr(o, name)
             if a is not None:
                 d[name] = a
         except AttributeError:
             pass
    return d

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
