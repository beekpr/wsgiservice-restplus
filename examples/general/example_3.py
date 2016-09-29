"""
The store service is a simple document store. It stores key/value pairs on
the documents. This is currently a dummy implementation with ony in-memory
storage.
"""

import uuid
from wsgiservice import *
import logging
import sys

from exampleslib.utils import data, update_document, token_authentication
from wsgiservice_restplus import namespace, fields
from wsgiservice_restplus.api import Api

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)




api = Api(
    version='1.0',
    title='Document store REST API',
    description='This API provides access to a simple in-memory document store',
    contact='Maintainer name',
    contact_url='beekeeper.io',
    contact_email='maintainer@beekeeper.io',
    default='default',
    default_label='Default namespace',
    prefix='/documents/',
    default_mediatype='application/json',
    doc='/',
    security=None,
    tags=None,
    validate=None,
    terms_url=None,
    license=None,
    license_url=None,
    authorizations=None
)


# Namespace:
ns = namespace.Namespace(
    name='store_interface',
    description='An associative (key,document) store',
    path='/ns_path/')


doc_model = ns.model(
    'doc_model',
    {
        'doc': fields.String(
            description='The document',
            example='Some document goes here...')
    }
)

id_model = ns.model(
    'id_model',
    {
        'id': fields.String(
            pattern=r'[-0-9a-zA-Z]{36}',
            description='UUID of key-document pair',
            example='3c805c7c-9ff0-4879-8eb7-d2eee97ca39d')
    }
)

id_doc_model = ns.clone('id_doc_model', id_model,doc_model)


id_saved_model = ns.inherit(
    'id_saved_model',
    id_model,
    {
        'saved': fields.Boolean(
            description='Storage status',
            example='True')
    }
)

error_model = ns.model(
    'error',
    {
        'error': fields.String(
            description='Description of the error',
            example='The error was ...')
    }
)



# -----------------
#    ENDPOINTS
# -----------------

@validate('id', re=r'[-0-9a-zA-Z]{36}', doc='User ID, must be a valid UUID.')
@ns.route('/{id}')
@ns.param(name='id', description='User ID, must be a valid UUID.')
class Document(Resource):
    """
    Represents an individual document in the document store.

    The storage is only persistent in-memory, so it will go away when the service is
    restarted.
    """
    NOT_FOUND = (KeyError,)

    @ns.response(code=200, description='Returned requested document', model=id_doc_model)
    @ns.response(code=404, description='Not found', model=error_model)
    def GET(self, id):
        """Return the document indicated by the ID."""
        return data[id]

    @ns.response(code=200, description='Deleted specified document')
    def DELETE(self, id):
        """Delete the document indicated by the ID."""
        del data[id]


@ns.route('/')
class Documents(Resource):

    @ns.security('api_token')
    @ns.expect(doc_model)
    @ns.param(name='doc', description='Document to post.', _in='formData')    # could be replaced by @ns.expect()
    @ns.response(code=201, description='Document posted', model=id_saved_model)
    @ns.response(code=401, description='Authentication error', model=error_model)
    def POST(self):
        """Create a new document, assigning a unique ID.
        Parameters are passed in as key/value pairs in the POST data.
        """
        if not token_authentication(self.request):
            msg = 'Please authenticate'
            raise_401(self, msg,msg)

        id = str(uuid.uuid4())
        # TODO: Parse body parameter of self.request

        self.response.body_raw = update_document(id, self.request.POST)
        raise_201(self, id)



# Add the namespace to the api object:
api.add_namespace(ns)

# Application factory using the resources owned by the Api instance instead of app = get_app(globals())
app = api.create_wsgiservice_app()


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print "Running on port 8001"
    make_server('', 8001, app).serve_forever()