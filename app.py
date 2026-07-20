# from flask import Flask , render_template , request
from flask import Flask , render_template, request, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
import os
import dotenv
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from flask import g
from psycopg2.extras import RealDictCursor



app = Flask(__name__)
dotenv.load_dotenv()


app.secret_key = os.getenv("SECRETKEY")


DATABASE_URL = os.getenv("DATABASE_URL")

db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    dsn=DATABASE_URL
)

def get_db():
    if "db" not in g:
        g.db = db_pool.getconn()
    return g.db

@app.teardown_appcontext
def close_db(exception):
    conn = g.pop("db", None)

    if conn is not None:
        db_pool.putconn(conn)




class database:
    def tableformation():
        conn = get_db()

        with conn.cursor() as cur:

            cur.execute("""
                            CREATE TABLE if not exists users (
    email VARCHAR(255) PRIMARY KEY,

    google_id VARCHAR(50) UNIQUE NOT NULL,

    full_name VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),

    profile_picture TEXT,

    email_verified BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    last_login TIMESTAMPTZ DEFAULT NOW())

            """)

        conn.commit()



    def save_user(user):
        conn = get_db()

        with conn.cursor( ) as cur:

            cur.execute("""
                INSERT INTO users(
                    email,
                    google_id,
                    full_name,
                    first_name,
                    last_name,
                    profile_picture,
                    email_verified
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)

                ON CONFLICT(email)

                DO UPDATE SET

                    full_name = EXCLUDED.full_name,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    profile_picture = EXCLUDED.profile_picture,
                    email_verified = EXCLUDED.email_verified,
                    last_login = NOW();

            """, (

                user["email"],
                user["sub"],
                user["name"],
                user.get("given_name"),
                user.get("family_name"),
                user.get("picture"),
                user.get("email_verified")

            ))

        conn.commit()



# authenticator init.
oauth = OAuth(app)

with app.app_context():
    database.tableformation()

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
    event_date = "2026-08-20T10:00:00"
    # f"{date}T{time}"
    userdata = session.get("userdata",None)
    return render_template("index.html", user = userdata, event_date = event_date )



@app.before_request
def require_login():    
    allowed_routes = ["login","home","googlelogin","callback","logout","static"]

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
    # print(data) #just printing the data only here -> no database, no storing
    session["userdata"] = data
    session["user"] = data["name"]
    database.tableformation()
    database.save_user(data)
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