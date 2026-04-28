import http.server
import sqlite3
import bcrypt
import secrets
import urllib.parse
import html
from http.cookies import SimpleCookie


sessions={}



def init_db():

    conn=sqlite3.connect("secure.db")
    c=conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY,
      username TEXT UNIQUE,
      password BLOB
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS comments(
      id INTEGER PRIMARY KEY,
      username TEXT,
      content TEXT
    )
    """)

    conn.commit()
    conn.close()




def body(handler):
    length=int(handler.headers["Content-Length"])
    data=handler.rfile.read(length).decode()
    return urllib.parse.parse_qs(data)


def current_user(handler):

    cookie=SimpleCookie(
      handler.headers.get("Cookie")
    )

    if "sid" in cookie:
        sid=cookie["sid"].value
        return sessions.get(sid)

    return None


def page(title,content):
    return f"""
    <html>
    <body>
    <h1>{title}</h1>
    {content}
    </body>
    </html>
    """



class App(http.server.BaseHTTPRequestHandler):


    def send_page(self,text):

        self.send_response(200)

        self.send_header(
         "Content-Type",
         "text/html"
        )

        # Security headers
        self.send_header(
         "Content-Security-Policy",
         "default-src 'self'"
        )

        self.send_header(
         "X-Frame-Options",
         "DENY"
        )

        self.send_header(
         "X-Content-Type-Options",
         "nosniff"
        )

        self.end_headers()

        self.wfile.write(text.encode())


    def do_GET(self):

        user=current_user(self)


        if self.path=="/":

            self.send_page(
                page(
                 "Home",
                 """
                 <a href='/register'>Register</a><br>
                 <a href='/login'>Login</a><br>
                 <a href='/comments'>Comments</a>
                 """
                )
            )


        elif self.path=="/register":

            self.send_page(
                page(
                "Register",
                """
                <form method='POST' action='/register'>
                Username:<input name='username'><br>
                Password:<input type='password'
                name='password'><br>
                <button>Register</button>
                </form>
                """
                )
            )


        elif self.path=="/login":

            self.send_page(
                page(
                "Login",
                """
                <form method='POST' action='/login'>
                Username:<input name='username'><br>
                Password:<input type='password'
                name='password'><br>
                <button>Login</button>
                </form>
                """
                )
            )


        elif self.path=="/comments":

            conn=sqlite3.connect("secure.db")
            c=conn.cursor()

            c.execute(
             "SELECT username,content FROM comments"
            )

            rows=c.fetchall()

            conn.close()


            comments=""

            for username,text in rows:

                # XSS protection
                safe_user=html.escape(username)
                safe_text=html.escape(text)

                comments+=(
                   f"<p><b>{safe_user}</b>: "
                   f"{safe_text}</p>"
                )


            form=""

            if user:

                form="""
                <form method='POST'
                action='/comments'>
                <textarea name='content'>
                </textarea><br>
                <button>Post</button>
                </form>
                """


            self.send_page(
              page(
               "Comments",
               comments+form
              )
            )



    def do_POST(self):


        if self.path=="/register":

            data=body(self)

            username=data["username"][0].strip()
            password=data["password"][0]

            if not username or not password:
                return

            # Secure password hashing
            hashed=bcrypt.hashpw(
               password.encode(),
               bcrypt.gensalt()
            )

            conn=sqlite3.connect("secure.db")
            c=conn.cursor()

            try:
                c.execute(
                  """
                  INSERT INTO users
                  (username,password)
                  VALUES (?,?)
                  """,
                  (username,hashed)
                )

                conn.commit()

            except:
                conn.close()
                return

            conn.close()

            self.send_response(302)
            self.send_header(
             "Location",
             "/login"
            )
            self.end_headers()



        elif self.path=="/login":

            data=body(self)

            username=data["username"][0]
            password=data["password"][0]

            conn=sqlite3.connect(
               "secure.db"
            )

            c=conn.cursor()

            c.execute(
              """
              SELECT password
              FROM users
              WHERE username=?
              """,
              (username,)
            )

            row=c.fetchone()

            conn.close()

            if row and bcrypt.checkpw(
               password.encode(),
               row[0]
            ):

                sid=secrets.token_hex(32)

                sessions[sid]=username

                self.send_response(302)

                self.send_header(
                 "Set-Cookie",
                 (
                  "sid="+sid+
                  "; HttpOnly; SameSite=Strict"
                 )
                )

                self.send_header(
                 "Location",
                 "/comments"
                )

                self.end_headers()



        elif self.path=="/comments":

            user=current_user(self)

            if not user:
                return

            data=body(self)

            content=data["content"][0]

            conn=sqlite3.connect(
              "secure.db"
            )

            c=conn.cursor()

            c.execute(
             """
             INSERT INTO comments
             (username,content)
             VALUES (?,?)
             """,
             (user,content)
            )

            conn.commit()

            conn.close()

            self.send_response(302)

            self.send_header(
             "Location",
             "/comments"
            )

            self.end_headers()



init_db()

server=http.server.HTTPServer(
 ("localhost",8001),
 App
)

print("http://localhost:8001")

server.serve_forever()