import lxml.etree

class solr_date(object):
    pass


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
