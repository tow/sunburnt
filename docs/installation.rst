.. _installation:

Installing Sunburnt
===================

Sunburnt's current release is `0.6`.

You can install sunburnt via pip, you can download a release, or you
can pull from the git repository.

To use sunburnt, you'll need an Apache Solr installation. Sunburnt
currently requires at least version 1.4 of Apache Solr.


Using pip
---------

If you have `pip <http://www.pip-installer.org>`_ installed, just type:

::

 pip install sunburnt

If you've got an old version of sunburnt installed, and want to
upgrade, then type:

::

 pip install -U sunburnt

That's all you need to do; all dependencies will be pulled in automatically.


Using a downloaded release
--------------------------

You can get versions of sunburnt from pypi.

::
 wget http://pypi.python.org/packages/source/s/sunburnt/sunburnt-0.6.tar.gz
 tar xzf sunburnt-0.6.tar.gz
 cd sunburnt-0.6
 setup.py install

Before using sunburnt, you need to make sure you have `httplib2
<http://code.google.com/p/httplib2/>`_ and `lxml <http://lxml.de>`_ installed.


Using git
---------

You can install the latest code from github by doing

::

 git clone http://github.com/tow/sunburnt.git
 cd sunburnt
 setup.py install

Again, you'll need to have `httplib2
<http://code.google.com/p/httplib2/>`_ and `lxml <http://lxml.de>`_ installed.

Note that there's no guarantees that the latest git version will be
particularly stable!


Installing and configuring Solr
===============================

If you're using sunburnt to connect to an existing Solr installation,
then you won't need further instructions.

Otherwise, the solr wiki contains `helpful instructions on installing and
configuring Solr
<http://wiki.apache.org/solr/FrontPage#Installation_and_Configuration>`_,
and you can set up a simple server by following the `tutorial <http://lucene.apache.org/solr/tutorial.html>`_.
