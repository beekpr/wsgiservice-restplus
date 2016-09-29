"""The store service is a simple document store. It stores key/value pairs on
the documents. This is currently a dummy implementation with ony in-memory
storage.
"""

import logging
import sys
import uuid

from wsgiservice import *

from exampleslib.utils import data, put_document
from wsgiservice_restplus import namespace, fields
from wsgiservice_restplus.api import Api

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

# ----------------------
#       API SETUP:
# ----------------------

ns = namespace.Namespace(
    name='store_interface_ns',
    description='An associative (key,document) store',
    path='/',
)


id_model = ns.model(
    'id',
    {
        'id': fields.String(
            pattern=r'[-0-9a-zA-Z]{36}',
            description='UUID of key-document pair',
            example='3c805c7c-9ff0-4879-8eb7-d2eee97ca39d')
    }
)

doc_model = ns.inherit(
    'doc_model',
    {
        'doc': fields.String(
            description='The document',
            example='Some document goes here...')
    }
)

id_saved_model = ns.clone(
    'id_saved_model',
    id_model,
    {
        'saved': fields.Boolean(
            description='Storage status',
            example='True')
    }
)


# ----------------------
#   GLOBAL SETTINGS
# ----------------------

#Swagger Security Scheme:
security_defintions = {
    'basic_auth': {'type': 'basic'},
    'api_token': {
        'type': 'apiKey',
        'name': 'Authorization',
        'in': 'header',
        'description': 'API token authenatication: '\
        'Enter the token you received from http://... in this format: \"Token xwdt...\"'
    }
}

# API wide applied security settings (list of security schemes to authorize with the API
# (logical OR is implicitely used between list elements))
# It is then assembled to a Swagger Security Requirement object by documentation generator
api_wide_security = ('api_token', 'basic_auth')


# Note: the URL prefix for mounting the wsgiservice.Application instance to the URLMap must be
# retrieved from the Api instance via Api.base_path() in order to enforce consistency between
# application and documentation
api = Api(
    version='1',
    contact_url=None,
    contact_email=None,
    authorizations=security_defintions, security=api_wide_security, doc='/',
    tags=None,
    prefix='/',  # NOTE the special prefix as the base_path
    default_mediatype='application/json',
    catch_all_404s=False,
    serve_challenge_on_401=False,
    title=None,
    description=None,
    terms_url=None,
    license=None,
    license_url=None,
    contact=None,
    validate=None,
    decorators=None,
    format_checker=None
)


#----------------------
#      ENDPOINTS
#----------------------

@ns.route('/{id}')
@ns.param(name='id', description='User ID, must be a valid UUID.')
@validate('id', re=r'[-0-9a-zA-Z]{36}', doc='User ID, must be a valid UUID.')
class Document(Resource):
    """Represents an individual document in the document store. The storage
    is only persistent in-memory, so it will go away when the service is restarted.
    """
    NOT_FOUND = (KeyError,)

    @ns.expect(id)
    @ns.security('basic_auth','api_key')
    @ns.response(code=200, description='Returned requested document', model=None)
    def GET(self, id):
        """Returns the document indicated by the ID."""
        return data[id]

    @ns.expect(doc_model)
    @ns.param(name='doc', description='Document replacing old document.', _in='formData')
    @ns.marshal_with(id_saved_model, code=200, description='Document updated')
    @ns.security('basic_auth')
    def PUT(self, id):
        """Overwrite or create the document indicated by the ID. Parameters
        are passed as key/value pairs in the POST data."""
        return put_document(id, self.request.POST)

    def DELETE(self, id):
        """Delete the document indicated by the ID."""
        del data[id]


@ns.route('/')
class Documents(Resource):

    @ns.expect(doc_model)
    @ns.deprecated
    @ns.param(name='doc', description='Document to post.', _in='formData')
    @ns.response(code=201, description='Document posted', model=id_saved_model)
    def POST(self):
        """Create a new document, assigning a unique ID. Parameters are
        passed in as key/value pairs in the POST data."""

        id = str(uuid.uuid4())
        self.response.body_raw = put_document(id, self.request.POST)
        raise_201(self, id)



# ---- SETUP ----


api.add_namespace(ns)

# wsgiservice.Application factory using the resources owned by the Api instance
app = api.create_wsgiservice_app()


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print "Running on port 8001"
    make_server('', 8001, app).serve_forever()
