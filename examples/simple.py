import logging
import sys

from wsgiservice import *

from wsgiservice_restplus import namespace, fields
from wsgiservice_restplus.api import Api

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

posts_dict = {
    '0': {
            "id": 0,
            "text": "Welcome to the Beekeeper!",
            "title": "Welcome message",
            "sticky": True,
            "locked": False
          }
}

# Create NAMESPACE:

ns = namespace.Namespace(
    name='store_interface_ns',
    description='An associative (key,document) store',
    path='/',
)

post_core_model = ns.model(
    "post_core_model",
    {
        'title': fields.String(
            pattern=r'[-0-9a-zA-Z]{36}',
            description='Title of the post',
            example='Welcome!'),

        'text': fields.String(
            pattern=r'[-0-9a-zA-Z]{300}',
            description='Text content of the post',
            example='Well hello everybody! THis is ...'),

        'locked': fields.Boolean(
            description="Boolean switch, makes a post locked for comments.",
        ),

        'sticky': fields.Boolean(
            description="Boolean switch, makes a post pinned to the top of the stream.",
        ),
    }
)

post_model = ns.model(

    "post_model",
    {
        "id": fields.Integer(
            desciption="Unique index integer number (used as key to store the post in dictionary)" ),

        'title': fields.String(
            pattern=r'[-0-9a-zA-Z]{36}',
            description='Title of the post',
            example='Welcome!'),

        'text': fields.String(
            pattern=r'[-0-9a-zA-Z]{300}',
            description='Text content of the post',
            example='Well hello everybody! THis is ...'),

        'locked': fields.Boolean(
            description="Boolean switch, makes a post locked for comments.",
        ),

        'sticky': fields.Boolean(
            description="Boolean switch, makes a post pinned to the top of the stream.",
        ),
    }
)


#
# # Create Field Dictionaries:
#
# post_core_dict = {
#
#     'title': fields.String(
#         pattern=r'[-0-9a-zA-Z]{36}',
#         description='Title of the post',
#         example='Welcome!'),
#
#     'text': fields.String(
#         pattern=r'[-0-9a-zA-Z]{300}',
#         description='Text content of the post',
#         example='Well hello everybody! THis is ...'),
#
#     'locked': fields.Boolean(
#         description="Boolean switch, makes a post locked for comments.",
#     ),
#
#     'sticky': fields.Boolean(
#         description="Boolean switch, makes a post pinned to the top of the stream.",
#     ),
# }
#
# post_dict = {k: v for k, v in post_core_dict.items()}
# post_dict['id'] = fields.Integer(
#     desciption="Unique index integer number (used as key to store the post in dictionary)"
# ),
#
# # Create MODELs:
#
# # without 'id' parameter
# post_core_model = ns.model(
#     "post_core_model",
#     post_core_dict
# )
#
# # with 'id' parameter
# post_model = ns.model(
#     "post_model",
#     post_dict
# )



# Define ENDPOINTS:


@ns.route('/posts')
class Posts(Resource):
    """Provides access to the list of all posts in a dictionary"""

    @ns.marshal_list_with(post_model)
    def GET(self):
        """Returns a dictionary of all the posts stored on server.
        Each post element is a dictionary with four `text`, `title`, `sticky` and `locked` parameters.
        """
        logging.info("got GET Request ...")
        return posts_dict.values()

    @ns.expect(post_core_model)
    @ns.marshal_with(post_model)
    def POST(self):
        """Adds a new post entry to the posts_dict - automatically assigns it an index `id` value
        and returns the post object with the id"""

        post_content = dict(self.request.POST)
        id = len(posts_dict)
        posts_dict[id] = post_content

        return post_content[id]


@ns.route('/posts/{id}')
class Post(Resource):

    @ns.param(name='id', description="Id of the post to retrieve", _in='query')
    def GET(self, id):
        """Returns a post from a dictionary using the provided id (from query)"""
        return posts_dict[id]

    @ns.param(name='id', description='Id of the post', _in='query')
    @ns.param(name='post_content', description='json object with the post definition', _in='query')
    def PUT(self, id, post_content):
        """Edits an existing post with provided new content."""
        pass

    @ns.deprecated
    @ns.param(name='id', description='Old way to create a post!', _in='query')
    def POST(self, id):
        """Old way of posting with the ability to specify and id - DEPRECATED!"""
        posts_dict['id'] = self.request.POST[id]


security_defintions = {
    'basic_auth': {
        "type": "basic"
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
