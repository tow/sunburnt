from __future__ import absolute_import

import collections
import re


class SolrSearch(object):
    default_term_re = re.compile(r'^\w+$')

    def __init__(self, interface):
        self.interface = interface
        self.schema = interface.schema
        self.search = {'query':
                          {'terms':collections.defaultdict(set),
                           'phrases':collections.defaultdict(set)},
                      'filter':
                          {'terms':collections.defaultdict(set),
                           'phrases':collections.defaultdict(set)}}
        self.range_queries = []
        self.options = {}

    def update_search(self, q, t, k, v):
        if k and k not in self.schema.fields:
            raise ValueError("%s is not a valid field name" % k)
        self.search[q][t][k].add(v)
        return self

    def query_by_term(self, field_name=None, term=""):
        return self.update_search('query', 'terms', field_name, term)

    def query_by_phrase(self, field_name=None, phrase=""):
        return self.update_search('query', 'phrases', field_name, phrase)

    def filter_by_term(self, field_name=None, term=""):
        return self.update_search('filter', 'terms', field_name, term)

    def filter_by_phrase(self, field_name=None, term=""):
        return self.update_search('filter', 'phrases', field_name, phrase)

    def query(self, *args, **kwargs):
        for arg in args:
            self.update_search('query', self.term_or_phrase(arg), None, arg)
        return self.update_q('query', kwargs)

    def filter(self, *args, **kwargs):
        for arg in args:
            self.update_search('filter', self.term_or_phrase(arg), None, arg)
        return self.update_q('filter', kwargs)

    def update_q(self, q, kwargs):
        for k, v in kwargs.items():
            try:
                name, rel = k.split("__")
            except ValueError:
                name, rel = k, 'eq'
            self._check_fields(name)
            field_type  = self.schema.fields[name].type
            if rel == 'eq':
                if field_type is unicode:
                    search_type = self.term_or_phrase(v)
                else:
                    search_type = "terms"
                self.update_search(q, search_type, name, v)
            else:
                self._range_query(name, rel, v)
        return self

    def _range_query(self, name, rel, value):
        field_type  = self.schema.fields[name].type
        if field_type is bool:
            raise ValueError("Cannot do a '%s' query on a bool field" % rel)
        if rel.startswith('range'):
            try:
                assert len(value) == 2
            except (AssertionError, TypeError):
                raise ValueError("'%s__%s' argument must be a length-2 iterable"
                                 % (name, rel))
        try:
            if rel.startswith('range'):
                value = tuple(sorted(field_type(v) for v in value))
            else:
                value = field_type(value)
        except (ValueError, TypeError):
                raise ValueError("'%s__%s' arguments of the wrong type"
                                 % (name, rel))
        self.range_queries.append((name, rel, value))

    def _check_fields(self, fields):
        if isinstance(fields, basestring):
            fields = [fields]
        for field in fields:
            if field not in self.schema.fields:
                raise ValueError("Field '%s' not defined in schema" % field)
        return fields

    def facet_by(self, field, limit=None, mincount=None):
        self._check_fields(field)
        self.options.update({"facet":"true",
                             "facet.field":field})
        if limit:
            self.options["f.%s.facet.limit" % field] = limit
        if mincount:
            self.options["f.%s.facet.mincount" % field] = mincount
        return self

    def highlight(self, fields=None, snippets=None, fragsize=None):
        self.options["hl"] = "true"
        if fields:
            fields = self._check_fields(fields)
            self.options["hl.fl"] = ','.join(fields)
            # what if fields has a comma in it?
        if snippets is not None:
            for field in fields:
                self.options["f.%s.hl.snippets" % field] = snippets
        if fragsize is not None:
            for field in fields:
                self.options["f.%s.hl.fragsize" % field] = fragsize
        return self

    def mlt(self, fields, query_fields=None, **kwargs):
        self.options["mlt"] = "true"
        fields = self._check_fields(fields)
        self.options["mlt.fl"] = ",".join(fields)
        if query_fields is not None:
            qf_arg = []
            for k, v in query_fields.items():
                if k not in fields:
                    raise SolrError("'%s' specified in query_fields but not fields")
                if v is None:
                    qf_arg.append(k)
                else:
                    try:
                        v = float(v)
                    except ValueError:
                        raise SolrError("'%s' has non-numerical boost value")
                    qf_arg.append("%s^%s" % (k, v))
            self.options["mlt.qf"] = " ".join(qf_arg)
        mlt_options = MoreLikeThisOptions(self.schema)
        self.options.update(mlt_options(**kwargs))
        return self

    def paginate(self, start=1, rows=10):
        self.options["start"] = start
        self.options["rows"] = rows
        return self

    def execute(self):
        q = "%s %s" % (serialize_search(**self.search['query']),
                       serialize_range_queries(self.range_queries))
        if q:
            self.options["q"] = q
        qf = serialize_search(**self.search['filter'])
        if qf:
            self.options["qf"] = qf
        return self.interface.search(**self.options)

    def term_or_phrase(self, arg):
        return 'terms' if self.default_term_re.match(arg) else 'phrases'


class MoreLikeThisOptions(object):
    opts = {"count":int,
            "mintf":float,
            "mindf":float,
            "minwl":int,
            "maxwl":int,
            "maxqt":int,
            "maxntp":int,
            "boost":bool,
            }
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, **kwargs):
        options = {}
        for opt_name, opt_value in kwargs.items():
            try:
                opt_type = self.opts[opt_name]
            except IndexError:
                raise SolrError("Invalid MLT option %s" % opt_name)
            try:
                options["mlt.%s" % opt_name] = opt_type(opt_value)
            except (ValueError, TypeError):
                raise SolrError("'mlt.%s' should be an '%s'"%
                                (opt_name, opt_type.__name__))
        return options


def serialize_search(terms, phrases):
    s = []
    for name in terms:
        if name:
            s += ['%s:%s' % (name, lqs_escape(value))
                  for value in terms[name]]
        else:
            s += [lqs_escape(value) for value in terms[name]]
    for name in phrases:
        if name:
            s += ['%s:"%s"' % (name, value)
                  for value in phrases[name]]
        else:
            s += ['"%s"' % value for value in phrases[name]]
    return ' '.join(s)

_range_query_templates = {
    "lt": "* TO %s",
    "gt": "%s TO *",
    "ra": "%s TO %s",
}

def serialize_range_queries(queries):
    s = []
    for name, rel, value in queries:
        if rel in ('lte', 'gte', 'range'):
            left, right = "[", "]"
        else:
            left, right = "{", "}"
        range = _range_query_templates[rel[:2]] % value
        s.append("%(name)s:%(left)s%(range)s%(right)s" % vars())
    return ' '.join(s)


lucene_special_chars = re.compile(r'([+\-&|!\(\){}\[\]\^\"~\*\?:\\])')
def lqs_escape(s):
    if isinstance(s, unicode):
        return lucene_special_chars.sub(r'\\\1', s)
    else:
        return s
