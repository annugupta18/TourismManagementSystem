from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)

app.secret_key = "tourism_secret_key"


# ================= DATABASE CONNECTION =================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="tourism_management"
    )


# ================= HOME =================

@app.route("/")
def home():

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM destinations")

        destinations = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template(
            "index.html",
            destinations=destinations
        )

    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        try:

            db = get_db_connection()
            cursor = db.cursor()

            query = """
                INSERT INTO users
                (name, email, password)
                VALUES (%s, %s, %s)
            """

            cursor.execute(
                query,
                (name, email, password)
            )

            db.commit()

            cursor.close()
            db.close()

            return """
                <h1>🎉 Registration Successful!</h1>
                <p>Your account has been created successfully.</p>
                <a href="/login">Go to Login</a>
            """

        except mysql.connector.Error as e:

            return f"Database Error: {e}"

    return render_template("register.html")


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        try:

            db = get_db_connection()
            cursor = db.cursor()

            query = """
                SELECT *
                FROM users
                WHERE email = %s
                AND password = %s
            """

            cursor.execute(
                query,
                (email, password)
            )

            user = cursor.fetchone()

            cursor.close()
            db.close()

            if user:

                session["user_id"] = user[0]

                # Save user role
                session["role"] = user[4]

                return redirect("/destinations")

            else:

                return "Invalid Email or Password ❌"

        except mysql.connector.Error as e:

            return f"Database Error: {e}"

    return render_template("login.html")


# ================= DESTINATIONS =================

@app.route("/destinations")
def destinations():

    if "user_id" not in session:

        return redirect("/login")

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM destinations"
        )

        destinations = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template(
            "destinations.html",
            destinations=destinations
        )

    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= BOOK DESTINATION =================

@app.route(
    "/book/<int:destination_id>",
    methods=["GET", "POST"]
)
def book(destination_id):

    if "user_id" not in session:

        return redirect("/login")

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Get destination
        cursor.execute(
            """
            SELECT *
            FROM destinations
            WHERE id = %s
            """,
            (destination_id,)
        )

        destination = cursor.fetchone()

        if destination is None:

            cursor.close()
            db.close()

            return "Destination not found!"

        # ================= BOOKING FORM =================

        if request.method == "POST":

            user_id = session["user_id"]

            travel_date = request.form["travel_date"]

            persons = int(
                request.form["persons"]
            )

            # Calculate total price
            total_price = (
                destination["price"] * persons
            )

            # Save booking
            query = """
                INSERT INTO bookings
                (
                    user_id,
                    destination_id,
                    travel_date,
                    persons,
                    total_price,
                    status
                )

                VALUES
                (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                query,
                (
                    user_id,
                    destination_id,
                    travel_date,
                    persons,
                    total_price,
                    "Pending"
                )
            )

            db.commit()

            cursor.close()
            db.close()

            return render_template(
                "booking_success.html",
                destination=destination,
                travel_date=travel_date,
                persons=persons,
                total_price=total_price,
                status="Pending"
            )

        cursor.close()
        db.close()

        return render_template(
            "booking.html",
            destination=destination
        )

    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= MY BOOKINGS =================

@app.route("/my-bookings")
def my_bookings():

    if "user_id" not in session:

        return redirect("/login")

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        query = """
            SELECT
                bookings.id,
                destinations.name,
                destinations.location,
                bookings.travel_date,
                bookings.persons,
                bookings.total_price,
                bookings.booking_date,
                bookings.status

            FROM bookings

            JOIN destinations
            ON bookings.destination_id = destinations.id

            WHERE bookings.user_id = %s

            ORDER BY bookings.id DESC
        """

        cursor.execute(
            query,
            (session["user_id"],)
        )

        bookings = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template(
            "my_bookings.html",
            bookings=bookings
        )

    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= CANCEL BOOKING =================

@app.route("/cancel-booking/<int:booking_id>")
def cancel_booking(booking_id):

    if "user_id" not in session:

        return redirect("/login")

    try:

        db = get_db_connection()
        cursor = db.cursor()

        query = """
            UPDATE bookings
            SET status = 'Cancelled'

            WHERE id = %s
            AND user_id = %s
        """

        cursor.execute(
            query,
            (
                booking_id,
                session["user_id"]
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect("/my-bookings")

    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= ADMIN DASHBOARD =================

@app.route("/admin")
def admin_dashboard():

    # Login check
    if "user_id" not in session:

        return redirect("/login")

    # Admin check
    if session.get("role") != "admin":

        return "Access Denied ❌"

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)


        # ================= ALL BOOKINGS =================

        query = """
            SELECT
                bookings.id,
                users.name AS user_name,
                users.email,
                destinations.name AS destination_name,
                destinations.location,
                bookings.travel_date,
                bookings.persons,
                bookings.total_price,
                bookings.booking_date,
                bookings.status

            FROM bookings

            JOIN users
            ON bookings.user_id = users.id

            JOIN destinations
            ON bookings.destination_id = destinations.id

            ORDER BY bookings.id DESC
        """

        cursor.execute(query)

        bookings = cursor.fetchall()


        # ================= ALL DESTINATIONS =================

        cursor.execute("""
            SELECT
                id,
                name,
                location,
                price

            FROM destinations

            ORDER BY id DESC
        """)

        destinations = cursor.fetchall()


        # ================= STATISTICS =================

        cursor.execute(
            "SELECT COUNT(*) AS total_users FROM users"
        )

        total_users = cursor.fetchone()["total_users"]


        cursor.execute(
            "SELECT COUNT(*) AS total_destinations FROM destinations"
        )

        total_destinations = cursor.fetchone()["total_destinations"]


        cursor.execute(
            "SELECT COUNT(*) AS total_bookings FROM bookings"
        )

        total_bookings = cursor.fetchone()["total_bookings"]


        cursor.execute("""
            SELECT COUNT(*) AS confirmed
            FROM bookings
            WHERE status = 'Confirmed'
        """)

        confirmed = cursor.fetchone()["confirmed"]


        cursor.execute("""
            SELECT COUNT(*) AS pending
            FROM bookings
            WHERE status = 'Pending'
        """)

        pending = cursor.fetchone()["pending"]


        cursor.execute("""
            SELECT COUNT(*) AS cancelled
            FROM bookings
            WHERE status = 'Cancelled'
        """)

        cancelled = cursor.fetchone()["cancelled"]


        cursor.close()
        db.close()


        return render_template(
            "admin.html",

            bookings=bookings,

            destinations=destinations,

            total_users=total_users,

            total_destinations=total_destinations,

            total_bookings=total_bookings,

            confirmed=confirmed,

            pending=pending,

            cancelled=cancelled
        )


    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= ADMIN UPDATE BOOKING STATUS =================

@app.route(
    "/admin/update-booking/<int:booking_id>/<status>"
)
def admin_update_booking(
    booking_id,
    status
):

    if "user_id" not in session:

        return redirect("/login")

    if session.get("role") != "admin":

        return "Access Denied ❌"

    # Only these statuses allowed
    if status not in [
        "Confirmed",
        "Cancelled",
        "Pending"
    ]:

        return "Invalid Status ❌"

    try:

        db = get_db_connection()
        cursor = db.cursor()

        query = """
            UPDATE bookings

            SET status = %s

            WHERE id = %s
        """

        cursor.execute(
            query,
            (
                status,
                booking_id
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect("/admin")

    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= ADD DESTINATION =================

@app.route(
    "/admin/add-destination",
    methods=["GET", "POST"]
)
def add_destination():

    if "user_id" not in session:

        return redirect("/login")

    if session.get("role") != "admin":

        return "Access Denied ❌"

    if request.method == "POST":

        name = request.form["name"]

        location = request.form["location"]

        description = request.form["description"]

        image = request.form["image"]

        price = request.form["price"]

        try:

            db = get_db_connection()
            cursor = db.cursor()

            query = """
                INSERT INTO destinations
                (
                    name,
                    location,
                    description,
                    image,
                    price
                )

                VALUES
                (%s, %s, %s, %s, %s)
            """

            cursor.execute(
                query,
                (
                    name,
                    location,
                    description,
                    image,
                    price
                )
            )

            db.commit()

            cursor.close()
            db.close()

            return redirect("/admin")

        except mysql.connector.Error as e:

            return f"Database Error: {e}"

    return render_template(
        "add_destination.html"
    )


# ================= DELETE DESTINATION =================

@app.route(
    "/admin/delete-destination/<int:destination_id>"
)
def delete_destination(destination_id):

    # Login check
    if "user_id" not in session:

        return redirect("/login")

    # Admin check
    if session.get("role") != "admin":

        return "Access Denied ❌"

    try:

        db = get_db_connection()
        cursor = db.cursor()

        # Check if destination has bookings
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE destination_id = %s
            """,
            (destination_id,)
        )

        result = cursor.fetchone()

        total_bookings_for_destination = result[0]


        # Don't delete if bookings exist
        if total_bookings_for_destination > 0:

            cursor.close()
            db.close()

            return """
                <html>

                <head>
                    <title>Cannot Delete</title>
                </head>

                <body
                    style="
                        font-family: Arial;
                        text-align: center;
                        padding: 60px;
                        background: #f5f7fa;
                    "
                >

                    <h1 style="color: #dc3545;">
                        ❌ Cannot Delete Destination
                    </h1>

                    <p>
                        This destination already has bookings.
                    </p>

                    <p>
                        You cannot delete a destination
                        that has existing bookings.
                    </p>

                    <br>

                    <a
                        href="/admin"
                        style="
                            background: #0077b6;
                            color: white;
                            padding: 12px 20px;
                            text-decoration: none;
                            border-radius: 6px;
                        "
                    >
                        ← Back to Admin Dashboard
                    </a>

                </body>

                </html>
            """


        # Delete destination
        cursor.execute(
            """
            DELETE FROM destinations
            WHERE id = %s
            """,
            (destination_id,)
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect("/admin")

    except mysql.connector.Error as e:

        return f"Database Error: {e}"


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ================= RUN APPLICATION =================

if __name__ == "__main__":

    app.run(debug=True)