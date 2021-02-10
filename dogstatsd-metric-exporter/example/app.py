from os import getenv

from flask import Flask, Response, request
from flask.helpers import make_response

from example import metrics

app = Flask(__name__)


@app.route("/")
def index_view():
    args = request.args
    environment: str = args.get("env", "default")
    labels = {"environment": environment}

    metrics.requests_counter.add(1, labels)

    if request.content_length is not None:
        metrics.request_body_length.record(request.content_length, labels)

    response: Response = make_response(labels)
    metrics.response_body_length.record(response.content_length, labels)
    return response


if __name__ == "__main__":
    HOST = getenv("APP_HOST", "127.0.0.1")
    PORT = int(getenv("APP_PORT", 5542))
    print(f"Starting application at: http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT)
