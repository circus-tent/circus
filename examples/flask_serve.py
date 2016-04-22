import requests
from flask import Flask, make_response
app = Flask(__name__)
app.debug = True


@app.route("/")
def pdf():
    pdf = requests.get('http://localhost:5000/file.pdf')
    response = make_response(pdf.content)
    response.headers['Content-Type'] = "application/pdf"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=8181, host='0.0.0.0')
