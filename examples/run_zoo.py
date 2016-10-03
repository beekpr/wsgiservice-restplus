from zoo import api

app = api.create_wsgiservice_app()

if __name__ == "__main__":

    from wsgiref.simple_server import make_server
    print "Running on port 8001"
    make_server('', 8001, app).serve_forever()