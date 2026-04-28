import http.server
import sqlite3
import hashlib
import urllib.parse
from http.cookies import SimpleCookie

sessions = {}


def init_db():
    conn = sqlite3.connect("blog.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY,
      username TEXT,
      password TEXT
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
    cookie=SimpleCookie(handler.headers.get("Cookie"))
    if "sid" in cookie:
        return sessions.get(cookie["sid"].value)
    return None


def html(title,content):
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
        self.send_header("Content-Type","text/html")
        self.end_headers()
        self.wfile.write(text.encode())


    def do_GET(self):

        user=current_user(self)

        if self.path=="/":

            self.send_page(html(
                "Home",
                """
                <a href='/register'>Register</a><br>
                <a href='/login'>Login</a><br>
                <a href='/comments'>Comments</a>
                """
            ))


        elif self.path=="/register":
            self.send_page(html(
                "Register",
                """
                <form method='POST' action='/register'>
                Username:<input name='username'><br>
                Password:<input name='password' type='password'><br>
                <button>Register</button>
                </form>
                """
            ))


        elif self.path=="/login":
            self.send_page(html(
                "Login",
                """
                <form method='POST' action='/login'>
                Username:<input name='username'><br>
                Password:<input name='password' type='password'><br>
                <button>Login</button>
                </form>
                """
            ))

        elif self.path=="/comments":

            conn=sqlite3.connect("blog.db")
            c=conn.cursor()

            c.execute("SELECT username,content FROM comments")
            rows=c.fetchall()
            conn.close()

            comments=""

            for u,text in rows:

                comments += f"<p><b>{u}</b>: {text}</p>"

            form=""

            if user:
                form="""
                <form method='POST' action='/comments'>
                <textarea name='content'></textarea><br>
                <button>Post</button>
                </form>
                """

            self.send_page(
                html(
                    "Comments",
                    comments+form
                )
            )



    def do_POST(self):

        if self.path=="/register":

            data=body(self)

            username=data["username"][0]
            password=data["password"][0]

            pw=hashlib.md5(password.encode()).hexdigest()

            conn=sqlite3.connect("blog.db")
            c=conn.cursor()

            c.execute(
              f"INSERT INTO users(username,password) VALUES('{username}','{pw}')"
            )

            conn.commit()
            conn.close()

            self.send_response(302)
            self.send_header("Location","/login")
            self.end_headers()



        elif self.path=="/login":

            data=body(self)

            username=data["username"][0]
            password=data["password"][0]

            pw=hashlib.md5(password.encode()).hexdigest()

            conn=sqlite3.connect("blog.db")
            c=conn.cursor()

            query=f"""
            SELECT * FROM users
            WHERE username='{username}'
            AND password='{pw}'
            """

            print(query)

            c.execute(query)

            user=c.fetchone()

            conn.close()

            if user:

                sid=username

                sessions[sid]=username

                self.send_response(302)
                self.send_header(
                    "Set-Cookie",
                    f"sid={sid}"
                )
                self.send_header("Location","/comments")
                self.end_headers()



        elif self.path=="/comments":

            user=current_user(self)

            if not user:
                return

            data=body(self)

            content=data["content"][0]

            conn=sqlite3.connect("blog.db")
            c=conn.cursor()

            c.execute(
             f"""
             INSERT INTO comments(username,content)
             VALUES('{user}','{content}')
             """
            )

            conn.commit()
            conn.close()

            self.send_response(302)
            self.send_header("Location","/comments")
            self.end_headers()



init_db()

server=http.server.HTTPServer(
("localhost",8000),
App
)

print("http://localhost:8000")

server.serve_forever()