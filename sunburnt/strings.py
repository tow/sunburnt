class WildcardString(unicode):
    def __new__(cls, s):
        return unicode.__new__(cls, s)

    def __init__(self, s):
        self.chars = self.get_wildcards(s)

    class SpecialChar(object):
        def __unicode__(self):
            return unicode(self.char)
    class Asterisk(SpecialChar):
        char = '*'
    class QuestionMark(SpecialChar):
        char = '?'

    def get_wildcards(self, s):
        backslash = False
        i = 0
        chars = []
        for c in s:
            if backslash:
                backslash = False
                chars.append(c)
                continue
            i += 1
            if c == '\\':
                backslash = True
            elif c == '*':
                chars.append(self.Asterisk())
            elif c == '?':
                chars.append(self.QuestionMark())
            else:
                chars.append(c)
        if backslash:
            chars.append('\\')
        return chars

    # The behaviour below is only really relevant for String fields rather
    # than Text fields - most queryparsers will strip these characters out
    # for a text field anyway.
    lucene_special_chars = '+-&|!(){}[]^"~*?: \t\v\\'
    def escape_for_lqs_term(self):
        if self in ["AND", "OR", "NOT"]:
            return '"%s"' % self
        chars = []
        for c in self.chars:
            if isinstance(c, basestring) and c in self.lucene_special_chars:
                chars.append(u'\%s'%c)
            else:
                chars.append(u'%s'%c)
        return ''.join(chars)
