import os
import mysql.connector
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session, g, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev_key')

# --- DB CONNECTION ---
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

# --- AUTH DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_register', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route("/")
def index():
    db, cursor = get_db()
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
    query = """
    SELECT e.event_id, e.title, e.venue, e.description, e.starts_at, e.ends_at, o.org_name, MIN(t.price_cents) as price_cents
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
    next_url = request.args.get('next') or url_for('index')

    if request.method == "POST":
        db, cursor = get_db()
        
        if 'orgName' in request.form:
            org_name = request.form['orgName']
            email = request.form['orgEmail']
            raw_password = request.form['orgPassword']
            
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("This email is already registered. Please login.", "warning")
                return redirect(url_for('login_register'))

            hashed_pw = generate_password_hash(raw_password)

            try:
                cursor.execute("INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)", 
                               (org_name + " Admin", email, hashed_pw))
                new_user_id = cursor.lastrowid

                cursor.execute("INSERT INTO organizations (org_name) VALUES (%s)", (org_name,))
                new_org_id = cursor.lastrowid

                cursor.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (%s, %s, 'OWNER')", 
                               (new_org_id, new_user_id))
                
                db.commit()
                
                session['user_id'] = new_user_id
                session['org_id'] = new_org_id
                session['is_admin'] = False
                flash("Registration successful!", "success")
                return redirect(url_for('create_event'))
                
            except mysql.connector.Error as err:
                db.rollback()
                flash(f"Registration error: {err}", "danger")

        elif 'loginEmail' in request.form:
            email = request.form['loginEmail']
            password = request.form['loginPassword']
            
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['user_id']
                session['is_admin'] = bool(user.get('is_admin', False))

                if not session['is_admin']:
                    cursor.execute("SELECT org_id FROM org_members WHERE user_id = %s", (user['user_id'],))
                    membership = cursor.fetchone()
                    if membership:
                        session['org_id'] = membership['org_id']
                
                flash("Welcome back!", "success")
                return redirect(next_url)
            else:
                flash("Invalid email or password. Please try again.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route("/register", methods=["GET", "POST"])
def register_for_event():
    db, cursor = get_db()
    
    if request.method == "POST":
        event_id = request.form['event']
        full_name = request.form['fullname']
        email = request.form['email']
        student_id = request.form['student_id']
        payment_method = request.form.get('payment')
        qty = 1 
        
        try:
            cursor.execute("SELECT * FROM events WHERE event_id = %s", (event_id,))
            event = cursor.fetchone()
            if not event:
                return "Event not found", 404

            cursor.execute("SELECT user_id FROM users WHERE student_id = %s", (student_id,))
            user = cursor.fetchone()
            
            if not user:
                cursor.execute("INSERT INTO users (full_name, email, student_id) VALUES (%s, %s, %s)", 
                               (full_name, email, student_id))
                user_id = cursor.lastrowid
            else:
                user_id = user['user_id'] if isinstance(user, dict) else user[0]

            cursor.execute("""
                SELECT COUNT(*) as count FROM order_items oi
                JOIN tickets t ON oi.ticket_id = t.ticket_id
                JOIN orders o ON oi.order_id = o.order_id
                WHERE o.buyer_user_id = %s AND t.event_id = %s
            """, (user_id, event_id))
            
            result = cursor.fetchone()
            count = result['count'] if isinstance(result, dict) else result[0]

            if count > 0:
                flash("This Student ID is already registered for this event.", "warning")
                return redirect(url_for('register_for_event'))

            cursor.execute("SELECT ticket_id, price_cents FROM tickets WHERE event_id = %s LIMIT 1", (event_id,))
            ticket = cursor.fetchone()
            total_cost = ticket['price_cents'] * qty

            cursor.execute("INSERT INTO orders (buyer_user_id, email, created_at) VALUES (%s, %s, NOW())", 
                           (user_id, email))
            order_id = cursor.lastrowid

            cursor.execute("INSERT INTO order_items (order_id, ticket_id, qty, unit_price_cents) VALUES (%s, %s, %s, %s)",
                           (order_id, ticket['ticket_id'], qty, ticket['price_cents']))

            if payment_method == 'cash':
                status = 'PENDING'
                provider = 'cash'
            else:
                status = 'SUCCEEDED'
                provider = 'credit_card'

            cursor.execute("INSERT INTO payments (order_id, provider, status, amount_cents) VALUES (%s, %s, %s, %s)",
                           (order_id, provider, status, total_cost))

            platform_fee = int(total_cost * 0.07) 
            cursor.execute("INSERT INTO revenue (order_id, platform_fee_cents, created_at) VALUES (%s, %s, NOW())",
                           (order_id, platform_fee))

            db.commit()

            return render_template('thank_you.html', 
                                   event=event, 
                                   user_name=full_name, 
                                   order_id=order_id,
                                   payment_status=status)
            
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            flash(f"Error processing registration: {e}", "danger")
            return redirect(url_for('register_for_event'))

    cursor.execute("SELECT event_id, title FROM events WHERE is_published = TRUE ORDER BY title")
    events = cursor.fetchall()
    return render_template("register.html", events=events)

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")

@app.route("/create-event", methods=["GET", "POST"])
@login_required
def create_event():
    if session.get('is_admin'):
        flash("Admins cannot create events.", "warning")
        return redirect(url_for('revenue_dashboard'))

    if request.method == "POST":
        db, cursor = get_db()
        org_id = session['org_id']
        
        title = request.form['eventName']
        description = request.form.get('eventDescription', '') 
        venue = request.form['eventLocation']
        starts_at_str = request.form['eventDate']
        
        try:
            start_dt = datetime.strptime(starts_at_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            start_dt = datetime.strptime(starts_at_str, '%Y-%m-%d %H:%M:%S')

        end_dt = start_dt + timedelta(hours=2)
        
        price = float(request.form['ticketPrice'])
        price_cents = int(price * 100)
        qty_total = int(request.form['totalTickets'])

        try:
            cursor.callproc('CreateEventWithTicket', [
                org_id, 
                title, 
                description, 
                venue, 
                start_dt, 
                end_dt, 
                qty_total,
                price_cents,
                qty_total
            ])
            
            db.commit()
            flash("Event created successfully!", "success")
            return redirect(url_for('index')) 
            
        except mysql.connector.Error as err:
            db.rollback()
            print(f"Error: {err}")
            flash("Error creating event. Please check your inputs.", "danger")

    return render_template("create-event.html")

# --- NEW: ORDER MANAGEMENT ROUTES ---

@app.route("/update-order/<int:order_id>/<action>", methods=["POST"])
@login_required
def update_order_status(order_id, action):
    db, cursor = get_db()
    
    # 1. Verify Permission (Security Check)
    # If Admin, they can edit anything. If Org, they must own the event.
    is_admin = session.get('is_admin', False)
    org_id = session.get('org_id')

    # Fetch order details to check ownership
    cursor.execute("""
        SELECT e.org_id 
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN tickets t ON oi.ticket_id = t.ticket_id
        JOIN events e ON t.event_id = e.event_id
        WHERE o.order_id = %s
    """, (order_id,))
    
    order_data = cursor.fetchone()
    
    if not order_data:
        flash("Order not found.", "danger")
        return redirect(url_for('revenue_dashboard'))

    if not is_admin and (not org_id or order_data['org_id'] != org_id):
        flash("Unauthorized action.", "danger")
        return redirect(url_for('revenue_dashboard'))

    # 2. Perform Action
    if action == 'pay':
        cursor.execute("UPDATE payments SET status = 'SUCCEEDED' WHERE order_id = %s", (order_id,))
        flash(f"Order #{order_id} marked as PAID.", "success")
    elif action == 'cancel':
        cursor.execute("UPDATE payments SET status = 'FAILED' WHERE order_id = %s", (order_id,))
        flash(f"Order #{order_id} has been CANCELLED.", "warning")
    
    db.commit()
    return redirect(url_for('revenue_dashboard'))

@app.route("/revenue")
@login_required
def revenue_dashboard():
    db, cursor = get_db()
    is_admin = session.get('is_admin', False)
    org_id = session.get('org_id')
    
    event_rows = []
    pending_orders = []

    # 1. FETCH REVENUE STATS (Existing Logic)
    if is_admin:
        cursor.callproc('GetAdminRevenueReport')
        for result in cursor.stored_results():
            event_rows = result.fetchall()
        
        # Admin pending query (See ALL pending)
        cursor.execute("""
            SELECT o.order_id, u.full_name, u.student_id, e.title, p.amount_cents, o.created_at
            FROM orders o
            JOIN users u ON o.buyer_user_id = u.user_id
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN tickets t ON oi.ticket_id = t.ticket_id
            JOIN events e ON t.event_id = e.event_id
            JOIN payments p ON o.order_id = p.order_id
            WHERE p.status = 'PENDING'
            ORDER BY o.created_at DESC
        """)
        pending_orders = cursor.fetchall()
        
        total_rev = sum(row['revenue_cents'] for row in event_rows)
        total_tix = sum(row['tickets_sold'] for row in event_rows)
        
        stats = {
            'role': 'Admin (7% Cut)',
            'total_revenue': f"${total_rev / 100:,.2f}",
            'total_tickets_sold': total_tix,
            'events_hosted': len(event_rows)
        }
        
    else:
        cursor.callproc('GetOrgRevenueReport', [org_id])
        for result in cursor.stored_results():
            event_rows = result.fetchall()

        # Org pending query (See ONLY their events)
        cursor.execute("""
            SELECT o.order_id, u.full_name, u.student_id, e.title, p.amount_cents, o.created_at
            FROM orders o
            JOIN users u ON o.buyer_user_id = u.user_id
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN tickets t ON oi.ticket_id = t.ticket_id
            JOIN events e ON t.event_id = e.event_id
            JOIN payments p ON o.order_id = p.order_id
            WHERE p.status = 'PENDING' AND e.org_id = %s
            ORDER BY o.created_at DESC
        """, (org_id,))
        pending_orders = cursor.fetchall()

        total_rev = sum(row['revenue_cents'] for row in event_rows)
        total_tix = sum(row['tickets_sold'] for row in event_rows)
        
        stats = {
            'role': 'Organization (Net Revenue)',
            'total_revenue': f"${total_rev / 100:,.2f}",
            'total_tickets_sold': total_tix,
            'events_hosted': len(event_rows)
        }

    return render_template("revenue.html", 
                           stats=stats, 
                           event_rows=event_rows, 
                           pending_orders=pending_orders, # Pass pending orders to template
                           is_admin=is_admin)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)