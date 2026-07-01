from flask import Flask , render_template
# from flask import Flask , render_template, request, redirect, session 
from authlib.integrations.flask_client import OAuth
import os
import dotenv



dotenv.load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRETKEY")


@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)