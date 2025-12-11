# app.py
import os
import mysql.connector
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session, g, flash
)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_very_fallback_secret_key')

# Database Connection Management

def get_db():
    """
    Get a database connection for the current request.
    If one isn't already available, create it.
    """
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=os.environ.get('MYSQL_HOST', 'localhost'),
            port=os.environ.get('MYSQL_PORT', 3307), 
            user=os.environ.get('MYSQL_USER'),
            password=os.environ.get('MYSQL_PASSWORD'),
            database=os.environ.get('MYSQL_DATABASE')
        )
        g.cursor = g.db.cursor(dictionary=True)
    return g.db, g.cursor

@app.teardown_appcontext
def close_db(e=None):
    """
    Close the database connection at the end of the request.
    """
    cursor = g.pop('cursor', None)
    if cursor is not None:
        cursor.close()
    
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Authentication Decorator

def login_required(f):
    """
    A decorator to restrict access to organization-only pages.
    As noted in your HTML comments.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'org_id' not in session:
            return redirect(url_for('login_register'))
        return f(*args, **kwargs)
    return decorated_function

# Routes for Serving HTML Pages (GET Requests)

@app.route("/")
def index():
    """
    Render the homepage.
    We will fetch and display published events.
    """
    db, cursor = get_db()
    
    # Query to get events and their organization names
    query = """
    SELECT 
        e.event_id, e.title, e.venue, e.starts_at, e.ends_at,
        o.org_name
    FROM events e
    JOIN organizations o ON e.org_id = o.org_id
    WHERE e.is_published = TRUE
    ORDER BY e.starts_at ASC
    LIMIT 6; 
    """
    cursor.execute(query)
    events = cursor.fetchall()
    
    return render_template("index.html", events=events)

@app.route("/events")
def event_list():
    """
    Render the event details/list page.
    This dynamically pulls all events from the 'events' table.
    """
    db, cursor = get_db()
    
    # Same query as index, but without the limit
    query = """
    SELECT 
        e.event_id, e.title, e.venue, e.starts_at, e.ends_at,
        o.org_name, t.price_cents
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
    """
    Handle GET requests for the login/register page
    and POST requests for both login and registration forms.
    """
    if request.method == "POST":
        
        # IF REGISTER FORM 
        # org_name = request.form['orgName']
        # email = request.form['orgEmail']
        # password = request.form['orgPassword'] 
        # TODO: Hash the password (e.g., with werkzeug.security)
        # TODO: Insert new org into 'organizations' table
        # TODO: Log them in by setting session['org_id']
        # return redirect(url_for('create_event'))

        # IF LOGIN FORM
        # email = request.form['loginEmail']
        # password = request.form['loginPassword']
        # TODO: Query 'organizations' table for user by email
        # TODO: Check if user exists and password hash matches
        # TODO: If valid, set session['org_id'] = org.org_id
        # return redirect(url_for('create_event'))
        
        pass # Remove this once logic is added

    # For a GET request, just show the page
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Clear the session to log the organization out."""
    session.clear()
    return redirect(url_for('index'))

@app.route("/register", methods=["GET", "POST"])
def register_for_event():
    """
    Handle user registration for a specific event.
    """
    if request.method == "POST":
        # Handle Event Registration Form
        # event_id = request.form['event']
        # full_name = request.form['fullname']
        # email = request.form['email']
        # ... other form fields ...
        
        # TODO: Check if user exists in 'users' table, if not, create one.
        # TODO: Create an 'orders' record.
        # TODO: Create 'order_items' record.
        # TODO: Create a 'payments' record.
        # TODO: Check if event capacity/ticket quantity is exceeded.
        
        # On success, redirect to the thank you page
        return redirect(url_for('thank_you'))
        
    # For a GET request, show the registration form
    # We should pass the list of events to the dropdown
    db, cursor = get_db()
    cursor.execute("SELECT event_id, title FROM events WHERE is_published = TRUE ORDER BY title")
    events = cursor.fetchall()
    
    return render_template("register.html", events=events)

@app.route("/thank-you")
def thank_you():
    """Render the thank you page after registration."""
    return render_template("thank-you.html")

# Organization-Only Routes 
# These routes are protected by our @login_required decorator

@app.route("/create-event", methods=["GET", "POST"])
@login_required
def create_event():
    """
    Allow logged-in organizations to create new events.
    """
    if request.method == "POST":
        # Handle Create Event Form
        # org_id = session['org_id'] # Get the logged-in org's ID
        # title = request.form['eventName']
        # starts_at = request.form['eventDate']
        # ... other form fields ...
        
        # TODO: Insert into 'events' table
        # TODO: Insert into 'tickets' table (from price/quantity)
        
        # On success, redirect to a confirmation or event page
        # For now, we'll use the thank_you.html page as a placeholder
        return redirect(url_for('thank_you'))

    # For a GET request, just show the form
    return render_template("create-event.html")

@app.route("/revenue")
@login_required
def revenue_dashboard():
    """
    Show the revenue dashboard for the logged-in organization.
    """
    # org_id = session['org_id'] # Get the logged-in org's ID
    
    # TODO: Write complex SQL queries to aggregate revenue:
    # 1. Get total revenue (SUM payments WHERE order_id is in (orders...))
    # 2. Get total tickets sold (SUM order_items...)
    # 3. Get events hosted (COUNT events...)
    # All queries should be filtered by `org_id`
    
    # Pass placeholder data for now
    stats = {
        'total_revenue': 0,
        'total_tickets_sold': 0,
        'events_hosted': 0,
        'avg_attendance': "0%"
    }
    event_rows = []

    return render_template("revenue.html", stats=stats, event_rows=event_rows)


# Run the Application

if __name__ == "__main__":
    app.run(debug=True, port=5000)