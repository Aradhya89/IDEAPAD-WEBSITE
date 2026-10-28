# from flask import Flask , render_template , request
from flask import Flask , render_template, request, redirect, session, url_for, send_file, after_this_request
from authlib.integrations.flask_client import OAuth
import pandas as pd
import os
import dotenv
import psycopg2
import cloudinary.uploader
import cloudinary 
from psycopg2.pool import SimpleConnectionPool
from flask import g
from psycopg2.extras import RealDictCursor
from functools import wraps
from datetime import datetime
import tempfile
from word2pdf import convert
from docxtpl import DocxTemplate
import shutil



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


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)



class database:

    @staticmethod
    def addevent(data):
        conn = get_db()

        with conn.cursor( ) as cur:

            cur.execute("""
                        insert into events (title, description, time, date, banner)
                        values
                        (%s,%s,%s,%s,%s)
                        """,(data['title'],
                             data['description'],
                             data['time'],
                             data['date'],
                             data['banner']))
        
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
    
    
    @staticmethod
    def attendencesheet(id):
        conn = get_db()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                        Select full_name as "Name", rollno as "RollNo" from event_registrations where event_id = %s order by "Name" Asc;
                        ''',(id,))
            return cur.fetchall()
            
            
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
    def get_registration(email,id):

        conn = get_db()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

            SELECT *
            FROM event_registrations
            WHERE email=%s and event_id =%s

            """,(email,id))

            return cur.fetchone()
    
    # ADMIN - to get all the data of participants
    @staticmethod
    def get_event_registrations(id):

        conn = get_db()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT
                    r.*,
                    u.profile_picture,
                    u.last_login

                FROM event_registrations r
                

                JOIN users u
                ON r.email=u.email
                where event_id = %s

                ORDER BY updated_at DESC

            """,(id,))

            return cur.fetchall()
    
    @staticmethod
    def get_all_event():
        conn = get_db()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                        select title, id from events;
                        """)
            return cur.fetchall()
    
    @staticmethod
    def get_event_home():
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

            SELECT title, id, date from events where id =%s

            """,(id,))
            
            return cur.fetchone()



# authenticator init
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

# CONFIG FUNCTION

#to prevent the user to access unautroised page without login
@app.before_request
def require_login():    
    allowed_routes = ["login","home","googlelogin","callback","logout","static"]

    if request.endpoint in allowed_routes:
        return

    if not session.get("user"):
        return redirect(url_for("login"))
        # return redirect(url_for("login", next=request.path))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session["userdata"]["email"] not in os.getenv("Admin"):
            return "Access Denied", 403

        return f(*args, **kwargs)

    return decorated_function



# home page
@app.route("/")
def home():
    data = database.get_event_home()
    userdata = session.get("userdata",None)
    return render_template("index.html", user = userdata ,event_data = data )


# login page
@app.route("/login")
def login():
    return render_template("login.html")


#google login := 

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
    registration = database.get_registration(userdata["email"],event_id) #to making the already submitted data appear on it
    return render_template(
        "registration.html",
        user=userdata,
        registration=registration,
        event_data=event_data

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
    
    

@app.route("/admin")
@admin_required 
def admin_home():
    eventdata = database.get_all_event()
    return render_template("admin.html",event_data = eventdata)


@app.route("/admin/team/<int:id>")
@admin_required
def team_formation():
    return "Under Production"


@app.route("/admin/attendencelist",methods= ["POST"])
@admin_required
def attendence_list():
    data = request.get_json()
    event_id = data.get("id")
    data = database.attendencesheet(event_id)
    event_data = database.get_event_form(event_id)

    formatted_date = datetime.strptime(str(event_data['date']), "%Y-%m-%d").strftime("%d %b %Y")
    UPLOAD_FOLDER = tempfile.mkdtemp()
    context = {
        "students": data,
        "event": event_data['title'],
        "date":formatted_date
    }
        
    doc = DocxTemplate("template.docx")
    doc.render(context)
    output_path_docx = os.path.join(UPLOAD_FOLDER,"Attendence_list.docx")
    output_path_pdf = os.path.join(UPLOAD_FOLDER,"Attendence_list.pdf")# adding the path of the temp folder with the report stored temporarly

    doc.save(output_path_docx)
    convert(output_path_docx, output_path_pdf)
    
    @after_this_request
    def cleanup(response):
        try:
            shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)
        except Exception as e:
            print("Cleanup error:", e)
        return response

    return send_file(
        output_path_pdf,    
        as_attachment=True,
        download_name="Attendence.pdf"
    )


@app.route("/admin/list/<int:id>")
@admin_required
def admin_list(id):
    registrations = database.get_event_registrations(id)
   
    return render_template(
        "adminlist.html",
        registrations=registrations,
        id = id
    )
    
    
@app.route("/admin/addevent",methods = ["GET","POST"])
@admin_required
def addevent():
    if request.method == "POST":
        data = {}
        data['description'] = request.form.get("description")
        data['time'] = request.form.get("time")
        data['date'] = request.form.get("date")
        banner = request.files.get("banner")
        data['title']= request.form.get("title")
        
        # 1. Upload the banner to Cloudinary.
        result = cloudinary.uploader.upload(banner,
        folder="ideapad/events", #folder name
        resource_type="image",
        quality="auto"
        )

        data['banner'] = result["secure_url"]
        database.addevent(data)
        data['banner_public_id'] = result["public_id"]
        
        return redirect(url_for("admin_home"))
    
    return render_template("hostevent.html")

# Logout Function
@app.route("/logout")
def logout():
    if session.get("user"):
        session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":      
    app.run(host="0.0.0.0", port=8080, debug=True)