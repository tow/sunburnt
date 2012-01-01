.. _contributing:

Contributing to Sunburnt
========================

Sunburnt development is carried out on `github <http://github.com/tow/sunburnt/>`_, and discussion takes places on the `mailing list <http://groups.google.com/group/python-sunburnt>`_.

Contributors are very welcome!

* we could always do with more documentation.

* bugs may be reported on `github <https://github.com/tow/sunburnt/issues>`_ - the more detailed the description the better!

* bug reports accompanied by patches are also welcome; even better is a patch including a testcase demonstrating the behaviour with and without the patch. See below (link) for notes on the testcases.

* feature requests can also be made through the `issue tracker <https://github.com/tow/sunburnt/issues>`_ - but development is primarily driven by the practicalities of the authors' needs.

* so feature requests including working patches are very much welcome!

Before putting a new feature into a release, though, it's important that the feature be accompanied by 

1. *Documentation* - what is the feature meant to do; if it corresponds directly to an underlying Solr feature, then link through to the appropriate part of the Solr wiki. Give a couple of examples of using the feature, and explain why and when it might be appropriate to use it.

2. *Tests*. As far as possible, every feature added should have tests added which thoroughly explore its behaviour. This is for two reasons; firstly so that it's clear, when the code is merged into a release, that the new code actually does work; and secondly, so that as further development continues, another contributro doesn't change something which has the end result of breaking the original feature code.

   Generally speaking, the only person who really understands the code well is the original author; they're the ones who wrote it, and they have a particular usecase in mind, and they have a particular understanding of what the code is intended to do. If no tests accompany the feature, then when it's merged for a release, the person making the release can't tell whether they've merged the code correctly. Even worse, other developers later on can't tell whether their proposed changes might conflict with the understanding of the code set up by the original author.

Documentation
=============

In writing sunburnt and open-sourcing it, the single thing which has done most to get other people using sunburnt is writing documentation.

Documentation can be written in several ways, but the most immediately useful sort is simple worked examples. They don't have to be elaborate, but should be illustrative:

1. why might you want to be using this aspect of the library/API?
2. If necessary/possible, provide a couple of example documents to be inserted into Solr for expected results to be given
3. Show the use of the feature as Python code that could be cut-and-pasted into Python terminal
4. Show the expected result of step 3.

If all these steps are in place, then it makes it much more likely that other people will actually use a new feature, which makes it much more useful!

For examples of such documentation, look at the chapter on :ref:`queryingsolr`. You don't need that much detail for every new feature, but the more we can illustrate the use of a feature, the better it will be used.

Tests
=====

The test suite is run using `nose <http://readthedocs.org/docs/nose/en/latest/>`_. To run the tests, make sure you have nose installed in your environment

::

 pip install nose

and from the sunburnt directory, execute the test runner

::

 sunburnt% nosetests
 ................................................................................................................................................................................................................................................................
 ----------------------------------------------------------------------
 Ran 258 tests in 0.312s

 OK

and you should see output like that above. (Note that the number of tests is correct as of release 0.6.)

Most of the testsuite is concerned with exercising an API method with various combinations of arguments. The best way to do this, I've found, is via the use of nose's test generators.

The outline of such a test is that:

* a particular method,
* when given a particular set of arguments
* will either:

  + return a given result, or
  + throw a particular exception.

Rather than write a whole lot of test cases essentially duplicating that pattern with different arguments of results, the tests in sunburnt compress all the testcases for a given method in the following way:

::

 specifications_for_method_tests = (
     ( (tuple, of, args), result_or_exception_class )
 )

Or in words, the specifications for the tests are a tuple of:

* for each test, a two-tuple

  + whose first member is a tuple of ordered arguments, and
  + whose second member is either:

    + the expected return value, or
    + the exception class expected to be thrown.

From this list of specifications, we *generate* a sequence of tests. A nose test generator is a function (taking no arguments), whose name begins with *test_*, which will yield up a list of tests. A typical test generator might look like

::

 def test_method():
     for args, result_or_exception in specification_for_method_tests:
         yield check_method, args, result_or_exception

So the test generator iterates over all the specification, each time yielding 'check_method', as well as the first and second member of the two-tuple representing each test.

'check_method' is a callable, taking two arguments, which simply performs the test given the specification. In this case, the method being tested is just *method*.

::

 def check_method(args, result_or_exception):
     if not isinstance(result_or_exception, Exception):
         assert method(*args) == result_or_exception, "Wrong result"
         return
     try:
         method(*args)
     except result_or_exception, e:
         return
     except:
         assert False, "Wrong exception thrown"
     assert False, "No exception thrown"


The above is then the general pattern of most tests:

1. a test specification, consisting of a list of tuples specifying arguments and expected results, 
2. a test generator to generate all the tests from the specification
3. the function which actually does the checking.

This pattern is not adhered to strictly throughout the testsuite, but in nearly all cases, the above is the outline of what is being achieved.

In some cases, there may be one-off tests which require more setup and less iteration.

One difficulty in writing tests is when the function is intended to interact with a running solr instance. 

Checking internal state
~~~~~~~~~~~~~~~~~~~~~~~

Sunburnt is written with several aids to debugging and testing, which allow you to check some parts of its logic without needing a Solr instance to hand. For example, when constructing a Solr query using the sunburnt APIs, we need to check that we are generating the correct output without having to feed it to a running instance.

So the SolrQuery object has a method, ``params()``, which tells you what the parameters would be, if you passed them to Solr. When writing tests for the sunburnt query APIs, we construct the queries, and then test their ``params()`` - so we don't need a running Solr instance to run the testsuite.

Mocking out external dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes, though, you need to mock out part of a Solr instance; this happens either when you want to check logic for interacting with Solr output, or when you need to check an end-to-end set of functionality.

Sunburnt is written to support dependency injection, so that mock connections, or mock interfaces can be used.

There's an example of this in ``sunburnt/test_sunburnt.py``. We need to test some of the pagination code, which wraps both query construction and result decoding. Inspecting sunburnt internals won't give us enough of a picture; we need something to act as a Solr instance. In this case, we create a ``PaginationMockConnection`` which we have setup to respond with fake but well-specified results, given the input we need to test.

So, with a mocked-out solr instance, with well-defined behaviour, we can then test all the code for generating queries to it, and for acting on its output.


