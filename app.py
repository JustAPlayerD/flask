from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello Flask"

@app.route("/test")
def test():
    return "This is test"

@app.route("/html")
def html():
    return render_template('/home.html')

if __name__ == "__main__":
    app.run()
