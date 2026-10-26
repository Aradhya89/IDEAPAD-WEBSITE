# from flask import Flask , render_template , request
from flask import Flask , render_template, request, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
import pandas as pd
import os
import dotenv
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from flask import g
from psycopg2.extras import RealDictCursor
from functools import wraps



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
        
        with g.db.cursor() as cur:
            cur.execute("SET TIME ZONE 'Asia/Kolkata';")
            
    return g.db

@app.teardown_appcontext
def close_db(exception):
    conn = g.pop("db", None)

    if conn is not None:
        db_pool.putconn(conn)




class database:
    
    #to create the user login table
    @staticmethod
    def user_table():
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


    #to save the google login data
    @staticmethod
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

    #to create the hackathon registration table
    @staticmethod
    def registration_table():
        conn = get_db()

        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS registrations(

                email VARCHAR(255) PRIMARY KEY,

                full_name VARCHAR(255) NOT NULL,
                rollno VARCHAR(50) NOT NULL,
                batch VARCHAR(30) NOT NULL,
                branch VARCHAR(100) NOT NULL,

                registered_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),

                FOREIGN KEY(email)
                REFERENCES users(email)
                ON DELETE CASCADE

            );
            """)

        conn.commit()
        
    #to save the registration form data
    @staticmethod
    def save_registration(data):

        conn = get_db()

        with conn.cursor() as cur:

            cur.execute("""

            INSERT INTO event_registrations(
                event_id,
                email,
                full_name,
                rollno,
                batch,
                branch

            )

            VALUES(%s,%s,%s,%s,%s,%s)

            ON CONFLICT(email,event_id)

            DO UPDATE SET
                full_name = EXCLUDED.full_name,
                rollno = EXCLUDED.rollno,
                batch = EXCLUDED.batch,
                branch = EXCLUDED.branch,
                updated_at = NOW();

            """,(
                data["event_id"],
                data["email"],
                data["name"],
                data["rollno"],
                data["batch"],
                data["branch"]

            ))
        conn.commit()
        
    #get the user registration data
    @staticmethod
    def get_registration(email):

        conn = get_db()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

            SELECT *
            FROM registrations
            WHERE email=%s

            """,(email,))

            return cur.fetchone()
    
    # ADMIN - to get all the data of participants
    @staticmethod
    def get_all_registrations():

        conn = get_db()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT
                    r.*,
                    u.profile_picture,
                    u.last_login

                FROM registrations r

                JOIN users u
                ON r.email=u.email

                ORDER BY updated_at DESC

            """)

            return cur.fetchall()
        
    #to get the dataframe of data for export in csv/pdf/excel
    # @staticmethod
    # def get_export_dataframe():

    #     conn = get_db()

    #     query = """
    #     SELECT
    #         full_name AS "Name",
    #         rollno AS "Roll Number",
    #         batch AS "Batch",
    #         branch AS "Branch",
    #         email AS "Email"
    #     FROM registrations
    #     ORDER BY full_name;
    #     """

    #     return pd.read_sql(query, conn)
    
    @staticmethod
    def get_event():
        conn = get_db()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""
            select *,
            TO_CHAR(date, 'YYYY-MM-DD') || 'T' || TO_CHAR(time, 'HH24:MI:SS') AS timer_datetime,
            To_Char(date, 'MON DD, YYYY') as formated_date
            from events 
            WHERE (date + time) >= (NOW() AT TIME ZONE 'Asia/Kolkata')
            order by date limit 4;

            """)
            
            return cur.fetchall()
    @staticmethod
    def get_event_form(id):
    
        conn = get_db()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

            SELECT title, id from events where id =%s

            """,(id,))
            
            return cur.fetchone()



# authenticator init
oauth = OAuth(app)

#table creation (check if exist)
with app.app_context():
    database.user_table()
    database.registration_table()


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

#to prevent the user to axis unautroised page without login
@app.before_request
def require_login():    
    allowed_routes = ["login","home","googlelogin","callback","logout","static"]

    if request.endpoint in allowed_routes:
        return

    if not session.get("user"):
        return redirect(url_for("login"))
        # return redirect(url_for("login", next=request.path))
print("hello world")

# home page
@app.route("/")
def home():

    # f"{date}T{time}"
    data = database.get_event()
    userdata = session.get("userdata",None)
    return render_template("index.html", user = userdata ,event_data = data )



# login page
@app.route("/login")
def login():
    return render_template("login.html")


#google login account window
#send to external website and then redirect to given callback website with data token in it
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
    session["userdata"] = data #to store the login data in the session
    session["user"] = data["name"] #to store the user for the verification of login
    
    database.save_user(data) #save the data into the login user table
    return redirect(url_for("home"))


#event registration form 
@app.route("/registration/hack/<int:event_id>")
def eventform(event_id):
    userdata = session.get("userdata")
    event_data = database.get_event_form(event_id)
    registration = database.get_registration(userdata["email"]) #to making the already submitted data appear on itcc
    return render_template(
        "registration.html",
        user=userdata,
        registration=registration,
        event_data  = event_data

    )   

#post of the event form data and saving it to db
@app.route("/formdata",methods = ["POST"])
def formdata():
    data = request.get_json()
    
    logged_in_email = session["userdata"]["email"]

    #to prevent anyone so send custom email from developer tool
    if data["email"] != logged_in_email:
        return {
            "success": False,
            "message": "Email does not match logged in account."
        }, 400
        
    database.save_registration(data)
    return {
        "success": True
    }
    
    
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session["userdata"]["email"] not in os.getenv("Admin"):
            return "Access Denied", 403

        return f(*args, **kwargs)

    return decorated_function

#for the admin panel

@app.route("/admin/list")
@admin_required
def admin_list():
    registrations = database.get_all_registrations()
   
    return render_template(
        "adminlist.html",
        registrations=registrations
    )
    
    
@app.route("/admin")
@admin_required 
def admin_home():
    return render_template("admin.html")


@app.route("/admin/team")
@admin_required
def team_formation():
    registrations = database.get_all_registrations()
    return render_template(
        "team_formation.html",
        registrations=registrations
    )

# attendence list route
@app.route("/admin/attendencelist")
@admin_required
def attendence_list():
    return "under production"


# Logout Function
@app.route("/logout")
def logout():
    if session.get("user"):
        session.clear()
    return redirect(url_for("home"))

# @app.route("/testing")
# def events():
#     data = database.get_event()
#     print(data)
#     return "check console"

if __name__ == "__main__":      
    app.run(host="0.0.0.0", port=8080, debug=True)