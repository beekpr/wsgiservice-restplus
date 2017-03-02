import logging
import sys

from wsgiservice import Resource, raise_404, raise_403, raise_201, raise_409, raise_200, validate

from wsgiservice_restplus import namespace, fields
from wsgiservice_restplus.api import Api

logging.basicConfig(level=logging.INFO, stream=sys.stderr)

api = Api(
    version='1',
    contact_url=None,
    contact_email=None,
    doc=False,
    tags=None,
    prefix='/',
    default_mediatype='application/json',
    catch_all_404s=False,
    serve_challenge_on_401=False,
)

ping_ns = namespace.Namespace(
    name="Ping Pong Endpoint",
    description="Test endpoint for trying out the request calls and swagger documentation",
    internal=False
)

api.add_namespace(ping_ns)

def Integer(value):
    """Converts value to Integer"""
    return int(value)



# ===== MODELS: ======

tesball_payload = ping_ns.model(
    "Testball Payload",
    {
        "good": fields.Boolean(
            description="Flag indicating that the ball was served very well.",
            example=True
        )
    }
)


pong_model = ping_ns.model(
    "Pong Response",
    {
        "good": fields.String(
            description="Some snappy response from receiving a ping request",
            example="Wow, that was a nice shot!"),

        "bad": fields.String(
            description="Some BAD response from receiving a ping request",
            example="Wow, that was a BAAAAAAD shot!")
    }
)


ball_model = ping_ns.model(
    "ball model",
    {
        "ball": fields.Boolean(
            description="True means a ball was decent, False means the ball was weak!"
        )
    }
)

ball_count_model = ping_ns.model(
    "ball count model",
    {
        "rally": fields.Integer(
            description="Number of a rally (URL variable)"
        ),
        "balls": fields.Integer(
            description="Number of balls exchanged in a rally (received in a request query)"
        )
    }
)

# ===== ENDPOINTS ======


@ping_ns.route('/testball', internal=True)
class Testball(Resource):
    """Example endpoint function for TESTING purposes only!"""

    def GET(self):
        return "This is a test ball endpoint - please make a POST request with good or bad " \
               "(strings)"

    @ping_ns.payload_model(tesball_payload)
    @ping_ns.marshal_with(pong_model)
    def POST(self, good=False, bad=True):
        """Returns a ball response comment.
        Praises if ball=True or mocks if ball=False (or else)"""

        logging.info("BALL WAS good:{} bad: {}".format(good, bad))

        if good:
            return {"response": "Wow, that was a nice shot!"}
        else:
            return {"response": "Dread lord, you're calling this a serve? ;p"}


@ping_ns.route('/ping')
class Ping(Resource):
    """Example endpoint function for TESTING purposes only!"""

    def GET(self):
        """Returns a simple ping-pong dictionary"""
        return {"what?": 'did you just ping me?'}

    @ping_ns.expect(ball_model)
    @ping_ns.payload_param(name='ball', doc='Switch to make the ball good (True) or bad (False)', mandatory=False)
    @ping_ns.marshal_with(pong_model)
    def POST(self, ball):
        """Returns a ball response comment.
        Praises if ball=True or mocks if ball=False (or else)"""

        logging.info("BALL WAS {}".format(ball))

        if ball is True:
            return {"response": "Wow, that was a nice shot!"}
        else:
            return {"response": "Dread lord, you're calling this a serve? ;p"}


@ping_ns.path_param(name='rally', description='RALLY NUMBER (hybrid)', convert=Integer)
@ping_ns.route('/ping/{rally}')
class Pong(Resource):

    @ping_ns.query_param(name='balls', doc='NUMBER OF BALLS EXCHANGED (HYBRYD!)')
    @ping_ns.marshal_with(ball_count_model)
    def GET(self, rally, balls=1):
        """Returns a number of balls in a given rally"""

        return {"nr of balls exchanged": balls, "rally": rally}


test_swagger = api.__schema__()

print test_swagger

if __name__ == "__main__":

    app = api.create_wsgiservice_app()

    from wsgiref.simple_server import make_server
    print "Running on port 8002"

    make_server('', 8002, app).serve_forever()
