import logging
import sys

from wsgiservice import Resource, raise_404, raise_403, raise_201, raise_409, raise_200

from wsgiservice_restplus import namespace, fields
from wsgiservice_restplus.api import Api

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

posts_database = {
    '0': {
            "id": 0,
            "text": "Welcome to the Beekeeper!",
            "title": "Welcome message",
            "sticky": True,
            "locked": False
          }
}

post_core = {

    'title': fields.String(
        pattern=r'[-0-9a-zA-Z]{36}',
        description='Title of the post',
        example='Welcome!',
        required=True),

    'text': fields.String(
        pattern=r'[-0-9a-zA-Z]',
        description='Text content of the post',
        example='Well hello everybody! THis is ...',
        required=True),

    'locked': fields.Boolean(
        description="Boolean switch, makes a post locked for comments.",
    ),

    'sticky': fields.Boolean(
        description="Boolean switch, makes a post pinned to the top of the stream.",
    ),
}

post_with_id = post_core.copy()
post_with_id["id"] = fields.Integer(
            desciption="Unique index integer number (used as key to store the post in dictionary)"
)


#-----------------------------
# Create NAMESPACE and MODELS:
#-----------------------------

ns = namespace.Namespace(
    name='store_interface_ns',
    description='An associative (key,document) store',
    path='/',
)

post_core_model = ns.model(
    "post_core_model",
    post_core
)

post_model = ns.model(
    "post_model",
    post_with_id
)


#-----------------------------
#     Define ENDPOINTS:
#-----------------------------


@ns.route('/posts')
class Posts(Resource):
    """Provides access to the list of all posts in a dictionary"""

    @ns.response(code=404, description="No posts were found!")
    @ns.marshal_list_with(post_model)
    def GET(self):
        """Returns a dictionary of all the posts stored on server.
        Each post element is a dictionary with four `text`, `title`, `sticky` and `locked` parameters.
        """
        if len(posts_database.values()) == 0:
            raise_404(self)
        else:
            return posts_database.values()

    @ns.expect(post_core_model)
    @ns.marshal_with(post_model)
    def POST(self):
        """Adds a new post entry to the posts_dict - automatically assigns it an index `id` value
        and returns the post object with the id"""

        id = len(posts_database)
        post = self.request.POST
        post['id'] = id
        posts_database['id'] = post

        return posts_database['id']


@ns.path_param(name="id", doc="The ID of an existing post", type=int) #<-- Defines the id query param for all methods
@ns.route('/post/{id}')
class Post(Resource):

    @ns.marshal_with(post_model)
    @ns.response(code=404, description="Post with the requested ID does not exist")
    def GET(self, id):
        """Returns a post from a dictionary using the provided id (from query)"""

        try:
            return posts_database[id]
        except KeyError as e:
            self.response.body = "post id {} not found! {}".format(id, e)
            raise_404(self)

    @ns.expect(post_core_model)
    @ns.marshal_with(post_model)
    @ns.response(code=404, description="Post with specified ID does not exist")
    def PUT(self, id):
        """Replaces the content of an existing post with the provided new content."""

        if id not in posts_database:
            raise_404(self)
        else:
            post_content = self.request.PUT
            post_content['id'] = id

            posts_database[id] = post_content
            return posts_database[id]


    @ns.response(code=404, description="Post with requested ID was not found")
    def DELETE(self, id):
        """Deletes a post with a specified id."""

        try:
            del posts_database[id]
        except KeyError:
            raise_404(self)

        raise_200(self)

    @ns.deprecated
    @ns.response(code=409, description="ID specified in the post payload already exists.")
    @ns.expect(post_core_model)
    @ns.marshal_with(post_model)
    def POST(self, id):
        """DEPRECATED METHOD - DO NOT USE - can potentially introduce errors.
        Old way of posting with the ability to specify and id in the payload (must not conflict with current ids!)
        """

        post_content = dict(self.request.POST)

        if id in posts_database:
            self.response.body_raw = {'error': "Id {} already in use! Please use POST request to /posts "
                                               "instead to have a non-conflicting id assigned automatically."}
            raise_409(self)
        else:
            posts_database[id] = post_content
            return post_content[id]



#-----------------------------
#     Create Api and App:
#-----------------------------


security_defintions = {

    'basic_auth': {
        "type": "basic",
        "description": "Basic username & password OAuth2 authentication, "
                       "eg. Authorization: Basic QWxhZGRpbjpPcGVuU2VzYW1l. "
                       "Request returns a token string",
    },

    'api_token': {
        'type': 'apiKey',
        'name': 'Authorization',
        'in': 'header',
        'description': 'API token authenatication: '\
                       'Enter the token you received from http://... in this format:'
                       ' \"Token xwdt...\"'
    }
}

api_wide_security = ['basic_auth', 'api_token']

api = Api(
    version='1',
    contact_url=None,
    contact_email=None,
    authorizations=security_defintions,
    security=api_wide_security,
    doc=False,
    tags=None,
    prefix='/',
    default_mediatype='application/json',
    catch_all_404s=False,
    serve_challenge_on_401=False,
)

api.add_namespace(ns)
app = api.create_wsgiservice_app()


if __name__ == "__main__":

    from wsgiref.simple_server import make_server
    print "Running on port 8001"
    make_server('', 8001, app).serve_forever()
