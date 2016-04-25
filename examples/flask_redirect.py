from flask import Flask, redirect, make_response
app = Flask(__name__)
app.debug = True


@app.route("/file.pdf")
def file():
    with open('file.pdf', 'rb') as f:
        response = make_response(f.read())
        response.headers['Content-Type'] = "application/pdf"
        return response


@app.route("/")
def page_redirect():
    return redirect("http://localhost:8000")


if __name__ == "__main__":
    app.run(debug=True, port=8181, host='0.0.0.0')
