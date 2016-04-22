# import sys
# import StringIO

from flask import Flask
app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    # sys.stderr = sys.stdout = StringIO.StringIO()
    app.run(port=8000)
