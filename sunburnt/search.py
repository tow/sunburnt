from __future__ import absolute_import

import collections
import re

from .schema import SolrError, SolrUnicodeField, SolrBooleanField


class LuceneQuery(object):
    default_term_re = re.compile(r'^\w+$')
    range_query_templates = {
        "lt": "* TO %s",
        "gt": "%s TO *",
        "ra": "%s TO %s",
    }
    def __init__(self, option_flag, schema):
        self.option_flag = option_flag
        self.schema = schema
        self.terms = collections.defaultdict(set)
        self.phrases = collections.defaultdict(set)
        self.ranges = []

    @property
    def options(self):
        opts = {}
        s = unicode(self)
        if s:
            opts[self.option_flag] = s
        return opts

    # Below, we sort all our value_sets - this is for predictability when testing.
    def serialize_term_queries(self):
        s = []
        for name, value_set in sorted(self.terms.items()):
            if name:
                field = self.schema.fields[name]
            else:
                field = self.schema.default_field
            if isinstance(field, SolrUnicodeField):
                value_set = [self.__lqs_escape(value) for value in value_set]
            if name:
                s += [u'%s:%s' % (name, value) for value in sorted(value_set)]
            else:
                s += sorted(value_set)
        return ' '.join(s)

    # I'm very much not sure we're doing the right thing here:
    lucene_special_chars = re.compile(r'([+\-&|!\(\){}\[\]\^\"~\*\?:\\])')
    def __lqs_escape(self, s):
        return self.lucene_special_chars.sub(r'\\\1', s)

    def serialize_phrase_queries(self):
        s = []
        for name, value_set in sorted(self.phrases.items()):
            if name:
                field = self.schema.fields[name]
            else:
                field = self.schema.default_field
            if isinstance(field, SolrUnicodeField):
                value_set = [self.__phrase_escape(value) for value in value_set]
            if name:
                s += [u'%s:"%s"' % (name, value)
                      for value in sorted(value_set)]
            else:
                s += ['"%s"' % value for value in sorted(value_set)]
        return ' '.join(s)

    phrase_special_chars = re.compile(r'"')
    def __phrase_escape(self, s):
        return self.phrase_special_chars.sub(r'\\\1', s)

    def serialize_range_queries(self):
        s = []
        for name, rel, value in sorted(self.ranges):
            if rel in ('lte', 'gte', 'range'):
                left, right = "[", "]"
            else:
                left, right = "{", "}"
            if isinstance(value, tuple):
                value = tuple(self.schema.serialize_value(name, v) for v in value)
            else:
                value = self.schema.serialize_value(name, value)
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

    def add(self, args, kwargs, terms_or_phrases=None):
        try:
            terms_or_phrases = kwargs.pop("__terms_or_phrases")
        except KeyError:
            terms_or_phrases = None
        for value in args:
            self.add_exact(None, value, terms_or_phrases)
        for k, v in kwargs.items():
            try:
                field_name, rel = k.split("__")
            except ValueError:
                field_name, rel = k, 'eq'
            if field_name not in self.schema.fields:
                raise ValueError("%s is not a valid field name" % k)
            if rel == 'eq':
                self.add_exact(field_name, v, terms_or_phrases)
            else:
                self.add_range(field_name, rel, v)

    def add_exact(self, field_name, value, term_or_phrase):
        if field_name:
            field = self.schema.fields[field_name]
        else:
            field = self.schema.default_field
        if isinstance(field, SolrUnicodeField):
            term_or_phrase = term_or_phrase or self.term_or_phrase(value)
        else:
            value = field.serialize(value)
            term_or_phrase = "terms"
        getattr(self, term_or_phrase)[field_name].add(value)

    def add_range(self, field_name, rel, value):
        field = self.schema.fields[field_name]
        if isinstance(field, SolrBooleanField):
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

    def term_or_phrase(self, arg, force=None):
        return 'terms' if self.default_term_re.match(arg) else 'phrases'


class SolrSearch(object):
    def __init__(self, interface):
        self.interface = interface
        self.schema = interface.schema
        self.query_obj = LuceneQuery('q', self.schema)
        self.filter_obj = LuceneQuery('fq', self.schema)
        self.paginator = PaginateOptions(self.schema)
        self.more_like_this = MoreLikeThisOptions(self.schema)
        self.highlighter = HighlightOptions(self.schema)
        self.faceter = FacetOptions(self.schema)
        self.option_modules = [self.query_obj, self.filter_obj, self.paginator,
                               self.more_like_this, self.highlighter, self.faceter]

    def query_by_term(self, *args, **kwargs):
        return self.query(__terms_or_phrases="terms", *args, **kwargs)

    def query_by_phrase(self, *args, **kwargs):
        return self.query(__terms_or_phrases="phrases", *args, **kwargs)

    def filter_by_term(self, *args, **kwargs):
        return self.filter(__terms_or_phrases="terms", *args, **kwargs)

    def filter_by_phrase(self, *args, **kwargs):
        return self.filter(__terms_or_phrases="phrases", *args, **kwargs)

    def query(self, *args, **kwargs):
        self.query_obj.add(args, kwargs)
        return self

    def filter(self, *args, **kwargs):
        self.filter_obj.add(args, kwargs)
        return self

    def facet_by(self, field, limit=None, mincount=None):
        self.faceter.update(field, limit, mincount)
        return self

    def highlight(self, fields=None, snippets=None, fragsize=None):
        self.highlighter.update(fields, snippets, fragsize)
        return self

    def mlt(self, fields, query_fields=None, **kwargs):
        self.more_like_this.update(fields, query_fields, **kwargs)
        return self

    def paginate(self, start=None, rows=None):
        self.paginator.update(start, rows)
        return self

    def execute(self):
        options = {}
        for option_module in self.option_modules:
            options.update(option_module.options)
        return self.interface.search(**options)


class Options(object):
    pass


class FacetOptions(Options):
    def __init__(self, schema):
        self.schema = schema
        self.fields = {}
        
    def update(self, fields, limit=None, mincount=None):
        self.schema.check_fields(fields)
        if isinstance(fields, basestring):
            fields = [fields]
        for field in fields:
            self.fields[field] = {"limit":limit, "mincount":mincount}

    @property
    def options(self):
        opts = {}
        if self.fields:
            opts['facet'] = True
            opts['facet.field'] = set()
        for field_name, field_opts in self.fields.items():
            opts['facet.field'].add(field_name)
            
            if field_opts['limit'] is not None:
                opts["f.%s.facet.limit" % field_name] = field_opts['limit']
            if field_opts['mincount'] is not None:
                opts["f.%s.facet.mincount" % field_name] = field_opts['mincount']
        return opts


class HighlightOptions(Options):
    def __init__(self, schema):
        self.schema = schema
        self.fields = {}
        self.snippets = None
        self.fragsize = None

    def update(self, fields=None, snippets=None, fragsize=None):
        if fields:
            self.schema.check_fields(fields)
            for field in fields:
                self.fields[field] = {'snippets':snippets, 'fragsize':fragsize}
        else:
            if snippets is not None:
                self.snippets = snippets
            if fragsize is not None:
                self.fragsize = fragsize

    @property
    def options(self):
        opts = {}
        if self.fields:
            opts['hl'] = True
            opts["hl.fl"] = ','.join(fields)
            if self.snippets is not None:
                opts['hl.snippets'] = self.snippets
            if self.fragsize is not None:
                opts['hl.fragsize'] = self.fragsize
        for field_name, field_opts in self.fields:
            if field_opts.get('snippets') is not None:
                opts["f.%s.hl.snippets" % field_name] = field_opts['snippets']
            if field_opts.get('fragsize') is not None:
                opts["f.%s.hl.fragsize" % field_name] = field_opts['fragsize']
        return opts


class MoreLikeThisOptions(Options):
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
        self.fields = set()
        self.query_fields = {}
        self.kwargs = {}

    def update(self, fields, query_fields, **kwargs):
        self.schema.check_fields(fields)
        self.fields = self.fields.add(fields)

        if query_fields is not None:
            for k, v in query_fields.items():
                if k not in self.fields:
                    raise SolrError("'%s' specified in query_fields but not fields", k)
                if v is not None:
                    try:
                        v = float(v)
                    except ValueError:
                        raise SolrError("'%s' has non-numerical boost value", k)
        self.query_fields.update(query_fields)

        for opt_name, opt_type in kwargs.items():
            if opt_name not in self.opts:
                raise SolrError("Invalid MLT option %s" % opt_name)
            try:
                opt_type(opt_value)
            except (ValueError, TypeError):
                raise SolrError("'mlt.%s' should be an '%s'"%
                                (opt_name, opt_type.__name__))
        self.kwargs.update(kwargs)

    @property
    def options(self):
        opts = {}
        if self.fields:
            opts['mlt'] = True
            opts['mlt.fl'] = ','.join(self.fields)

        if self.query_fields:
            qf_arg = []
            for k, v in self.query_fields.items():
                if v is None:
                    qf_arg.append(k)
                else:
                    qf_arg.append("%s^%s" % (k, float(v)))
            opts["mlt.qf"] = " ".join(qf_arg)

        for opt_name, opt_value in self.kwargs.items():
            opt_type = self.opts[opt_name]
            opts["mlt.%s" % opt_name] = opt_type(opt_value)

        return opts


class PaginateOptions(Options):
    def __init__(self, schema):
        self.schema = schema
        self.start = None
        self.rows = None

    def update(self, start, rows):
        if start is not None:
            if start < 0:
                raise SolrError("paginator start index must be 0 or greater")
            self.start = start
        if rows is not None:
            if rows < 0:
                raise SolrError("paginator rows must be 0 or greater")
            self.rows = rows

    @property
    def options(self):
        opts = {}
        if self.start is not None:
            opts['start'] = self.start
        if self.rows is not None:
            opts['rows'] = self.rows
        return opts
