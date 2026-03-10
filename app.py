from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="login_app"
)

cursor = db.cursor(dictionary=True)

# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        try:
            if role == "farmer":
                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, hashed_password)
                )

            elif role == "buyer":
                cursor.execute(
                    "INSERT INTO buyers (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, hashed_password)
                )

            db.commit()
            flash("Account created successfully")
            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:
            flash("Email already exists")

    return render_template("register.html")

# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Check in users table (farmers)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        farmer = cursor.fetchone()

        if farmer and check_password_hash(farmer["password"], password):
            session["user_id"] = farmer["id"]
            session["name"] = farmer["name"]
            session["role"] = "farmer"
            return redirect(url_for("farmer_dashboard"))

        # Check in buyers table
        cursor.execute("SELECT * FROM buyers WHERE email=%s", (email,))
        buyer = cursor.fetchone()

        if buyer and check_password_hash(buyer["password"], password):
            session["user_id"] = buyer["id"]
            session["name"] = buyer["name"]
            session["role"] = "buyer"
            return redirect(url_for("buyer_dashboard"))

        flash("Invalid Email or Password")

    return render_template("login.html")


# ================= FARMER DASHBOARD =================
@app.route("/farmer_dashboard")
def farmer_dashboard():
    if "user_id" in session and session["role"] == "farmer":
        return render_template("farmer_dashboard.html", name=session["name"])
    return redirect(url_for("login"))

    # ================= buyer dashboard =================

@app.route("/buyer_dashboard", methods=["GET", "POST"])
def buyer_dashboard():
    if "user_id" not in session or session["role"] != "buyer":
        return redirect(url_for("login"))

    # If profile form submitted
    if request.method == "POST":
        
        company_name = request.form["company_name"]
        location = request.form["location"]
        contact_no = request.form["contact_no"]

        cursor.execute("""
            UPDATE buyers
            SET 
                company_name=%s,
                location=%s,
                contact_no=%s
            WHERE id=%s
        """, ( company_name, location, contact_no, session["user_id"]))

        db.commit()

    # Fetch buyer profile
    cursor.execute("SELECT * FROM buyers WHERE id=%s", (session["user_id"],))
    buyer = cursor.fetchone()

    # Fetch crop prices
    cursor.execute("""
        SELECT cp.id, c.crop_name, cp.price
        FROM crop_prices cp
        JOIN crops c ON cp.crop_id = c.id
        WHERE cp.buyer_id = %s
    """, (session["user_id"],))

    crops = cursor.fetchall()

    return render_template(
        "buyer_dashboard.html",
        buyer=buyer,
        crops=crops
    )
# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= ADD CROP =================

@app.route("/add_crop", methods=["GET", "POST"])
def add_crop():
    if "user_id" not in session or session["role"] != "buyer":
        return redirect(url_for("login"))

    if request.method == "POST":
        crop_id = request.form["crop_id"]
        price = request.form["price"]

        cursor.execute(
            "INSERT INTO crop_prices (buyer_id, crop_id, price) VALUES (%s, %s, %s)",
            (session["user_id"], crop_id, price)
        )
        db.commit()
        flash("Crop price added successfully")

        return redirect(url_for("buyer_dashboard"))

    # Load crop list for dropdown
    cursor.execute("SELECT * FROM crops")
    crops = cursor.fetchall()

    return render_template("add_crop.html", crops=crops)
           



           # ================= search crop =================

@app.route("/search_crop", methods=["GET", "POST"])
def search_crop():
    results = None

    if request.method == "POST":
        crop_name = request.form["crop_name"]

        query = """
        SELECT b.company_name,b.name, b.location,b.contact_no, c.crop_name, cp.price,cp.updated_at
        FROM crop_prices cp
        JOIN buyers b ON cp.buyer_id = b.id
        JOIN crops c ON cp.crop_id = c.id
        WHERE c.crop_name = %s
        """

        cursor.execute(query, (crop_name,))
        results = cursor.fetchall()

    return render_template("search_crop.html", results=results)



# ================= update price =================

@app.route("/update_price/<int:id>", methods=["GET", "POST"])
def update_price(id):

    if "user_id" not in session or session["role"] != "buyer":
        return redirect(url_for("login"))

    if request.method == "POST":
        new_price = request.form["price"]

        cursor.execute(
            "UPDATE crop_prices SET price=%s WHERE id=%s AND buyer_id=%s",
            (new_price, id, session["user_id"])
        )
        db.commit()
        flash("Price updated successfully")
        return redirect(url_for("buyer_dashboard"))

    cursor.execute("""
    SELECT cp.id, cp.price, c.crop_name
    FROM crop_prices cp
    JOIN crops c ON cp.crop_id = c.id
    WHERE cp.id=%s AND cp.buyer_id=%s
""", (id, session["user_id"]))
    crop = cursor.fetchone()

    return render_template("update_price.html", crop=crop)

# ================= delete price =================

@app.route("/delete_price/<int:id>")
def delete_price(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor.execute(
        "DELETE FROM crop_prices WHERE id = %s AND buyer_id = %s",
        (id, session["user_id"])
    )
    db.commit()

    flash("Crop price deleted successfully!", "success")

    return redirect(url_for("buyer_dashboard"))


# ================= update profile =================

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session or session["role"] != "buyer":
        return redirect(url_for("login"))

    if request.method == "POST":
        buyer_name = request.form["buyer_name"]
        company_name = request.form["company_name"]
        location = request.form["location"]
        contact_no = request.form["contact_no"]

        cursor.execute("""
            UPDATE buyers
            SET name=%s,
                company_name=%s,
                location=%s,
                contact_no=%s
            WHERE id=%s
        """, (buyer_name, company_name, location, contact_no, session["user_id"]))

        db.commit()
        return redirect(url_for("buyer_dashboard"))

    cursor.execute("SELECT * FROM buyers WHERE id=%s", (session["user_id"],))
    buyer = cursor.fetchone()

    return render_template("edit_profile.html", buyer=buyer)




    

# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)
