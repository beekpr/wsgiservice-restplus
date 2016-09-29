=======================================
WSGI Service RestPlus (NEEDS UPDATING!)
=======================================


Flask-RESTPlus is an extension for `wsgiservice`_ that adds support for quickly building REST APIs.
Flask-RESTPlus encourages best practices with minimal setup.
If you are familiar with Flask, Flask-RESTPlus should be easy to pick up.
It provides a coherent collection of decorators and tools to describe your API
and expose its documentation properly using `Swagger`_.


Compatibility
=============

wsgiservice_restplus requires Python 2.7+ and the following libraries:

* pytz
* jsonschema
* six>=1.3.0
* aniso8601>=0.82
* WsgiService


Installation
============

You can install wsgiservice_restplus (along with all its dependencaies if abent) with the following command:

.. code-block:: console

    $ python setup.py install clean



Quick start
===========

With Flask-Restplus, you only import the api instance to route and document your endpoints.

.. code-block:: python

    from wsgiservice_restplus import Api, Resource, fields



