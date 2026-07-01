# from flask import Flask , render_template , request
from flask import Flask , render_template, request, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
import os
import dotenv



dotenv.load_dotenv()


app = Flask(__name__)


app.secret_key = os.getenv("SECRETKEY")
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.getenv("Client_id"),
    client_secret=os.getenv("Client_Secret"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")



#google login account window
@app.route("/googlelogin")
def googlelogin():
    return google.authorize_redirect(
        url_for("callback", _external=True),
        prompt="select_account"  
    )

#data processing after the google login
@app.route("/callback")
def callback():
    token = google.authorize_access_token()

    resp = google.get("https://www.googleapis.com/oauth2/v3/userinfo")
    data = resp.json()
    pri
    return redirect("/login")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)