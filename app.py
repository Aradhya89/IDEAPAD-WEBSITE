# from flask import Flask , render_template , request
from flask import Flask , render_template, request, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
import os
import dotenv



dotenv.load_dotenv()


app = Flask(__name__)


app.secret_key = os.getenv("SECRETKEY")

# authenticator init.
oauth = OAuth(app)

# google authenticator setup
google = oauth.register(
    name='google',
    client_id=os.getenv("Client_id"),
    client_secret=os.getenv("Client_Secret"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


# home page
@app.route("/")
def home():
    userdata = session.get("userdata",None)
    return render_template("indextemp.html", user = userdata)



@app.before_request
def require_login():    
    allowed_routes = ["login","home","googlelogin","callback","logout"]

    if request.endpoint in allowed_routes:
        return

    if not session.get("user"):
        return redirect(url_for("login"))
        # return redirect(url_for("login", next=request.path))



# login page
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
    print(data) #just printing the data only here -> no database, no storing
    session["userdata"] = data
    session["user"] = data["name"]
    session["email"] = data["email"]
    session["picture"]  = data["picture"]
    return redirect(url_for("home"))


@app.route("/registration")
def eventform():
    userdata = session.get("userdata")
    return render_template("registration.html", user = userdata)

@app.route("/formdata",methods = ["POST"])
def formdata():
    data = request.get_json()
    print(data)#for debbuging
    return "successful"
    

@app.route("/logout")
def logout():
    if session.get("user"):
        session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":      
    app.run(host="0.0.0.0", port=8080, debug=True)