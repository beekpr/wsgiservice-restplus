# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from jsonschema import RefResolver, FormatChecker

from ._compat import OrderedDict
from .namespace import Namespace
from .swagger import Swagger
from .utils import default_id, camel_to_dash # deleted unpack

from .errors import SecurityError

from .wsgiservice_adaptors import get_resource_http_methods

# ### TODO: Would need to be readapted to RE_RULES = re.compile('({.*})')
# RE_RULES = re.compile('(<.*>)')

# List headers that should never be handled by Flask-RESTPlus
HEADERS_BLACKLIST = ('Content-Length',)

# Replaced output_json by None (cf. wsgiservice.Resource content negotiation)
DEFAULT_REPRESENTATIONS = [('application/json', None)]

import wsgiservice


class Api(object):
    '''
    The main entry point for the application.
    You need to initialize it with a Flask Application: ::

    >>> app = Flask(__name__)
    >>> api = Api(app)

    Alternatively, you can use :meth:`init_app` to set the Flask application
    after it has been constructed.

    The endpoint parameter prefix all views and resources:

        - The API root/documentation will be ``{endpoint}.root``
        - A resource registered as 'resource' will be available as ``{endpoint}.resource``

    :param str version: The API version (used in Swagger documentation)
    :param str title: The API title (used in Swagger documentation)
    :param str description: The API description (used in Swagger documentation)
    :param str terms_url: The API terms page URL (used in Swagger documentation)
    :param str contact: A contact email for the API (used in Swagger documentation)
    :param str license: The license associated to the API (used in Swagger documentation)
    :param str license_url: The license page URL (used in Swagger documentation)
    :param func default_id: The default Swagger Operation.operationId string generation function
        accepting a resource class and HTTP method string
    :param str endpoint: The API base endpoint (default to 'api).
    :param str default: The default namespace base name (default to 'default')
    :param str default_label: The default namespace label (used in Swagger documentation)
    :param str default_mediatype: The default media type to return
    :param bool validate: API-wide request validation setting (can be overridden by concrete methods).
    :param str prefix: API base_path occurring in Swagger specification but NOT in _path attributes of resources
    :param str doc: The documentation path. If set to a false value, documentation is disabled.
                (Default to '/')
    :param list decorators: Decorators to attach to every resource
    :param bool catch_all_404s: Use :meth:`handle_error`
        to handle 404 errors throughout your app
    :param dict authorizations: A Swagger Authorizations declaration as dictionary
    :param bool serve_challenge_on_401: Serve basic authentication challenge with 401
        responses (default 'False')
    :param FormatChecker format_checker: A jsonschema.FormatChecker object that is hooked into
    the Model validator. A default or a custom FormatChecker can be provided (e.g., with custom
    checkers), otherwise the default action is to not enforce any format validation.
    '''

    def __init__(self,
            version='1.0', title=None, description=None,
            terms_url=None, license=None, license_url=None,
            contact=None, contact_url=None, contact_email=None,
            authorizations=None, security=None, swagger_path='/swagger.json', default_id=default_id, #default='default', default_label='Default namespace',
            validate=None,
            tags=None, prefix='',
            decorators=None, # catch_all_404s=False, serve_challenge_on_401=False, # TODO FUL-3505
            format_checker=None,
            **kwargs): # TODO: FUL-3376 Delete kwargs
        self.version = version
        self.title = title or 'API'
        self.description = description
        self.terms_url = terms_url
        self.contact = contact
        self.contact_email = contact_email
        self.contact_url = contact_url
        self.license = license
        self.license_url = license_url
        self.authorizations = authorizations
        self.security = security
        self.default_id = default_id
        self._validate = validate          # Api-wide request validation setting
        self._swagger_path = swagger_path

        self._default_error_handler = None # TODO: FUL-3505
        self.tags = tags or []

        # TODO: FUL-3505
        # self.error_handlers = {
        #     ParseError: mask_parse_error_handler,
        #     MaskError: mask_error_handler,
        # }

        self._schema = None # cache for Swagger JSON specification
        self.models = {}
        self._refresolver = None
        self.format_checker = format_checker
        self.namespaces = []

        self.representations = OrderedDict(DEFAULT_REPRESENTATIONS)

        self.prefix = prefix

        self.decorators = decorators if decorators else []

        # TODO: FUL-3505
        # self.catch_all_404s = catch_all_404s
        # self.serve_challenge_on_401 = serve_challenge_on_401

        # TODO: FUL-3376 (probably deletable)
        self.resources = []


    # TODO: Make the Swagger specification resources configurable (such as e.g. with a predicate
    #       that specifies whether to include an endpoint in the documentation)
    def create_wsgiservice_app(self):
        '''
        Creates a :class:`wsgiservice.application.Application` instance from the resources owned by self (the namespaces of this Api instance)
        '''

        SwaggerResourceClass = generate_swagger_resource(api=self, swagger_path=self._swagger_path)

        self.resources.append((SwaggerResourceClass, self._swagger_path, {}))

        # Check for resource._path == url (Api.prefix ignored)
        for resource, url, _ in self.resources:
            if getattr(resource,'_path', None) is not None:
                if resource._path != url:
                    raise Exception # raise a path error exception due to inconsistent mount point

        return wsgiservice.get_app(
            {resource.__name__ : resource for resource, _, _ in self.resources})


    # NOTE: self.default_namespace deleted here as all namespaces must be added manually


    # TODO: FUL-3376 (probably deletable to do copy elision)
    ## Add resource, assigned urls and constructor named/kw-args to sequence of resources
    def register_resource(self, namespace, resource, url, **kwargs):

        kwargs['endpoint'] = default_endpoint(resource, namespace)

        self.resources.append((resource, url, kwargs))


    # NOTE: _register_view method deleted here
    # Constructed flask view function(s) from resource class (including binding of resource constructor to
    # named/kw-arguments), application of all Api-level decorators to the resulting view function and return
    # value transformation based on requested content type registering the view with the flask.Application
    # instance.

    # NOTE: default_endpoint method moved outside this instance (as not dependent on internal attributes)

    # Add namespace to list in this Api instance and this Api instance to list of Api objects
    # in namespace
    # # TODO: FUL-3505
    def add_namespace(self, ns):

        # Check whether namespace security requirements are contained in API security definitions
        if not self._security_requirements_in_authorizations(ns):
            raise SecurityError('Namespace security use inconsistent with Api security definitions in authorizations')

        if ns not in self.namespaces:
            self.namespaces.append(ns)
            if self not in ns.apis:
                ns.apis.append(self)

        # Copy all resources
        # TODO: FUL-3376 copy elision?
        for resource, url, kwargs in ns.resources:
            self.register_resource(ns, resource, url, **kwargs)

        # Copy all models
        # TODO: FUL-3376 copy elision?
        for name, definition in ns.models.items():
            self.models[name] = definition

        # TODO: FUL-3505
        # # Register error handlers
        # for exception, handler in ns.error_handlers.items():
        #     self.error_handlers[exception] = handler


    def _security_requirements_in_authorizations(self, ns):

        for resource, _, _ in ns.resources:
            for method in get_resource_http_methods(resource):
                method = getattr(resource, method)
                if hasattr(method, '__apidoc__'):
                    for security_requirement in method.__apidoc__.get('security', []):
                        if security_requirement not in self.authorizations:
                            return False
        return True


    # TODO: FUL-3376 Remove this at later stage (Api should become a namespace collection)
    def get_resources(self):
        '''Get resources held by this instance'''
        resources = {}
        for ns in self.namespaces:
            for resource, _, _ in ns.resources:
                resources[resource.__name__] = resource
        return resources


    # TODO: FUL-3376: replace prefix by a more reasonable name such as _base_path ###
    @property
    def base_path(self):
        '''
        The base path of the API

        :rtype: str
        '''
        return self.prefix

    def __schema__(self):
        '''
        The Swagger specifications/schema for this API

        :returns dict: the schema as a serializable dict
        '''
        if not self._schema:
            self._schema = Swagger(self).as_dict()
        return self._schema



    @property
    def refresolver(self):
        '''
        JSON schema model system reference resolver
        '''
        if not self._refresolver:
            self._refresolver = RefResolver.from_schema(self.__schema__)
        return self._refresolver


    # TODO: FUL-3376 (Remove if possible)
    ###  Retrieve URL path for a particular resource ###
    # To work with absolute URLs would need host name
    def url_for(self, resource, **values):
        '''
        Generates a URL to the given resource.
        '''

        for resource_class, url, _ in iter(self.resources):
            if resource == resource_class:
                return self.base_path + url.lstrip('/')
        else:
            return None



def generate_swagger_resource(api, swagger_path):
    '''
    Returns a wsgiservice Swagger documentation Resource class that binds the Api instance
    '''

    class SwaggerResource(wsgiservice.Resource):
        '''
        Resource for the Swagger specification of the bound Api
        '''
        _path = swagger_path

        def GET(self):
            self.type = 'application/json'
            return api.__schema__()

    return SwaggerResource


def default_endpoint(resource, namespace):
    '''
    Provide a default endpoint name for a resource on a given namespace.

    :param Resource resource: the resource modeling the endpoint
    :param Namespace namespace: the namespace holding the resource
    :returns str: An endpoint name
    '''
    endpoint = camel_to_dash(resource.__name__)
    return '{ns.name}_{endpoint}'.format(ns=namespace, endpoint=endpoint)
