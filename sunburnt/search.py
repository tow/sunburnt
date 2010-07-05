from __future__ import absolute_import

import collections, copy, re

from .schema import SolrError, SolrUnicodeField, SolrBooleanField


class LuceneQuery(object):
    default_term_re = re.compile(r'^\w+$')
    range_query_templates = {
        "lt": "{* TO %s}",
        "lte": "[* TO %s]",
        "gt": "{%s TO *}",
        "gte": "[%s TO *]",
        "rangeexc": "{%s TO %s}",
        "range": "[%s TO %s]",
    }
    def __init__(self, schema, option_flag=None):
        self.schema = schema
        self.option_flag = option_flag
        self.terms = collections.defaultdict(set)
        self.phrases = collections.defaultdict(set)
        self.ranges = set()
        self.subqueries = []

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
        return ' AND '.join(s)

    # I'm very much not sure we're doing the right thing here:
    lucene_special_chars = re.compile(r'([+\-&|!\(\){}\[\]\^\"~\*\?:\\])')
    lucene_special_words = ("AND", "NOT", "OR")
    def __lqs_escape(self, s):
        if s in self.lucene_special_words:
            return u'"%s"'%s
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
        return ' AND '.join(s)

    def __phrase_escape(self, s):
        # For phrases, anything is allowed between double-quotes, except
        # double-quotes themselves, which must be escaped with backslashes,
        # and thus also backslashes must too be escaped.
        return s.replace('\\', '\\\\').replace('"', '\\"')

    def serialize_range_queries(self):
        s = []
        for name, rel, value in sorted(self.ranges):
            range = self.range_query_templates[rel] % value
            s.append("%(name)s:%(range)s" % vars())
        return ' AND '.join(s)

    def child_needs_parens(self, child, op=None):
        if child.is_single_query():
            return False
        elif hasattr(child, '_not'):
            return False
        elif hasattr(child, '_pow'):
            return False
        elif (hasattr(self, '_or') or op=='OR') and hasattr(child, '_or'):
            return False
        elif (hasattr(self, '_and') or op=='AND') and hasattr(child, '_and'):
            return False
        else:
            return True

    def __unicode__(self):
        if hasattr(self, '_or'):
            s = []
            for o in self._or:
                if self.child_needs_parens(o):
                    s.append(u"(%s)"%o)
                else:
                    s.append(u"%s"%o)
            return u" OR ".join(s)
        elif hasattr(self, '_and'):
            s = []
            for o in self._and:
                if self.child_needs_parens(o):
                    s.append(u"(%s)"%o)
                else:
                    s.append(u"%s"%o)
            return u" AND ".join(s)
        elif hasattr(self, '_not'):
            o = self._not
            if hasattr(o, '_not'):
                # they cancel out
                self._not = self._not._not
                return u"%s"%o
            if self.child_needs_parens(o):
                return u"NOT (%s)"%o
            else:
                return u"NOT %s"%o
        elif hasattr(self, '_pow'):
            q, v = self._pow
            if self.child_needs_parens(q):
                return u"(%s)^%s"%(q,v)
            else:
                return u"%s^%s"%(q,v)
        else:
            u = [s for s in [self.serialize_term_queries(),
                             self.serialize_phrase_queries(),
                             self.serialize_range_queries()]
                 if s]
            if not u and len(self.subqueries) == 1:
                # Only one subquery, no need for parens
                u.append(u"%s"%self.subqueries[0])
            else:
                for q in self.subqueries:
                    if self.child_needs_parens(q, 'AND'):
                        u.append(u"(%s)"%q)
                    else:
                        u.append(u"%s"%q)
            return ' AND '.join(u)

    def stringify_with_optional_parens(self):
        if self.is_single_query():
            s = u"%s"
        else:
            s = u"(%s)"
        return s % self

    def is_single_query(self):
        return sum([len(self.terms), len(self.phrases), len(self.ranges), len(self.subqueries)]) == 1

    def Q(self):
        return LuceneQuery(self.schema)

    def __nonzero__(self):
        return bool(self.terms) or bool(self.phrases) or bool(self.ranges) or bool(self.subqueries)

    def __or__(self, other):
        q = LuceneQuery(self.schema)
        q._or = (self, other)
        return q

    def __and__(self, other):
        q = LuceneQuery(self.schema)
        q._and = (self, other)
        return q

    def __invert__(self):
        q = LuceneQuery(self.schema)
        q._not = self
        return q

    def __pow__(self, value):
        try:
            float(value)
        except ValueError:
            raise ValueError("Non-numeric value supplied for boost")
        q = LuceneQuery(self.schema)
        q._pow = (self, value)
        return q
        
    def add(self, args, kwargs, terms_or_phrases=None):
        _args = []
        for arg in args:
            if isinstance(arg, LuceneQuery):
                self.subqueries.append(arg)
            else:
                _args.append(arg)
        args = _args
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
        values = field.serialize(value) # Might be multivalued
        if isinstance(values, basestring):
            values = [values]
        for value in values:
            if isinstance(field, SolrUnicodeField):
                this_term_or_phrase = term_or_phrase or self.term_or_phrase(value)
            else:
                this_term_or_phrase = "terms"
            getattr(self, this_term_or_phrase)[field_name].add(value)

    def add_range(self, field_name, rel, value):
        field = self.schema.fields[field_name]
        if isinstance(field, SolrBooleanField):
            raise ValueError("Cannot do a '%s' query on a bool field" % rel)
        if rel not in self.range_query_templates:
            raise SolrError("No such relation '%s' defined" % rel)
        if rel in ('range', 'rangeexc'):
            try:
                assert len(value) == 2
            except (AssertionError, TypeError):
                raise SolrError("'%s__%s' argument must be a length-2 iterable"
                                 % (field_name, rel))
            value = tuple(sorted(field.serialize(v) for v in value))
        else:
            value = field.serialize(value)
        self.ranges.add((field_name, rel, value))

    def term_or_phrase(self, arg, force=None):
        return 'terms' if self.default_term_re.match(arg) else 'phrases'


class SolrSearch(object):
    option_modules = ('query_obj', 'filter_obj', 'paginator', 'more_like_this', 'highlighter', 'faceter')
    def __init__(self, interface):
        self.interface = interface
        self.schema = interface.schema
        self.query_obj = LuceneQuery(self.schema, 'q')
        self.filter_obj = LuceneQuery(self.schema, 'fq')
        self.paginator = PaginateOptions(self.schema)
        self.more_like_this = MoreLikeThisOptions(self.schema)
        self.highlighter = HighlightOptions(self.schema)
        self.faceter = FacetOptions(self.schema)

    def Q(self, *args, **kwargs):
        q = LuceneQuery(self.schema)
        q.add(args, kwargs)
        return q

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

    def exclude(self, *args, **kwargs):
        self.query(~self.Q(*args, **kwargs))
        return self

    def filter(self, *args, **kwargs):
        self.filter_obj.add(args, kwargs)
        return self

    def filter_exclude(self, *args, **kwargs):
        self.filter(~self.Q(*args, **kwargs))
        return self

    def facet_by(self, field, **kwargs):
        self.faceter.update(field, **kwargs)
        return self

    def highlight(self, fields=None, **kwargs):
        self.highlighter.update(fields, **kwargs)
        return self

    def mlt(self, fields, query_fields=None, **kwargs):
        self.more_like_this.update(fields, query_fields, **kwargs)
        return self

    def paginate(self, start=None, rows=None):
        self.paginator.update(start, rows)
        return self

    def boost_relevancy(self, boost_score, **kwargs):
        if not self.query_obj:
            raise TypeError("Can't boost the relevancy of an empty query")
        try:
            float(boost_score)
        except ValueError:
            raise ValueError("Non-numeric boost value supplied")
        old_query = self.query_obj
        self.query_obj = LuceneQuery(self.schema, 'q')
        return self.query(old_query | (copy.deepcopy(old_query) & self.Q(**kwargs)**boost_score))

    def options(self):
        options = {}
        for option_module in self.option_modules:
            options.update(getattr(self, option_module).options)
        return options

    def params(self):
        return self.interface.params(**self.options())

    def execute(self, constructor=dict):
        result = self.interface.search(**self.options())
        if constructor is not dict:
            result.result.docs = [constructor(**d) for d in result.result.docs]
        return result


class Options(object):
    def invalid_value(self, msg=""):
        assert False, msg

    def update(self, fields=None, **kwargs):
        if fields:
            self.schema.check_fields(fields)
            if isinstance(fields, basestring):
                fields = [fields]
            for field in set(fields) - set(self.fields):
                self.fields[field] = {}
        elif kwargs:
            fields = [None]
        self.check_opts(fields, kwargs)

    def check_opts(self, fields, kwargs):
        for k, v in kwargs.items():
            if k not in self.opts:
                raise SolrError("No such option for %s: %s" % (self.option_name, k))
            opt_type = self.opts[k]
            try:
                if isinstance(opt_type, (list, tuple)):
                    assert v in opt_type
                elif isinstance(opt_type, type):
                    v = opt_type(v)
                else:
                    v = opt_type(self, v)
            except:
                raise SolrError("Invalid value for %s option %s: %s" % (self.option_name, k, v))
            for field in fields:
                self.fields[field][k] = v

    @property
    def options(self):
        opts = {}
        if self.fields:
            opts[self.option_name] = True
            fields = [field for field in self.fields if field]
            self.field_names_in_opts(opts, fields)
        for field_name, field_opts in self.fields.items():
            if not field_name:
                for field_opt, v in field_opts.items():
                    opts['%s.%s'%(self.option_name, field_opt)] = v
            else:
                for field_opt, v in field_opts.items():
                    opts['f.%s.%s.%s'%(field_name, self.option_name, field_opt)] = v
        return opts



class FacetOptions(Options):
    option_name = "facet"
    opts = {"prefix":unicode,
            "sort":[True, False, "count", "index"],
            "limit":int,
            "offset":lambda self, x: int(x) >= 0 and int(x) or self.invalid_value(),
            "mincount":lambda self, x: int(x) >= 0 and int(x) or self.invalid_value(),
            "missing":bool,
            "method":["enum", "fc"],
            "enum.cache.minDf":int,
            }

    def __init__(self, schema):
        self.schema = schema
        self.fields = collections.defaultdict(dict)

    def field_names_in_opts(self, opts, fields):
        if fields:
            opts["facet.field"] = sorted(fields)


class HighlightOptions(Options):
    option_name = "hl"
    opts = {"snippets":int,
            "fragsize":int,
            "mergeContinuous":bool,
            "requireFieldMatch":bool,
            "maxAnalyzedChars":int,
            "alternateField":lambda self, x: x if x in self.schema.fields else self.invalid_value(),
            "maxAlternateFieldLength":int,
            "formatter":["simple"],
            "simple.pre":unicode,
            "simple.post":unicode,
            "fragmenter":unicode,
            "usePhraseHighlighter":bool,
            "highlightMultiTerm":bool,
            "regex.slop":float,
            "regex.pattern":unicode,
            "regex.maxAnalyzedChars":int
            }
    def __init__(self, schema):
        self.schema = schema
        self.fields = collections.defaultdict(dict)

    def field_names_in_opts(self, opts, fields):
        if fields:
            opts["hl.fl"] = ",".join(sorted(fields))


class MoreLikeThisOptions(Options):
    opts = {"count":int,
            "mintf":int,
            "mindf":int,
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

    def update(self, fields, query_fields=None, **kwargs):
        self.schema.check_fields(fields)
        if isinstance(fields, basestring):
            fields = [fields]
        self.fields.update(fields)

        if query_fields is not None:
            for k, v in query_fields.items():
                if k not in self.fields:
                    raise SolrError("'%s' specified in query_fields but not fields"% k)
                if v is not None:
                    try:
                        v = float(v)
                    except ValueError:
                        raise SolrError("'%s' has non-numerical boost value"% k)
            self.query_fields.update(query_fields)

        for opt_name, opt_value in kwargs.items():
            if opt_name not in self.opts:
                raise SolrError("Invalid MLT option %s" % opt_name)
            opt_type = self.opts[opt_name]
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
            opts['mlt.fl'] = ','.join(sorted(self.fields))

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
