from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta

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



# ================= Farmer Dashboard =================
@app.route("/farmer_dashboard", methods=["GET", "POST"])
def farmer_dashboard():
    if "user_id" not in session or session["role"] != "farmer":
        return redirect(url_for("login"))

    farmer_id = session["user_id"]

    # Handle profile form submission
    if request.method == "POST":
        name = request.form.get("name")
        contact_no = request.form.get("contact_no")
        location = request.form.get("location")

        cursor.execute("""
            UPDATE users
            SET name=%s, contact_no=%s, location=%s
            WHERE id=%s
        """, (name, contact_no, location, farmer_id))
        db.commit()

    # Fetch farmer profile
    cursor.execute("SELECT * FROM users WHERE id=%s", (farmer_id,))
    farmer_info = cursor.fetchone()

    # Fetch crop quantity + selling price
    cursor.execute("""
        SELECT cq.id, c.crop_name, cq.quantity, cq.selling_price
        FROM crop_quantity cq
        JOIN crops c ON cq.crop_id = c.id
        WHERE cq.user_id = %s
    """, (farmer_id,))
    crops = cursor.fetchall()

    return render_template(
        "farmer_dashboard.html",
        name=session["name"],
        farmer_info=farmer_info,
        crops=crops
    )

# ================= Edit Farmer Profile =================
@app.route("/edit_farmer_info", methods=["GET", "POST"])
def edit_farmer_info():
    if "user_id" not in session or session["role"] != "farmer":
        return redirect(url_for("login"))

    farmer_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name")
        contact_no = request.form.get("contact_no")
        location = request.form.get("location")

        cursor.execute("""
            UPDATE users
            SET name=%s, contact_no=%s, location=%s
            WHERE id=%s
        """, (name, contact_no, location, farmer_id))
        db.commit()

        flash("Information updated successfully!")
        return redirect(url_for("farmer_dashboard"))

    # Fetch current info for form
    cursor.execute("SELECT * FROM users WHERE id=%s", (farmer_id,))
    farmer_info = cursor.fetchone()

    return render_template(
        "edit_farmer_info.html",
        farmer_info=farmer_info,
        name=session["name"]
    )


# ================= buyer dashboard =================
@app.route("/buyer_dashboard", methods=["GET", "POST"])
def buyer_dashboard():

    if "user_id" not in session or session["role"] != "buyer":
        return redirect(url_for("login"))

    buyer_id = session["user_id"]

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
        """, (company_name, location, contact_no, buyer_id))

        db.commit()

    # Fetch buyer profile
    cursor.execute("SELECT * FROM buyers WHERE id=%s", (buyer_id,))
    buyer = cursor.fetchone()

    # Count total crops priced by buyer
    cursor.execute(
        "SELECT COUNT(*) AS total FROM crop_prices WHERE buyer_id=%s",
        (buyer_id,)
    )
    result = cursor.fetchone()
    total_crops = result["total"]

    # Calculate total trading value
    cursor.execute(
        "SELECT SUM(price) AS total_trading FROM crop_prices WHERE buyer_id=%s",
        (buyer_id,)
    )
    result = cursor.fetchone()
    total_trading = result["total_trading"]

    # Fetch crop prices
    cursor.execute("""
        SELECT cp.id, c.crop_name, cp.price
        FROM crop_prices cp
        JOIN crops c ON cp.crop_id = c.id
        WHERE cp.buyer_id = %s
    """, (buyer_id,))
    crops = cursor.fetchall()



    

    return render_template(
        "buyer_dashboard.html",
        buyer=buyer,
        crops=crops,
        total_crops=total_crops,
        total_trading=total_trading
    )


    
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



# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= ADD Quantity =================

@app.route("/add_quantity", methods=["GET","POST"])
def add_quantity():
    if "user_id" not in session or session["role"] != "farmer":
        return redirect(url_for("login"))

    farmer_id = session["user_id"]

    # Fetch crops list for dropdown
    cursor.execute("SELECT id, crop_name FROM crops")
    crops_list = cursor.fetchall()

    if request.method == "POST":
        crop_id = request.form.get("crop_id")
        quantity = request.form.get("quantity")
        selling_price = request.form.get("selling_price")

        if not crop_id or not quantity:
            flash("All fields are required", "danger")
            return redirect(url_for("add_quantity"))

        # Insert into database
        cursor.execute("""
            INSERT INTO crop_quantity (crop_id, quantity, selling_price, user_id)
            VALUES (%s, %s, %s, %s)
        """, (crop_id, quantity, selling_price, farmer_id))
        db.commit()

        flash("Crop added successfully!", "success")
        return redirect(url_for("farmer_dashboard"))  # redirect to dashboard after successful add

    # GET request → show form
    return render_template("add_quantity.html", crops_list=crops_list, name=session["name"])


# ================= ORDERS =================

@app.route("/orders", methods=["GET","POST"])
def orders():
    cursor = db.cursor(dictionary=True)

    # Fetch all crops
    cursor.execute("SELECT * FROM crops")
    crops = cursor.fetchall()

    orders = []
    my_orders = []

    buyer_id = session["user_id"]

    if request.method == "POST":
        crop_id = request.form["crop_id"]

        query = """
        SELECT 
            users.name AS farmer_name,
            users.id AS user_id,
            users.location,
            users.contact_no,
            crops.id AS crop_id,
            crops.crop_name,
            crop_quantity.quantity,
            crop_quantity.selling_price,
            orders.status
        FROM crop_quantity
        JOIN users ON crop_quantity.user_id = users.id
        JOIN crops ON crop_quantity.crop_id = crops.id
        LEFT JOIN orders 
            ON orders.user_id = users.id 
            AND orders.crop_id = crops.id 
            AND orders.buyer_id = %s
        WHERE crops.id = %s
        """
        cursor.execute(query, (buyer_id, crop_id))
        orders = cursor.fetchall()

    # BUYER PLACED ORDERS (last 30 days)
    cursor.execute("""
    SELECT 
        users.name AS farmer_name,
        users.location,
        users.contact_no,
        crops.crop_name,
        orders.quantity,
        crop_quantity.selling_price,
        orders.status,
        orders.order_date
    FROM orders
    JOIN users ON orders.user_id = users.id
    JOIN crops ON orders.crop_id = crops.id
    JOIN crop_quantity 
        ON crop_quantity.crop_id = crops.id 
        AND crop_quantity.user_id = users.id
    WHERE orders.buyer_id = %s
    AND orders.order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ORDER BY orders.order_date DESC
    """, (buyer_id,))
    my_orders = cursor.fetchall()


    cursor.execute("""
SELECT 
    users.name AS farmer_name,
    users.location,
    users.contact_no,
    crops.crop_name,
    orders.quantity,
    crop_quantity.selling_price,
    orders.order_date,
    orders.status
FROM orders
JOIN crop_quantity ON orders.crop_id = crop_quantity.crop_id
JOIN users ON crop_quantity.user_id = users.id
JOIN crops ON orders.crop_id = crops.id
WHERE orders.buyer_id = %s
ORDER BY orders.order_date DESC
LIMIT 3
""",(buyer_id,))
    my_orders = cursor.fetchall()


    return render_template("orders.html",
        crops=crops,
        orders=orders,
        my_orders=my_orders
    )




@app.route("/order_history")
def order_history():

    buyer_id = session["user_id"]
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
    users.name AS farmer_name,
    users.location,
    users.contact_no,
    crops.crop_name,
    orders.quantity,
    crop_quantity.selling_price,
    orders.status,
    orders.order_date
    FROM orders
    JOIN users ON orders.user_id = users.id
    JOIN crops ON orders.crop_id = crops.id
    JOIN crop_quantity 
    ON crop_quantity.crop_id = crops.id 
    AND crop_quantity.user_id = users.id
    WHERE orders.buyer_id = %s
    ORDER BY orders.order_date DESC
    """,(buyer_id,))

    history = cursor.fetchall()

    return render_template("order_history.html", history=history)

# ================= UPDATE QUANTITY =================

@app.route("/update_quantity/<int:id>", methods=["GET", "POST"])
def update_quantity(id):
    if "user_id" not in session or session["role"] != "farmer":
        return redirect(url_for("login"))

    farmer_id = session["user_id"]

    # Fetch existing crop quantity
    cursor.execute("""
        SELECT cq.id, cq.quantity, cq.selling_price, cq.crop_id, c.crop_name
        FROM crop_quantity cq
        JOIN crops c ON cq.crop_id = c.id
        WHERE cq.id = %s AND cq.user_id = %s
    """, (id, farmer_id))
    crop = cursor.fetchone()

    if not crop:
        flash("Crop not found or you don't have permission.", "danger")
        return redirect(url_for("farmer_dashboard"))

    if request.method == "POST":
        quantity = request.form.get("quantity")
        selling_price = request.form.get("selling_price")

        cursor.execute("""
            UPDATE crop_quantity
            SET quantity=%s, selling_price=%s
            WHERE id=%s AND user_id=%s
        """, (quantity, selling_price, id, farmer_id))
        db.commit()
        flash("Crop quantity updated successfully!", "success")
        return redirect(url_for("farmer_dashboard"))

    # Render update form
    return render_template("update_quantity.html", crop=crop)


# ================= DELETE QUANTITY =================

@app.route("/delete_quantity/<int:id>", methods=["POST", "GET"])
def delete_quantity(id):
    # Check if farmer is logged in
    if "user_id" not in session or session["role"] != "farmer":
        return redirect(url_for("login"))

    farmer_id = session["user_id"]

    # Verify that the crop belongs to this farmer
    cursor.execute("""
        SELECT * FROM crop_quantity
        WHERE id=%s AND user_id=%s
    """, (id, farmer_id))
    crop = cursor.fetchone()

    if not crop:
        flash("Crop not found or you don't have permission.", "danger")
        return redirect(url_for("farmer_dashboard"))

    # Delete the crop quantity
    cursor.execute("DELETE FROM crop_quantity WHERE id=%s AND user_id=%s", (id, farmer_id))
    db.commit()

    flash("Crop deleted successfully!", "success")
    return redirect(url_for("farmer_dashboard"))




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

# ================= FARMER ORDERS (LAST 5) =================

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
    
# ================= FARMER ORDERS =================

@app.route("/farmer_orders")
def farmer_orders():

    farmer_id = session["user_id"]
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        orders.id,
        users.name AS buyer_name,
        crops.crop_name,
        orders.quantity,
        orders.status,
        orders.order_date
    FROM orders
    JOIN users ON orders.buyer_id = users.id
    JOIN crops ON orders.crop_id = crops.id
    WHERE orders.user_id = %s
    ORDER BY orders.order_date DESC
    LIMIT 5
    """,(farmer_id,))

    orders = cursor.fetchall()

    return render_template("farmer_orders.html", orders=orders)


# ================= FARMER ORDER HISTORY =================
@app.route("/farmer_order_history")
def farmer_order_history():

    farmer_id = session["user_id"]
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        users.name AS buyer_name,
        crops.crop_name,
        orders.quantity,
        orders.status,
        orders.order_date
    FROM orders
    JOIN users ON orders.buyer_id = users.id
    JOIN crops ON orders.crop_id = crops.id
    WHERE orders.user_id = %s
    ORDER BY orders.order_date DESC
    """,(farmer_id,))

    history = cursor.fetchall()

    return render_template("farmer_order_history.html", history=history)

# ================= ACCEPT  ORDERS  =================

@app.route("/accept_order/<int:id>")
def accept_order(id):

    cursor = db.cursor()

    cursor.execute(
        "UPDATE orders SET status='Accepted' WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect(url_for("farmer_orders"))

# ================= REJECT ORDERS  =================

@app.route("/reject_order/<int:id>")
def reject_order(id):

    cursor = db.cursor()

    cursor.execute(
        "UPDATE orders SET status='Rejected' WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect(url_for("farmer_orders"))

# ================= PLACE ORDERS  =================

@app.route("/place_order", methods=["POST"])
def place_order():

    buyer_id = session["user_id"]

    user_id = request.form["user_id"]
    crop_id = request.form["crop_id"]
    quantity = request.form["quantity"]

    cursor = db.cursor()

    cursor.execute("""
    INSERT INTO orders (buyer_id,user_id,crop_id,quantity,status)
    VALUES (%s,%s,%s,%s,'Pending')
    """,(buyer_id,user_id,crop_id,quantity))

    db.commit()

    return redirect(url_for("buyer_dashboard"))

# ================= GIVE ORDERS  =================

@app.route("/give_order/<int:user_id>/<int:crop_id>")
def give_order(user_id, crop_id):

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT users.name AS farmer_name, crops.crop_name, crop_quantity.selling_price
    FROM crop_quantity
    JOIN users ON crop_quantity.user_id = users.id
    JOIN crops ON crop_quantity.crop_id = crops.id
    WHERE users.id=%s AND crops.id=%s
    """,(user_id,crop_id))

    crop = cursor.fetchone()

    return render_template(
        "give_order.html",
        crop=crop,
        user_id=user_id,
        crop_id=crop_id
    )

# ================= forgot password  =================

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form["email"]

        cursor = db.cursor(dictionary=True)

        # Check in users table
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        # Check in buyers table
        cursor.execute("SELECT * FROM buyers WHERE email=%s", (email,))
        buyer = cursor.fetchone()

        if user:
            return redirect(url_for("reset_password", email=email, table="users"))

        elif buyer:
            return redirect(url_for("reset_password", email=email, table="buyers"))

        else:
            return render_template("forgot_password.html", error="Invalid Email")

    return render_template("forgot_password.html")
    
# ================= Reset password  =================

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    email = request.args.get("email")
    table = request.args.get("table")

    if request.method == "POST":
        new_password = request.form["password"]
        hashed_password = generate_password_hash(new_password)

        cursor = db.cursor()

        cursor.execute(f"""
            UPDATE {table}
            SET password=%s
            WHERE email=%s
        """, (hashed_password, email))

        db.commit()

        return redirect(url_for("login"))

    return render_template("reset_password.html")


    cursor = db.cursor(dictionary=True)

    # Check users table
    cursor.execute("SELECT * FROM users WHERE reset_token=%s", (token,))
    user_data = cursor.fetchone()

    # Check buyers table
    cursor.execute("SELECT * FROM buyers WHERE reset_token=%s", (token,))
    buyer_data = cursor.fetchone()

    user = user_data if user_data else buyer_data
    table = "users" if user_data else "buyers" if buyer_data else None

    if not user:
        return "Invalid token"

    # Check expiry
    if user["token_expiry"] < datetime.now():
        return "Token expired"

    if request.method == "POST":
        new_password = request.form["password"]
        hashed_password = generate_password_hash(new_password)

        cursor.execute(f"""
            UPDATE {table}
            SET password=%s, reset_token=NULL, token_expiry=NULL
            WHERE id=%s
        """, (hashed_password, user["id"]))

        db.commit()

        return redirect(url_for("login"))

    return render_template("reset_password.html")

# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)
