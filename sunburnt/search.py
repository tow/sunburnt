from __future__ import absolute_import

import collections
import re


class LuceneQuery(object):
    default_term_re = re.compile(r'^\w+$')
    range_query_templates = {
        "lt": "* TO %s",
        "gt": "%s TO *",
        "ra": "%s TO %s",
    }
    def __init__(self, schema):
        self.schema = schema
        self.terms = collections.defaultdict(set)
        self.phrases = collections.defaultdict(set)
        self.ranges = []

    def serialize_term_queries(self):
        s = []
        for name, value_set in self.terms.items():
            if name:
                s += [u'%s:%s' % (name, self.__lqs_escape(value))
                      for value in value_set]
            else:
                s += [lqs_escape(value) for value in value_set]
        return ' '.join(s)

    lucene_special_chars = re.compile(r'([+\-&|!\(\){}\[\]\^\"~\*\?:\\])')
    def __lqs_escape(self, s):
        if isinstance(s, unicode):
            return self.lucene_special_chars.sub(r'\\\1', s)
        else:
            return s

    def serialize_phrase_queries(self):
        s = []
        for name, value_set in self.phrases.items():
            if name:
                s += [u'%s:"%s"' % (name, value)
                      for value in value_set]
            else:
                s += [u'"%s"' % value for value in value_set]
        return ' '.join(s)

    def serialize_range_queries(self):
        s = []
        for name, rel, value in self.ranges:
            if rel in ('lte', 'gte', 'range'):
                left, right = "[", "]"
            else:
                left, right = "{", "}"
            range = self.range_query_templates[rel[:2]] % value
            s.append("%(name)s:%(left)s%(range)s%(right)s" % vars())
        return ' '.join(s)

    def __unicode__(self):
        u = [self.serialize_term_queries(),
             self.serialize_phrase_queries(),
             self.serialize_range_queries()]
        return ' '.join(s for s in u if s)

    def __nonzero__(self):
        return bool(self.terms) or bool(self.phrases) or bool(self.ranges)

    def add(self, kwargs, terms_or_phrases=None):
        for k, v in kwargs.items():
            try:
                field_name, rel = k.split("__")
            except ValueError:
                field_name, rel = k, 'eq'
            if field_name not in self.schema.fields:
                raise ValueError("%s is not a valid field name" % k)
            field_type = self.schema.fields[field_name].type
            if rel == 'eq':
                if field_type is unicode:
                    search_type = terms_or_phrases or self.term_or_phrase(v)
                else:
                    try:
                        v = field_type(v)
                    except TypeError:
                        raise SolrError("Invalid value %s for field %s"
                                        % (v, name))
                    search_type = "terms"
                self.add_exact(search_type, field_name, v)
            else:
                self.add_range(field_name, rel, v)

    def add_exact(self, term_or_phrase, field_name, value):
        if field_name and field_name not in self.schema.fields:
            raise ValueError("%s is not a valid field name" % k)
        getattr(self, term_or_phrase)[field_name].add(value)

    def add_range(self, field_name, rel, value):
        field_type = self.schema.fields[field_name].type
        if field_type is bool:
            raise ValueError("Cannot do a '%s' query on a bool field" % rel)
        if rel.startswith('range'):
            try:
                assert len(value) == 2
            except (AssertionError, TypeError):
                raise ValueError("'%s__%s' argument must be a length-2 iterable"
                                 % (field_name, rel))
        try:
            if rel.startswith('range'):
                value = tuple(sorted(field_type(v) for v in value))
            else:
                value = field_type(value)
        except (ValueError, TypeError):
                raise ValueError("'%s__%s' arguments of the wrong type"
                                 % (field_name, rel))
        self.ranges.append((field_name, rel, value))

    def term_or_phrase(self, arg):
        return 'terms' if self.default_term_re.match(arg) else 'phrases'


class SolrSearch(object):
    def __init__(self, interface):
        self.interface = interface
        self.schema = interface.schema
        self.query_obj = LuceneQuery(self.schema)
        self.filter_obj = LuceneQuery(self.schema)
        self.options = {}

    def query_by_term(self, *args, **kwargs):
        return self.query_obj.add_exact('terms', field_name, term)

    def query_by_phrase(self, field_name=None, phrase=""):
        return self.query_obj.add_exact('phrases', field_name, phrase)

    def filter_by_term(self, field_name=None, term=""):
        return self.filter_obj.add_exact('terms', field_name, term)

    def filter_by_phrase(self, field_name=None, phrase=""):
        return self.filter_obj.add_exact('phrases', field_name, phrase)

    def query(self, *args, **kwargs):
        for arg in args:
            self.query_obj.add_exact(self.term_or_phrase(arg), None, arg)
        self.query_obj.add(kwargs)
        return self

    def filter(self, *args, **kwargs):
        for arg in args:
            self.filter_obj.add_exact(self.term_or_phrase(arg), None, arg)
        self.filter_obj.add(kwargs)
        return self

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
        q = unicode(self.query_obj)
        if q:
            self.options["q"] = q
        fq = unicode(self.filter_obj)
        if fq:
            self.options["fq"] = fq
        return self.interface.search(**self.options)


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
