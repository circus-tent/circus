# import resource

# resource.setrlimit(resource.RLIMIT_NOFILE, (100, 100))

from flask import Flask
app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"


if __name__ == "__main__":
    app.run(debug=True, port=8181, host='0.0.0.0')
