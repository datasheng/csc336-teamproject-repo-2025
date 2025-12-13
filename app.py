import os
import mysql.connector
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session, g, flash
)
# specific security imports for password hashing
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev_key')

# Database Connection Management

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=os.environ.get('MYSQL_HOST', 'localhost'),
            port=os.environ.get('MYSQL_PORT', 3306), 
            user=os.environ.get('MYSQL_USER'),
            password=os.environ.get('MYSQL_PASSWORD'),
            database=os.environ.get('MYSQL_DATABASE')
        )
        g.cursor = g.db.cursor(dictionary=True)
    return g.db, g.cursor

@app.teardown_appcontext
def close_db(e=None):
    cursor = g.pop('cursor', None)
    if cursor is not None:
        cursor.close()
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Authentication Decorator

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'org_id' not in session:
            return redirect(url_for('login_register'))
        return f(*args, **kwargs)
    return decorated_function

# Public Routes

@app.route("/")
def index():
    db, cursor = get_db()
    # Fetch events that are published
    query = """
    SELECT e.event_id, e.title, e.venue, e.starts_at, e.ends_at, o.org_name, MIN(t.price_cents) as price_cents
    FROM events e
    JOIN organizations o ON e.org_id = o.org_id
    LEFT JOIN tickets t ON e.event_id = t.event_id
    WHERE e.is_published = TRUE
    GROUP BY e.event_id
    ORDER BY e.starts_at ASC LIMIT 6;
    """
    cursor.execute(query)
    events = cursor.fetchall()
    return render_template("index.html", events=events)

@app.route("/events")
def event_list():
    db, cursor = get_db()
    # Fetch all published events with their ticket price
    query = """
    SELECT e.event_id, e.title, e.venue, e.starts_at, e.ends_at, o.org_name, MIN(t.price_cents) as price_cents
    FROM events e
    JOIN organizations o ON e.org_id = o.org_id
    LEFT JOIN tickets t ON e.event_id = t.event_id 
    WHERE e.is_published = TRUE
    GROUP BY e.event_id
    ORDER BY e.starts_at ASC;
    """
    cursor.execute(query)
    events = cursor.fetchall()
    return render_template("event-detail.html", events=events)

@app.route("/login", methods=["GET", "POST"])
def login_register():
    if request.method == "POST":
        db, cursor = get_db()
        
        # REGISTER Logic 
        if 'orgName' in request.form:
            org_name = request.form['orgName']
            email = request.form['orgEmail']
            raw_password = request.form['orgPassword']
            hashed_pw = generate_password_hash(raw_password)

            try:
                # 1. Create User
                cursor.execute("INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)", 
                               (org_name + " Admin", email, hashed_pw))
                new_user_id = cursor.lastrowid

                # 2. Create Organization
                cursor.execute("INSERT INTO organizations (org_name) VALUES (%s)", (org_name,))
                new_org_id = cursor.lastrowid

                # 3. Link them in Org_Members
                cursor.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (%s, %s, 'OWNER')", 
                               (new_org_id, new_user_id))
                
                db.commit()
                
                # Auto-login
                session['user_id'] = new_user_id
                session['org_id'] = new_org_id
                return redirect(url_for('create_event'))
                
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                db.rollback()
                flash("Registration failed. Email might already exist.")

        # LOGIN Logic
        elif 'loginEmail' in request.form:
            email = request.form['loginEmail']
            password = request.form['loginPassword']
            
            # Find user
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
                # Check if they are part of an organization
                cursor.execute("SELECT org_id FROM org_members WHERE user_id = %s", (user['user_id'],))
                membership = cursor.fetchone()
                
                session['user_id'] = user['user_id']
                if membership:
                    session['org_id'] = membership['org_id']
                    return redirect(url_for('create_event'))
                else:
                    # Valid user, but not an org member (maybe just a ticket buyer)
                    return redirect(url_for('index'))
            else:
                flash("Invalid email or password")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/register", methods=["GET", "POST"])
def register_for_event():
    db, cursor = get_db()
    
    if request.method == "POST":
        event_id = request.form['event']
        full_name = request.form['fullname']
        email = request.form['email']
        qty = 1 # Default to 1 ticket for this simple form
        
        try:
            # 1. Find or Create User (Guest checkout flow)
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                # Create a user without a password (guest)
                cursor.execute("INSERT INTO users (full_name, email) VALUES (%s, %s)", (full_name, email))
                user_id = cursor.lastrowid
            else:
                user_id = user['user_id']

            # 2. Get Ticket Info for this event
            cursor.execute("SELECT ticket_id, price_cents FROM tickets WHERE event_id = %s LIMIT 1", (event_id,))
            ticket = cursor.fetchone()
            if not ticket:
                return "No tickets found for this event", 400

            total_cost = ticket['price_cents'] * qty

            # 3. Create Order
            cursor.execute("INSERT INTO orders (buyer_user_id, email, created_at) VALUES (%s, %s, NOW())", 
                           (user_id, email))
            order_id = cursor.lastrowid

            # 4. Create Order Item
            cursor.execute("INSERT INTO order_items (order_id, ticket_id, qty, unit_price_cents) VALUES (%s, %s, %s, %s)",
                           (order_id, ticket['ticket_id'], qty, ticket['price_cents']))

            # 5. Record Payment
            cursor.execute("INSERT INTO payments (order_id, provider, status, amount_cents) VALUES (%s, 'credit_card', 'SUCCEEDED', %s)",
                           (order_id, total_cost))

            # 6. Record Revenue (Financial Intelligence)
            # Example: 5% Platform Fee
            platform_fee = int(total_cost * 0.05) 
            cursor.execute("INSERT INTO revenue (order_id, platform_fee_cents, created_at) VALUES (%s, %s, NOW())",
                           (order_id, platform_fee))

            db.commit()
            return redirect(url_for('thank_you'))
            
        except Exception as e:
            db.rollback()
            print(e)
            return "Error processing registration", 500

    # GET Request: Show form
    cursor.execute("SELECT event_id, title FROM events WHERE is_published = TRUE ORDER BY title")
    events = cursor.fetchall()
    return render_template("register.html", events=events)

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")

# Organization-Only Routes

@app.route("/create-event", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        db, cursor = get_db()
        org_id = session['org_id']
        
        title = request.form['eventName']
        venue = request.form['eventLocation']
        starts_at_str = request.form['eventDate']
        
        # Calculate default end time (2 hours later) to satisfy DB constraint ends_at > starts_at
        try:
            start_dt = datetime.strptime(starts_at_str, '%Y-%m-%dT%H:%M')
        except ValueError:
             # Fallback if seconds are included or format differs
            start_dt = datetime.strptime(starts_at_str, '%Y-%m-%d %H:%M:%S')

        end_dt = start_dt + timedelta(hours=2)
        
        starts_at = start_dt
        ends_at = end_dt 
        
        price = float(request.form['ticketPrice'])
        price_cents = int(price * 100)
        qty_total = int(request.form['totalTickets'])

        try:
            # Stored procedure call
            cursor.callproc('CreateEventWithTicket', [
                org_id, 
                title, 
                venue, 
                starts_at, 
                ends_at, 
                qty_total,   # Capacity
                price_cents, # Ticket Price
                qty_total    # Ticket Quantity
            ])
            
            db.commit()
            return redirect(url_for('thank_you'))
            
        except mysql.connector.Error as err:
            db.rollback()
            print(f"Error: {err}")
            flash("Error creating event. Please check your inputs.")

    return render_template("create-event.html")

@app.route("/revenue")
@login_required
def revenue_dashboard():
    db, cursor = get_db()
    org_id = session['org_id']
    
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT e.event_id) as events_hosted,
            COALESCE(SUM(p.amount_cents), 0) as total_revenue_cents,
            COALESCE(SUM(oi.qty), 0) as total_tickets_sold
        FROM events e
        LEFT JOIN tickets t ON e.event_id = t.event_id
        LEFT JOIN order_items oi ON t.ticket_id = oi.ticket_id
        LEFT JOIN orders o ON oi.order_id = o.order_id
        LEFT JOIN payments p ON o.order_id = p.order_id
        WHERE e.org_id = %s AND (p.status = 'SUCCEEDED' OR p.status IS NULL)
    """, (org_id,))
    
    data = cursor.fetchone()
    
    stats = {
        'total_revenue': f"${data['total_revenue_cents'] / 100:,.2f}",
        'total_tickets_sold': data['total_tickets_sold'],
        'events_hosted': data['events_hosted'],
        'avg_attendance': "TBD" 
    }

    # Stored procedure call
    cursor.close()
    db, cursor = get_db()
    
    cursor.callproc('GetOrgRevenueReport', [org_id])
    
    # Stored procedures return multiple result sets, iterate to find the data
    event_rows = []
    for result in cursor.stored_results():
        event_rows = result.fetchall()

    return render_template("revenue.html", stats=stats, event_rows=event_rows)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)