#!/usr/bin/env python
# -*-coding: utf8-*-
# Title: walktree.py
# Author: Gribouillis for the python forum at www.daniweb.com
# Created: 2011-11-18 23:28:39.608291 (isoformat date)
# License: Public Domain
# Use this code freely.
# IP: http://www.daniweb.com/software-development/python/code/395270
"""This module implements a generic depth first tree and graph traversal.
"""
from __future__ import print_function
from collections import deque, namedtuple
from functools import reduce
import operator
import sys
import types

version_info = (1, 4)
version = ".".join(map(str, version_info))
__all__ = ["walk", "event", "event_repr",
            "enter", "within", "exit", "leaf", "bounce", "cycle"]

class ConstSequence(object):
    "Read-only wrapper around a sequence type instance"
    def __init__(self, seq):
        if isinstance(seq, ConstSequence):
            seq = seq._adaptee
        self._adaptee = seq
    
    def __getitem__(self, key):
        if isinstance(key, types.SliceType):
            return ConstSequence(self._adaptee[key])
        else:
            return self._adaptee[key]
        
    def __len__(self):
        return len(self._adaptee)
    def __contains__(self, key):
        return key in self._adaptee
    
    def __iter__(self):
        return (x for x in self._adaptee)
    
    def __reversed__(self):
        return (x for x in reversed(self._adaptee))

class _Int(int):
    pass
_cs = _Int()
for _i, _line in enumerate("""
    lnr: leaf non bounce
    lr: leaf bounce
    irnc: inner bounce non cycle
    ie: inner enter
    iw: inner within
    ix: inner exit
    ic: inner bounce cycle
    """.strip().splitlines()):
    _name = _line.lstrip().split(":")[0]
    setattr(_cs, _name, 1 << _i)
_NamedEvent = namedtuple("_NamedEvent", "name value")
def _event_items():
    yield "leaf", _cs.lnr | _cs.lr
    yield "inner", _cs.irnc | _cs.ie | _cs.iw | _cs.ix | _cs.ic
    yield "enter", _cs.ie
    yield "within", _cs.iw
    yield "exit", _cs.ix
    yield "bounce", _cs.lr | _cs.irnc | _cs.ic
    yield "cycle", _cs.ic
_named_events = tuple(_NamedEvent(*pair) for pair in _event_items())
globals().update(dict(_named_events))    
_event_names = tuple(e.name for e in _named_events)
def _test_events():
    for i, t in enumerate((
        _cs.lnr == (leaf & ~bounce),
        _cs.lr == (leaf & bounce),
        0 == (leaf & inner),
        _cs.irnc == (inner & bounce & ~cycle),
        (_cs.ie == enter) and (_cs.ie == (inner & enter)),
        (_cs.iw == within)  and (within == (inner & within)),
        (_cs.ix == exit) and (exit == (inner & exit)),
        (_cs.ic == cycle) and (cycle == (inner & cycle)),
        (cycle & bounce) == cycle,
        (cycle | bounce) == bounce,
    )):
        assert t, i
_enter, _within, _exit, _cycle, _pop = (
    _Int(enter), _Int(within), _Int(exit), _Int(cycle), _Int(1 << 15))
def parse_event_arg(events):
    if isinstance(events, int):
        events = (events,)
    events = event(reduce(operator.or_, events))
    selector = [_pop, None, '', None, '', None]
    for i, ev in ((1, _exit),(3, _within),(5, _enter)):
        if ev & events:
            selector[i] = ev
    selector = list(item for item in selector if item is not None)
    mask = event(events)
    return mask, selector
def event(n):
    """Keep only the lowest byte of an integer.
    This function is useful because bitwise operations in python
    yield integers out of the range(128), which represents walk events."""
    return n & 127
if sys.version_info < (3,):
    def bytes(x, **args):
        return x
    
def event_repr(_event_names):
    import base64, re, zlib
    s = """eNpVklEOwyAMQ2+D2r8CaX+4CyeJOPtsJ3SbtIYM8jDEXKWOq6wbAd+o5S7rGXXe
    E4PyyzW0cVzeziz1hvmG8vWU1cuyWJ1RGoTmmXQpeBeIiA9gy9UDZAd5qjTRvdhQyyxFRbf
    gA66+SO4/bx7RQtlEI+IL5b6VbSvbV7mrhOKmS2xxk7i2EI/ZGRlmv3fmLUwbBdgF9lc7wc
    zWTiNWUvjBAUBMdpnXnzui/Bk5r/0YnTgwoIRvHCtLWhZpVKzh4Txg1knHwi4cPZGeiEbF9
    GykX/QqjKJLHi3nOXAjNtafM8wKVLc311vjJFhD01PNUk2jYvo00iP6E+ao2er0Qbkz9frW
    S7i/byMIXpDGuDr9hzamWPD9MlUhWgSFdWbBavXMDdBzmTSqBmff6wdNK+td"""
    s = str(zlib.decompress(base64.b64decode(bytes(s, encoding="ascii"))))
    s = re.sub(r"\d", (lambda mo: _event_names[int(mo.group(0))]), s)
    s = re.sub(r"([|&^])", r" \1 ", s)
    s = tuple("event(%s)" % x for x in s.split(";"))
    def event_repr(n):
        """return a human readable, and evaluable representation of an event
        @ event: an integer (modulo 128)
        """
        return s[n & 127]
    return event_repr
event_repr = event_repr(_event_names) # overwrite event_repr()
class _MockDict(object):
    "Helper class for walk() in the tree mode"
    def __getitem__(self, key):
        pass
    def __setitem__(self, key, value):
        pass
    def __contains__(self, key):
        pass
 
def walk(node, gen_subnodes, event = enter, reverse_path = False, tree=True):
    """Traverse a tree or a graph based at 'node' and generate a sequence
    of paths in the graph from the initial node to the visited node.
    The arguments are
    
        @ node : an arbitrary python object used as root node.
        @ gen_subnodes : a function defining the graph structure. It must
            have the interface gen_subnodes(node) --> iterable containing
            other nodes. This function will be called with the initial
            node and the descendent nodes that it generates through
            this function.
        @ event: an integral value specifying which paths will be generated
            during the depth-first walk. This is usually a value obtained
            by composing the walk events (see below) with bitwise operators.
            For example passing event = event(enter|leaf|bounce) will
            generate inner nodes the first time they are entered, leaf
            nodes and all the nodes every time they are revisited during
            the walk.
        @ reverse_path: a boolean indicating that the path should be read
            from right to left (defaults to False).
        @ tree: a boolean indicating that the walked graph is a tree,
            which means that applying gen_subnodes() will only generate
            new nodes (defaults to True). Passing True if the graph
            is not a tree will walk multiple subgraphs several times,
            or lead to an infinite walk and a memory error if the graph
            contains cycles. When a False value is given, this function
            stores all the previoulsy visited nodes during the walk.
            When a True value is given, only the nodes in the current
            path are stored.
    
    Typical use:
        
        for path in walk(node, func, event(enter|leaf)):
            # this choice of events results in a preorder traversal
            visited = path[-1]
            if path.event & leaf:
                print(visited, 'is a leaf node!')
                
    The generated 'path' is a read-only sequence of nodes with path[0] being
    the base node of the walk and path[-1] being the visited node. If
    reverse_path is set to True, the path will appear from right to left,
    with the visited node in position 0. During the whole walk, the function
    generates the same path object, each time in a different state.
    Internally, this path is implemented using a collections.deque object,
    which means that indexing an element in the middle of the path (but not
    near both ends) may require a time proportional to its length.
    
    The generated paths have an attribute path.event which value is an
    integer in the range [0,128[ representing a bitwise combination of
    the base events (which are also integers) explained below
    
        enter:  the currently visited node is an inner node of the tree
                generated before this node's subgraph is visited.
        within: the currently visited node is an inner node generated after
                its first subgraph has been visited but before the other
                subgraphs.
        exit:   the currently visited node is an inner node generated after
                all its subgraphs have been visited.
        leaf:   the currently visited node is a leaf node.
        inner:  the currently visited node is an inner node
        cycle:  the currently visited node is an internal node already on
                the path, which means that the graph has a cycle. The subgraph
                based on this node will not be walked.
        bounce: the currently visited node is either an internal node which
                subgraph has already been walked, or a leaf already met.
                Subgraphs are never walked a twice with the argument tree=False.
    The actual events generated are often a combination of these events, for
    exemple, one may have a value of event(leaf & ~bounce). This attribute
    path.event is best tested with bitwise operators. For example to test if
    the walk is on a leaf, use 'if path.event & leaf:'.
    
    The constant events are also attributes of the walk function, namely
    (walk.enter, walk.within, ...)
    """
    mask, selector = parse_event_arg(event)
    isub = selector.index('', 1)
    ileft = selector.index('', isub + 1)
    tcycle = mask & cycle
    tleaf = mask & leaf
    tibounce = mask & bounce & inner
    tfbounce = mask & bounce & leaf
    tffirst = mask & ~bounce & leaf
    todo = deque((iter((node,)),))
    path = deque()
    const_path = ConstSequence(path)
    if reverse_path:
        ppush, ppop, ivisited = path.appendleft, path.popleft, 0
    else:
        ppush, ppop, ivisited = path.append, path.pop, -1
    less, more = todo.pop, todo.extend
    hist = _MockDict() if tree else dict()
    try:
        while True:
            sequence = todo[-1]
            if sequence.__class__ is _Int:
                less()
                if sequence is _pop:
                    # this node's subtree is exhausted, prepare for bounce
                    hist[path[ivisited]] = tibounce
                    ppop()
                else:
                    const_path.event = sequence
                    yield const_path
            else:
                try:
                    node = next(sequence)
                except StopIteration:
                    less()
                else:
                    ppush(node)
                    # if node in history, generate a bounce event
                    # (actually one of (leaf & bounce, inner & bounce, cycle))
                    if node in hist:
                        const_path.event = hist[node]
                        if const_path.event:
                            yield const_path
                        ppop()
                    else:
                        sub = iter(gen_subnodes(node))
                        try:
                            snode = next(sub)
                        except StopIteration:
                            hist[node] = tfbounce
                            if tleaf:
                                const_path.event = tffirst
                                yield const_path
                            ppop()
                        else:
                            # ajouter node 
                            hist[node] = tcycle
                            selector[ileft] = iter((snode,))
                            selector[isub] = sub
                            more(selector)
    except IndexError:
        if todo: # this allows gen_subnodes() to raise IndexError
            raise
for _e in _named_events:
    setattr(walk, _e.name, _e.value)
if __name__ == "__main__":
    
    def _graph_example(n=4):
        from string import ascii_uppercase as labels
        from random import Random
        n = min(n, 26)
        
        class Node(object):
            def __init__(self, letter):
                self.letter = str(letter)
                self.neigh = list()
            def __str__(self):
                return self.letter
            __repr__ = __str__
        
        # create a reproductible random graph
        nodes = [Node(x) for x in labels[:n]]
        ran = Random()
        ran.seed(6164554331563)
        neighmax = 3
        for n in nodes:
            n.neigh[:] = sorted((x for x in ran.sample(nodes, neighmax)
                                    if x is not n), key=lambda n: n.letter)
        #for n in nodes:
        #    print(n, ":", list(n.neigh))
        for path in walk(nodes[0], (lambda n: n.neigh), event(~0), tree=False):
            print(list(path), "{0:<7}".format(event_repr(path.event)))
        
    def _tree_example():
        # an example tree
        root = (
            ((1,2), (4,5), 6),
            (7, 9),
        )
    
        # a function to generates subnodes for this tree
        def subn(node):
            return node if isinstance(node, tuple) else ()
        
        # use of the walk() generator to traverse the tree
        for path in walk(root, subn, event(enter|exit|leaf)):
            print(list(path), "{0:<7}".format(event_repr(path.event)))
  
    _graph_example(7)
    #_tree_example()
       
""" example code output --->
# this example shows all the possible walk events for the graph shown
# in the attached image when starting from node A
[A] event(enter)
[A, B] event(enter)
[A, B, C] event(enter)
[A, B, C, D] event(enter)
[A, B, C, D, B] event(cycle)
[A, B, C, D] event(within)
[A, B, C, D, F] event(enter)
[A, B, C, D, F, C] event(cycle)
[A, B, C, D, F] event(within)
[A, B, C, D, F, G] event(enter)
[A, B, C, D, F, G, B] event(cycle)
[A, B, C, D, F, G] event(within)
[A, B, C, D, F, G, D] event(cycle)
[A, B, C, D, F, G, E] event(enter)
[A, B, C, D, F, G, E, C] event(cycle)
[A, B, C, D, F, G, E] event(within)
[A, B, C, D, F, G, E, D] event(cycle)
[A, B, C, D, F, G, E, G] event(cycle)
[A, B, C, D, F, G, E] event(exit)
[A, B, C, D, F, G] event(exit)
[A, B, C, D, F] event(exit)
[A, B, C, D] event(exit)
[A, B, C] event(within)
[A, B, C, G] event(inner & bounce)
[A, B, C] event(exit)
[A, B] event(within)
[A, B, E] event(inner & bounce)
[A, B, G] event(inner & bounce)
[A, B] event(exit)
[A] event(within)
[A, C] event(inner & bounce)
[A, G] event(inner & bounce)
[A] event(exit)
"""
