import os
import re
import random
import pandas as pd
import ngrok
import time
import json
import stripe
import requests
import logging
from datetime import date, datetime
from dotenv import load_dotenv  # <--- Load environment variables first!
load_dotenv()

from itsdangerous import URLSafeTimedSerializer as Serializer
from flask_mail import Mail, Message
from flask import Flask, request, render_template, session, jsonify, abort, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from Excel_Manager import ExcelManager
from Card_Filter import db, Card
from synergy_engine import run_synergy_analysis
from puzzle_engine import (
    get_random_puzzle, 
    validate_user_sequence, 
    get_all_puzzles,
    get_bonus_level_puzzle, 
    generate_puzzle_from_blueprint, 
    PUZZLE_POOL
)

app = Flask(__name__)
csrf = CSRFProtect(app)  # <--- Ensures all POST forms are cryptographically protected

# Add these right under your app configuration
app.config['SESSION_COOKIE_SECURE'] = True      # Forces cookies to only transmit over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True    # Prevents JavaScript (XSS) from stealing session cookies
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # Protects against cross-site request forgery

# --- Enforce Secure Secret Key ---
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set!")
app.secret_key = secret_key

# --- Database Configuration ---
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'cheepcards.db')}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("STRIPE KEY CHECK:", os.getenv("STRIPE_SECRET_KEY"))

# Reads 'True' or 'False' from your environment variables
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'False').lower() == 'true'

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Load disposable domains list on startup
DISPOSABLE_DOMAINS = set()
if os.path.exists('disposable_domains.json'):
    with open('disposable_domains.json', 'r') as f:
        DISPOSABLE_DOMAINS = set(json.load(f))

manager = ExcelManager("Magic Card Data Base Current View.xlsx")

SEARCH_CLUSTERS = {}

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # Catches server hiccups or database dropped connections
    return render_template('500.html'), 500

def validate_password_strength(password):
    """
    Ensures password meets complexity criteria:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special symbol
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must include at least one lowercase letter."
    if not re.search(r"\d", password):
        return "Password must include at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must include at least one special symbol."
    return None

# --- Flask-Mail Configuration ---
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp-relay.brevo.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)


# --- Maintenance Mode Guard with Developer Bypass ---
@app.before_request
def check_maintenance():
    # If maintenance mode is OFF, let everyone through normally
    if not MAINTENANCE_MODE:
        return

    # Allow static files (CSS/images/JS) so the maintenance page styles correctly
    if request.endpoint == 'static':
        return
        
    # Allow the secret unlock route itself so you can activate your session
    if request.endpoint == 'dev_unlock':
        return
        
    # If you have already used your secret token on this browser/device, let you pass
    if session.get('dev_bypass'):
        return
        
    # Block everyone else and show the Coming Soon page
    return render_template('maintenance.html'), 503


@app.route('/dev-unlock')
def dev_unlock():
    """Secret route to grant your browser access while maintenance mode is ON."""
    token = request.args.get('token')
    secret_token = os.environ.get('DEV_UNLOCK_TOKEN')
    
    if token and secret_token and token == secret_token:
        session['dev_bypass'] = True
        flash("Developer bypass activated!", "success")
        return redirect(url_for('home')) # Change 'index' to your main home route name if different
        
    abort(403)

def get_reset_token(user, expires_sec=1800):
    s = Serializer(app.config['SECRET_KEY'])
    return s.dumps({'user_id': user.id}, salt='password-reset-salt')

def verify_reset_token(token, expires_sec=1800):
    s = Serializer(app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, salt='password-reset-salt', max_age=expires_sec)['user_id']
    except Exception:
        return None
    return User.query.get(user_id)

# --- DATABASE MODELS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    
    # Stripe & Subscription Mapping
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), default='free') 
    pro_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Existing App Fields
    default_theme = db.Column(db.String(50), default='dark-mode')
    name_tag_color = db.Column(db.String(50), default='blue')
    bonus_completed = db.Column(db.Boolean, default=False)
    copper_completed = db.Column(db.Boolean, default=False)
    gold_completed = db.Column(db.Boolean, default=False)
    search_count = db.Column(db.Integer, default=0)
    last_search_date = db.Column(db.Date, nullable=True)
    
    decks = db.relationship('SavedDeck', backref='owner', lazy=True)

class SavedDeck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    card_data = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class BudgetCardHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_name = db.Column(db.String(150), unique=True, nullable=False)
    date_used = db.Column(db.Date, nullable=False)

class SearchLog(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    card_name = db.Column(db.String(100), nullable=True)
    colors = db.Column(db.String(50), nullable=True)
    classes = db.Column(db.String(100), nullable=True)
    rank_searched = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)

# Temporary in-memory staging dictionary for unranked card reviews
STAGED_EDITS = {}

@app.route('/review/card/<target_class>')
@login_required
def review_card(target_class):
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('home'))

    file_path = "Magic Card Data Base Current View.xlsx"
    if hasattr(manager, 'file_path'):
        file_path = manager.file_path
    elif hasattr(manager, 'path'):
        file_path = manager.path
        
    df = pd.read_excel(file_path, engine="openpyxl")
    
    name_col = next((c for c in df.columns if 'name' in c.strip().lower() or 'title' in c.strip().lower()), df.columns[0])
    class1_col = next((c for c in df.columns if 'class' in c.strip().lower()), df.columns[1])
    rank_col = next((c for c in df.columns if 'rank' in c.strip().lower()), df.columns[2])

    # Apply active in-memory staged edits so reviewed cards don't reappear before saving
    for c_idx, edit_data in STAGED_EDITS.items():
        if c_idx in df.index:
            df.loc[c_idx, class1_col] = edit_data['new_class']
            df.loc[c_idx, rank_col] = edit_data['new_rank']

    unranked_subset = df[
        (df[class1_col].astype(str).str.strip().str.lower() == target_class.strip().lower()) & 
        (df[rank_col].isna() | (df[rank_col].astype(str).str.strip() == '') | (df[rank_col].astype(str).str.strip().str.lower() == 'nan'))
    ]

    remaining_count = len(unranked_subset)
    if remaining_count == 0:
        save_btn_html = ""
        if STAGED_EDITS:
            save_btn_html = f'<form action="{url_for("review_save_all")}" method="POST" style="margin-top:20px;"><button type="submit" style="background:#27ae60;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;">💾 Save {len(STAGED_EDITS)} Staged Changes to Excel</button></form>'
        return f"<h1>All cards in class '{target_class}' are fully ranked! (Staged changes pending: {len(STAGED_EDITS)})</h1>{save_btn_html}<p><a href='/'>Home</a></p>"

    target_row = unranked_subset.iloc[0]
    card_idx = target_row.name
    card_name = str(target_row[name_col]).strip()
    clean_name = card_name.split(" // ")[0].strip()

    image_url = "https://cards.scryfall.io/normal/front/0/0/00000000-0000-0000-0000-000000000000.jpg"
    try:
        resp = requests.get(f"https://api.scryfall.com/cards/named?exact={clean_name}", headers={"User-Agent": "CheepCardsApp/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            if 'image_uris' in data:
                image_url = data['image_uris']['normal']
            elif 'card_faces' in data:
                image_url = data['card_faces'][0]['image_uris']['normal']
    except Exception:
        pass

    return render_template(
        'review.html',
        card_name=card_name,
        card_idx=card_idx,
        target_class=target_class,
        remaining_count=remaining_count,
        image_url=image_url,
        staged_count=len(STAGED_EDITS)
    )

@app.route('/review/submit', methods=['POST'])
@login_required
def review_submit():
    if current_user.role != 'admin':
        abort(403)

    card_idx = int(request.form['card_idx'])
    target_class = request.form['target_class']
    new_class = request.form['new_class']
    new_rank = request.form['new_rank']

    # Store edit in memory instantly with zero disk lag
    STAGED_EDITS[card_idx] = {
        'new_class': new_class,
        'new_rank': new_rank
    }

    flash(f"Card staged successfully. ({len(STAGED_EDITS)} changes pending save)", "info")
    return redirect(url_for('review_card', target_class=target_class))

@app.route('/review/save_all', methods=['POST'])
@login_required
def review_save_all():
    if current_user.role != 'admin':
        abort(403)

    if not STAGED_EDITS:
        flash("No staged changes to save.", "warning")
        return redirect(url_for('home'))

    if hasattr(manager, '_create_timestamped_backup'):
        manager._create_timestamped_backup()

    file_path = "Magic Card Data Base Current View.xlsx"
    if hasattr(manager, 'file_path'):
        file_path = manager.file_path
    elif hasattr(manager, 'path'):
        file_path = manager.path

    import openpyxl
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    headers = [cell.value for cell in ws[1]]
    class1_col_idx = next((i + 1 for i, h in enumerate(headers) if h and 'class' in str(h).strip().lower()), 2)
    rank_col_idx = next((i + 1 for i, h in enumerate(headers) if h and 'rank' in str(h).strip().lower()), 3)

    count = len(STAGED_EDITS)
    for card_idx, data in STAGED_EDITS.items():
        excel_row = card_idx + 2
        ws.cell(row=excel_row, column=class1_col_idx, value=data['new_class'])
        ws.cell(row=excel_row, column=rank_col_idx, value=data['new_rank'])

    wb.save(file_path)
    STAGED_EDITS.clear()

    if hasattr(manager, 'load_cards'):
        manager.load_cards()

    flash(f"Successfully bulk saved {count} card reviews to Excel!", "success")
    return redirect(url_for('home'))

@app.route('/healthz')
def healthz():
    return 'OK', 200

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPER FUNCTIONS ---

def get_rank_word_from_value(val):
    # If Excel_Manager passes a word or number, map it safely for frontend display
    if isinstance(val, str):
        text_map = {"optimized": "Optimized", "fast": "Fast", "average": "Average", "passive": "Passive", "low": "Low"}
        return text_map.get(val.strip().lower(), "Average")
    
    try:
        v = int(val)
    except (ValueError, TypeError):
        v = 3
    
    RANK_WORD_MAP = {
        5: "Optimized",
        4: "Fast",
        3: "Average",
        2: "Passive",
        1: "Low"
    }
    return RANK_WORD_MAP.get(v, "Average")

def get_daily_budget_card():
    today = date.today()
    if today.month == 1 and today.day == 1:
        db.session.execute(db.delete(BudgetCardHistory))
        db.session.commit()

    # Check if a budget card was already picked for today
    stmt = db.select(BudgetCardHistory).filter_by(date_used=today)
    today_record = db.session.execute(stmt).scalar_one_or_none()

    if today_record:
        matched_card = next((c for c in manager.card_pool if getattr(c, 'name', '').lower() == today_record.card_name.lower()), None)
        if matched_card:
            r1_word = str(getattr(matched_card, 'ranking_1_word', 'none')).strip()
            r2_word = str(getattr(matched_card, 'ranking_2_word', 'none')).strip()
            word = r1_word if r1_word.lower() != "none" and r1_word != "" else r2_word
            matched_card.active_rank_word = word.capitalize() if word.lower() != "none" and word != "" else "Average"
            
            c1 = str(getattr(matched_card, 'card_class_1', 'none')).strip()
            matched_card.display_class = c1 if c1.lower() != "none" and c1 != "" else getattr(matched_card, 'card_class_2', 'N/A')
            return matched_card

    used_stmt = db.select(BudgetCardHistory.card_name)
    used_names = {name.lower() for name in db.session.execute(used_stmt).scalars().all()}
    
    eligible_cards = []
    for card in manager.card_pool:
        name = getattr(card, 'name', '')
        if name.lower() in used_names:
            continue
            
        try:
            # 1. Price check <= $1.00
            price = float(getattr(card, 'price', 0.0) or 0.0)
            if price > 1.00:
                continue

            # 2. Class check: must have a valid class in card_class_1 or card_class_2
            c1 = str(getattr(card, 'card_class_1', 'none')).strip().lower()
            c2 = str(getattr(card, 'card_class_2', 'none')).strip().lower()
            has_class = (c1 and c1 != 'none' and c1 != 'nan') or (c2 and c2 != 'none' and c2 != 'nan')
            if not has_class:
                continue

            # 3. Rank check: Average or better means numeric value >= 3 (3=Average, 4=Fast, 5=Optimized)
            r1_val = int(getattr(card, 'ranking_1_value', 0) or 0)
            r2_val = int(getattr(card, 'ranking_2_value', 0) or 0)
            max_rank = max(r1_val, r2_val)

            if max_rank >= 3:
                eligible_cards.append(card)
        except (ValueError, TypeError):
            continue

    if not eligible_cards:
        return None

    # Randomize from the strictly filtered Excel card pool
    chosen_card = random.choice(eligible_cards)
    
    r1_word = str(getattr(chosen_card, 'ranking_1_word', 'none')).strip()
    r2_word = str(getattr(chosen_card, 'ranking_2_word', 'none')).strip()
    word = r1_word if r1_word.lower() != "none" and r1_word != "" else r2_word
    chosen_card.active_rank_word = word.capitalize() if word.lower() != "none" and word != "" else "Average"

    # Apply title casing to newly chosen card
    c1 = str(getattr(chosen_card, 'card_class_1', 'none')).strip()
    raw_class = c1 if c1.lower() != "none" and c1 != "" else str(getattr(chosen_card, 'card_class_2', 'N/A')).strip()
    chosen_card.display_class = raw_class.title() if raw_class.lower() != "none" and raw_class != "" else "N/A"

    new_history = BudgetCardHistory(card_name=getattr(chosen_card, 'name'), date_used=today)
    db.session.add(new_history)
    db.session.commit()

    return chosen_card

def render_mana_pips(identity_str):
    if not identity_str or str(identity_str).strip() == "" or str(identity_str).lower() == "nan":
        return '<div class="mana-badge-container"><span class="mana-pip pip-c" title="Colorless">C</span></div>'
    
    clean_val = str(identity_str).strip().upper()
    
    if "NONE" in clean_val or "COLORLESS" in clean_val or clean_val == "C":
        return '<div class="mana-badge-container"><span class="mana-pip pip-c" title="Colorless">C</span></div>'

    chars = [c for c in clean_val if c in ['W', 'U', 'B', 'R', 'G', 'C']]
    
    if not chars:
        return '<div class="mana-badge-container"><span class="mana-pip pip-c" title="Colorless">C</span></div>'
        
    html = '<div class="mana-badge-container">'
    for char in chars:
        css_class = f"pip-{char.lower()}" if char.lower() in ['w', 'u', 'b', 'r', 'g', 'c'] else "pip-c"
        html += f'<span class="mana-pip {css_class}" title="{char}">{char}</span>'
    html += '</div>'
    return html

app.jinja_env.filters['mana_pips'] = render_mana_pips

# --- APPLICATION ROUTES ---

@app.route("/")
def home():
    budget_card = get_daily_budget_card()
    return render_template("home.html", budget_card=budget_card)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Please check your login details and try again.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('sandbox_role', None)
    logout_user()
    flash("Logged out successfully.")
    return redirect(url_for('home'))

@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    selected_colors = request.form.getlist('colors') or request.args.getlist('colors')
    selected_classes = request.form.getlist('classes') or request.args.getlist('classes')
    selected_rank = request.form.get('rank') or request.args.get('rank', '')

    filtered_results = []

    colors_str = ", ".join(selected_colors) if selected_colors else None
    classes_str = ", ".join(selected_classes) if selected_classes else None
    top_result_card = filtered_results[0].name if filtered_results else None

    if selected_colors or selected_classes or selected_rank or top_result_card:
        new_log = SearchLog(
            card_name=top_result_card,
            colors=colors_str,
            classes=classes_str,
            rank_searched=selected_rank if selected_rank else None
        )
        db.session.add(new_log)
        db.session.commit()

    return render_template(
        "dashboard.html",
        report=None,
        search_reports=None,
        deck_input="", 
        selected_colors=selected_colors, 
        selected_classes=selected_classes, 
        selected_rank=selected_rank, 
        price_tier="all", 
        custom_price="", 
        selected_keyword=""
    )

@app.before_request
def check_daily_search_reset():
    if current_user.is_authenticated and current_user.role == 'free':
        today = date.today()
        if current_user.last_search_date != today:
            current_user.search_count = 0
            current_user.last_search_date = today
            db.session.commit()

@app.route("/toggle-theme")
def toggle_theme():
    current_theme = session.get('theme', 'dark')
    new_theme = 'light' if current_theme == 'dark' else 'dark'
    session['theme'] = new_theme
    
    if current_user.is_authenticated:
        current_user.default_theme = new_theme
        db.session.commit()
        
    return redirect(request.referrer or url_for('home'))

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        message = request.form.get('message')
        
        if not message:
            flash("Please enter a feedback message.", "error")
            return redirect(url_for('feedback'))
            
        username = current_user.username if current_user.is_authenticated else "Guest User"
        email = getattr(current_user, 'email', None) or "guest@cheepcards.local"
        category = "General"
        
        new_feedback = Feedback(
            username=username,
            email=email,
            category=category,
            message=message
        )
        db.session.add(new_feedback)
        db.session.commit()
        
        # Optional: Send email notification if SMTP environment variables are set
        try:
            smtp_server = os.environ.get('MAIL_SERVER')
            smtp_port = int(os.environ.get('MAIL_PORT', 587))
            smtp_user = os.environ.get('MAIL_USERNAME')
            smtp_pass = os.environ.get('MAIL_PASSWORD')
            admin_email = os.environ.get('ADMIN_EMAIL', smtp_user)
            
            if smtp_server and smtp_user and smtp_pass:
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = admin_email
                msg['Subject'] = f"New CheepCards Feedback from {username}"
                
                body = f"Category: {category}\nUser: {username} ({email})\n\nMessage:\n{message}"
                msg.attach(MIMEText(body, 'plain'))
                
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
        except Exception as e:
            print(f"⚠️ Email notification warning: {e}")
        
        flash("Thank you for your feedback! It has been successfully recorded.", "success")
        return redirect(url_for('news.public_news'))
        
    return render_template('feedback.html')

@app.route("/synergy", methods=["POST"])
def synergy():
    active_role = get_active_role() if 'get_active_role' in globals() else current_user.role

    if not current_user.is_authenticated or active_role == 'free':
        flash("⚡ The Synergy Engine is a Member-exclusive feature! Upgrade to unlock.")
        return redirect(url_for('home'))
        
    decklist_raw = request.form.get("decklist", "")
    deck_input = decklist_raw 
    deck_lines = [line.strip() for line in decklist_raw.split("\n") if line.strip()]
    report = run_synergy_analysis(deck_lines) if deck_lines else {}

    return render_template(
        "dashboard.html", 
        report=report, 
        deck_input=deck_input,
        search_reports=[], 
        selected_colors=[], 
        selected_classes=[], 
        selected_rank="",
        price_tier="all",
        custom_price="",
        selected_keyword=""
    )

@app.route("/search", methods=["POST"])
def search():
    active_role = get_active_role() if 'get_active_role' in globals() else current_user.role
    
    if current_user.is_authenticated and active_role == 'free':
        today_str = str(date.today())
        last_date_str = str(current_user.last_search_date) if current_user.last_search_date else ""
        
        if last_date_str != today_str:
            current_user.search_count = 0
            current_user.last_search_date = date.today()
            db.session.commit()
            
        if current_user.search_count >= 15:
            flash("MAX_SEARCH_REACHED")
            return redirect(url_for('home'))
            
        current_user.search_count += 1
        db.session.commit()
        
    session['current_rerolls'] = 0

    deck_input = request.form.get('decklist', '')
    raw_colors = request.form.getlist("colors")
    colors = []
    for c in raw_colors:
        colors.extend([x.strip().upper() for x in c.split(',') if x.strip()])
        
    raw_classes = request.form.getlist("classes")
    classes = []
    for c in raw_classes:
        classes.extend([x.strip().lower() for x in c.split(',') if x.strip()])

    rank = str(request.form.get("rank", "")).strip().lower()
    price_tier = str(request.form.get("price_tier", "all")).strip().lower()
    custom_price = request.form.get("custom_price", "").strip()
    keyword = request.form.get("keyword", "").strip().lower()
    
    search_reports = []
    SEARCH_CLUSTERS.clear() 
    target_classes = classes if classes else ["all available cards"]
    
    RANK_MAP = {"optimized": 5, "fast": 4, "average": 3, "passive": 2, "low": 1}
    target_start_rank = RANK_MAP.get(rank, 5)

    for target_class in target_classes:
        clean_target_class = target_class.strip().lower()
        
        # Query PostgreSQL directly instead of relying solely on ExcelManager memory pool
        if clean_target_class == "all available cards":
            class_results = Card.query.all()
        else:
            class_results = Card.query.filter(
                db.or_(
                    db.func.lower(Card.card_class_1).contains(clean_target_class),
                    db.func.lower(Card.card_class_2).contains(clean_target_class)
                )
            ).all()

        filtered_results = []
        for card in class_results:
            if keyword:
                card_text = str(getattr(card, 'oracle_text', '')).lower()
                card_name = str(getattr(card, 'name', '')).lower()
                if keyword not in card_text and keyword not in card_name:
                    continue

            c1_val = str(getattr(card, 'card_class_1', 'none')).strip().lower()
            c2_val = str(getattr(card, 'card_class_2', 'none')).strip().lower()
            
            r1_word = str(getattr(card, 'ranking_1_word', 'none')).strip().lower()
            r2_word = str(getattr(card, 'ranking_2_word', 'none')).strip().lower()
            
            r1_val = getattr(card, 'ranking_1_value', 0)
            r2_val = getattr(card, 'ranking_2_value', 0)

            current_card_rank_word = "none"
            current_card_rank_value = 0
            
            if clean_target_class == "all available cards":
                current_card_rank_word = r1_word if r1_word != "none" else r2_word
                current_card_rank_value = r1_val if r1_val > 0 else r2_val
            elif clean_target_class in c1_val:
                current_card_rank_word = r1_word if r1_word != "none" else r2_word
                current_card_rank_value = r1_val if r1_val > 0 else r2_val
            elif clean_target_class in c2_val:
                current_card_rank_word = r2_word if r2_word != "none" else r1_word
                current_card_rank_value = r2_val if r2_val > 0 else r1_val
            else:
                current_card_rank_word = r1_word if r1_word != "none" else r2_word
                current_card_rank_value = r1_val if r1_val > 0 else r2_val

            card.active_priority_val = int(current_card_rank_value)
            card.active_rank_word = current_card_rank_word.capitalize()

            card_type = str(getattr(card, 'card_type', getattr(card, 'type', ''))).lower()
            is_land = "land" in card_type or c1_val == "land" or c2_val == "land"
            card_identity = str(getattr(card, 'identity', '')).upper().strip()
            clean_db_identity = [char for char in card_identity if char in "WUBRG"]
            is_colorless_utility = is_land and len(clean_db_identity) == 0

            if rank and rank not in ["", "all", "none"]:
                if card.active_priority_val > target_start_rank and not (is_colorless_utility and keyword):
                    continue

            if colors and len(colors) > 0 and "ALL" not in colors:
                card_identity = str(getattr(card, 'identity', '')).upper().strip()
                clean_db_identity = [char for char in card_identity if char in "WUBRG"]
                
                card_type = str(getattr(card, 'card_type', getattr(card, 'type', ''))).lower()
                is_land = "land" in card_type or c1_val == "land" or c2_val == "land"
                
                is_rainbow_land = len(clean_db_identity) >= 4 or set(clean_db_identity) == set("WUBRG")
                
                if is_land and (len(clean_db_identity) == 0 or is_rainbow_land):
                    pass
                elif len(clean_db_identity) == 0:
                    if 'C' not in colors and 'COLORLESS' not in colors:
                        continue
                else:
                    if not all(symbol in colors for symbol in clean_db_identity):
                        continue

            card_price = float(getattr(card, 'price', 0.0))
            if custom_price:
                try:
                    if card_price > float(custom_price):
                        continue
                except ValueError:
                    pass
            elif price_tier == "low" and card_price >= 1.00:
                continue
            elif price_tier == "medium" and (card_price < 1.00 or card_price > 2.00):
                continue
            elif price_tier == "high" and card_price <= 2.00:
                continue
                
            filtered_results.append(card)

        target_limit = 10
        if keyword and len(filtered_results) < target_limit:
            fallback_pool = []
            for card in class_results:
                if card in filtered_results:
                    continue
                
                card_text = str(getattr(card, 'oracle_text', '')).lower()
                card_name = str(getattr(card, 'name', '')).lower()
                if keyword not in card_text and keyword not in card_name:
                    continue

                card_identity = str(getattr(card, 'identity', '')).upper().strip()
                clean_db_identity = [char for char in card_identity if char in "WUBRG"]
                
                if len(clean_db_identity) > 0:
                    continue

                if rank and rank not in ["", "all", "none"]:
                    if getattr(card, 'active_priority_val', 0) > target_start_rank:
                        continue

                card_price = float(getattr(card, 'price', 0.0))
                if custom_price:
                    try:
                        if card_price > float(custom_price): continue
                    except ValueError: pass
                elif price_tier == "low" and card_price >= 1.00: continue
                elif price_tier == "medium" and (card_price < 1.00 or card_price > 2.00): continue
                elif price_tier == "high" and card_price <= 2.00: continue

                fallback_pool.append(card)

            if fallback_pool:
                filtered_results.extend(fallback_pool)

        tier_groups = {}
        for card in filtered_results:
            rank_val = card.active_priority_val
            tier_groups.setdefault(rank_val, []).append(card)

        final_selected_cards = []
        target_limit = 10

        valid_ranks = [r for r in tier_groups.keys() if r <= target_start_rank]
        for rank_val in sorted(valid_ranks, reverse=True):
            tier_cards = tier_groups[rank_val]
            needed_slots = target_limit - len(final_selected_cards)
            
            if needed_slots <= 0:
                break

            if len(tier_cards) <= needed_slots:
                final_selected_cards.extend(tier_cards)
            else:
                shuffled_tier = tier_cards.copy()
                random.shuffle(shuffled_tier)
                final_selected_cards.extend(shuffled_tier[:needed_slots])
                break

        display_title = "All Available Cards" if clean_target_class == "all available cards" else target_class.capitalize()
        
        SEARCH_CLUSTERS[display_title] = [
            {
                "name": getattr(card, 'name', ''),
                "mana_cost": getattr(card, 'mana_cost', ''),
                "identity": getattr(card, 'identity', ''),
                "price": getattr(card, 'price', 0.0),
                "image_url": getattr(card, 'image_url', ''),
                "active_rank_word": getattr(card, 'active_rank_word', 'None')
            }
            for card in filtered_results
        ]
        
        search_reports.append({
            "class_name": display_title,
            "results": final_selected_cards
        })

    if current_user.is_authenticated:
        max_pool_price = max([float(getattr(c, 'price', 0.0)) for c in manager.card_pool], default=0.0)
        
        has_penny = False
        has_max_price = False
        
        for report in search_reports:
            for card in report.get("results", []):
                try:
                    p = float(getattr(card, 'price', 0.0))
                    if abs(p - 0.01) < 0.001:
                        has_penny = True
                    if max_pool_price > 0 and abs(p - max_pool_price) < 0.001:
                        has_max_price = True
                except (ValueError, TypeError):
                    pass
                    
        achievements_unlocked = False
        unlocked_names = []
        
        if has_penny and not getattr(current_user, 'copper_completed', False):
            current_user.copper_completed = True
            unlocked_names.append("Brushed Copper Tag 🥉")
            achievements_unlocked = True
            
        if has_max_price and not getattr(current_user, 'gold_completed', False):
            current_user.gold_completed = True
            unlocked_names.append("24K Sovereign Gold Tag ✨")
            achievements_unlocked = True
            
        if achievements_unlocked:
            db.session.commit()
            flash(f"🎉 Secret Achievement Unlocked: {', '.join(unlocked_names)}! Go equip it in your account settings.", "success")

    return render_template(
        "dashboard.html", 
        search_reports=search_reports, 
        selected_colors=colors, 
        selected_classes=classes, 
        selected_rank=rank,
        price_tier=price_tier,
        custom_price=custom_price,
        selected_keyword=keyword
    )

@app.route('/reroll', methods=['POST'])
def reroll_card():
    if current_user.is_authenticated and current_user.role == 'free':
        used_rerolls = session.get('current_rerolls', 0)
        if used_rerolls >= 3:
            return jsonify({'success': False, 'message': 'Free users are limited to 3 swaps per search!'})
        
        session['current_rerolls'] = used_rerolls + 1

    data = request.json or {}
    category = data.get('category')
    current_names = data.get('current_names', [])
    
    category_pool = SEARCH_CLUSTERS.get(category, [])

    if not category_pool:
        return jsonify({'success': False, 'message': 'No cached search pool found.'})

    available_candidates = [
        card for card in category_pool 
        if card.get('name') not in current_names
    ]

    if not available_candidates:
        return jsonify({'success': False, 'message': 'No remaining unused cards in this cluster!'})

    replacement_card = random.choice(available_candidates)

    card_name = replacement_card.get('name', '')
    card_mana = replacement_card.get('mana_cost', '')
    card_identity = replacement_card.get('identity', '')
    card_price = replacement_card.get('price', 0.0)
    card_image = replacement_card.get('image_url', '')
    card_rank = replacement_card.get('active_rank_word', 'None')

    new_card_data = {
        "name": card_name,
        "mana_cost": card_mana,
        "identity": render_mana_pips(card_identity), 
        "price": card_price,
        "image_url": card_image,
        "active_rank_word": card_rank
    }

    return jsonify({'success': True, 'new_card': new_card_data})

STRIPE_PRICE_ID = "price_1UD8xLFptxxDBwjmVmE8DV1W"

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('cancel', _external=True),
    )
    return redirect(checkout_session.url, code=303)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/success')
def success():
    flash("🎉 Welcome to Pro! Your subscription was successful.", "success")
    return redirect(url_for('account'))

@app.route('/cancel')
def cancel():
    flash("Checkout was canceled. Feel free to try again whenever you're ready.", "warning")
    return redirect(url_for('pricing'))

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route('/arcade')
def arcade():
    requested_level = request.args.get("level")
    if requested_level == "Bonus":
        if not session.get('bonus_unlocked', False):
            flash("Bonus level is locked! Clear all 12 levels under 5 minutes first.", "warning")
            return redirect(url_for('level_select'))
        session['arcade_level'] = "Bonus"
        session['is_bonus_level'] = True

    if 'arcade_level' not in session:
        session['arcade_level'] = 1
        session['total_solve_time'] = 0  
        session['bonus_unlocked'] = False
        session.pop('is_bonus_level', None)
        
    current_level = session['arcade_level']
    mode = request.args.get("mode", "")
    
    if mode == "practice":
        puzzle = get_random_puzzle()
    elif current_level == "Bonus":
        puzzle = get_bonus_level_puzzle()
    else:
        puzzle_index = (int(current_level) - 1) % len(PUZZLE_POOL)
        blueprint = PUZZLE_POOL[puzzle_index]
        puzzle = generate_puzzle_from_blueprint(blueprint)
    
    session['active_puzzle_rules'] = puzzle['rules']
    session['level_start_time'] = time.time()
    
    return render_template("arcade.html", puzzle=puzzle, current_level=current_level)

@app.route('/arcade/reset')
def arcade_reset():
    session.pop('arcade_level', None)
    session.pop('total_solve_time', None)
    session.pop('level_start_time', None)
    session.pop('is_bonus_level', None)
    return redirect(url_for('arcade'))

@app.route('/arcade/bonus')
def arcade_bonus():
    if not session.get('bonus_unlocked', False):
        return redirect(url_for('level_select'))
        
    puzzle = get_bonus_level_puzzle()
    session['active_puzzle_rules'] = puzzle['rules']
    session['is_bonus_level'] = True
    session['level_start_time'] = time.time()
    return render_template("arcade.html", puzzle=puzzle, current_level="Bonus")

@app.route('/select')
def level_select():
    return redirect(url_for('home'))

@app.route('/arcade/submit', methods=["POST"])
def arcade_submit():
    # 🌟 Bulletproof parsing: checks JSON, form data, or raw data fallback
    data = request.get_json(silent=True) or request.form
    if not data:
        # Fallback if sent as raw body
        import json
        try:
            data = json.loads(request.data.decode('utf-8'))
        except Exception:
            data = {}
            
    user_sequence = data.get("sequence", [])
    rules = session.get('active_puzzle_rules', {})
    
    result = validate_user_sequence(user_sequence, rules)
    
    if result.get("success"):
        if 'level_start_time' in session:
            level_duration = time.time() - session['level_start_time']
            session['total_solve_time'] = session.get('total_solve_time', 0) + level_duration
            session.pop('level_start_time', None)

        if session.get('is_bonus_level', False):
            session.pop('is_bonus_level', None)
            session.pop('arcade_level', None)
            session.pop('bonus_stage_cleared', True)
            
            if current_user.is_authenticated:
                current_user.bonus_completed = True
                db.session.commit()
                
            result["bonus_complete"] = True
            result["redirect_url"] = url_for('home')
            return jsonify(result)

        current_level = session.get('arcade_level', 1)
        
        if current_level < len(PUZZLE_POOL):
            session['arcade_level'] = current_level + 1
            result["next_level"] = session['arcade_level']
            result["campaign_complete"] = False
        else:
            total_time = session.get('total_solve_time', 0)
            if total_time <= 300:
                session['bonus_unlocked'] = True
                result["bonus_unlocked"] = True
            else:
                result["bonus_unlocked"] = False
            
            session.pop('arcade_level', None)
            result["campaign_complete"] = True
            result["redirect_url"] = url_for('level_select')
            
    return jsonify(result)

# A baseline set of common disposable email domains
DISPOSABLE_DOMAINS = {
    'mailinator.com', '10minutemail.com', 'guerrillamail.com', 
    'tempmail.com', 'trashmail.com', 'yopmail.com', 'sharklasers.com'
}

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Ensure terms agreement checkbox was checked
        if not request.form.get('terms_agreement'):
            flash('You must agree to the Terms of Service and Privacy Policy to register.', 'danger')
            return redirect(url_for('register'))

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
                
        # Block disposable and temporary email providers
        email_domain = email.split('@')[-1].lower() if '@' in email else ''
        if email_domain in DISPOSABLE_DOMAINS:
            flash('Temporary or disposable email addresses are not allowed.', 'danger')
            return redirect(url_for('register'))
        
        # Validate password strength
        password_error = validate_password_strength(password)
        if password_error:
            flash(password_error, 'danger')
            return redirect(url_for('register'))
            
        # Check if username or email is already taken
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash('Username or email already registered.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password, method='scrypt')
        
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role='free'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

def get_active_role():
    if current_user.is_authenticated:
        if current_user.role == 'admin' and 'sandbox_role' in session:
            return session['sandbox_role']
        return current_user.role
    return 'free'

@app.context_processor
def inject_active_role():
    def get_active_role():
        if current_user.is_authenticated:
            if current_user.role == 'admin' and 'sandbox_role' in session:
                return session['sandbox_role']
            return current_user.role
        return 'free'
    
    return dict(get_active_role=get_active_role)

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        email_input = request.form.get('email', '').strip()
        current_user.email = email_input if email_input else None
        current_user.default_theme = request.form.get('default_theme')
        current_user.name_tag_color = request.form.get('name_tag_color')
        
        new_password = request.form.get('new_password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
            
        db.session.commit()
        flash('Account settings updated successfully!')
        return redirect(url_for('account'))
        
    return render_template('account.html')

@app.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = get_reset_token(user)
            reset_url = url_for('reset_token', token=token, _external=True)
            
            msg = Message('Password Reset Request - CheepCards',
                          sender='noreply@cheepcards.com',
                          recipients=[user.email])
            msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, simply ignore this email.
'''
            try:
                mail.send(msg)
            except Exception:
                # Safely catches SMTP errors during local testing until Brevo is configured
                pass
                
        flash('If an account with that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

from flask_mail import Message

from flask_wtf.csrf import csrf_exempt

@app.route('/test-email')
def test_email():
    try:
        msg = Message(
            subject='CheepCards Pro Brevo Test',
            recipients=['your_personal_email@gmail.com']
        )
        msg.body = 'Success! Your local Flask app is successfully talking to Brevo SMTP.'
        mail.send(msg)
        return 'Email sent successfully! Check your inbox.'
    except Exception as e:
        return f'Email failed: {str(e)}'


@app.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    user = verify_reset_token(token)
    if not user:
        flash('That is an invalid or expired token.', 'warning')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        
        password_error = validate_password_strength(password)
        if password_error:
            flash(password_error, 'danger')
            return redirect(url_for('reset_token', token=token))
            
        user.password_hash = generate_password_hash(password, method='scrypt')
        db.session.commit()
        
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_token.html')

@app.route('/delete_deck/<int:deck_id>', methods=['POST'])
@login_required
def delete_deck(deck_id):
    deck = SavedDeck.query.get_or_404(deck_id)
    if deck.user_id == current_user.id:
        db.session.delete(deck)
        db.session.commit()
        flash('Deck deleted successfully.')
    return redirect(url_for('account'))

@app.route('/save_deck', methods=['POST'])
@login_required
def save_deck():
    active_role = get_active_role() if 'get_active_role' in globals() else current_user.role

    if active_role == 'free':
        return {'success': False, 'message': 'Free users cannot save decks. Upgrade to Pro!'}
        
    data = request.get_json()
    deck_name = data.get('name', 'My Custom Deck').strip()
    deck_cards = data.get('cards', '')
    
    if isinstance(deck_cards, list):
        deck_cards = "\n".join([f"1 {c['name']}" if isinstance(c, dict) else str(c) for c in deck_cards])

    existing_deck = SavedDeck.query.filter_by(name=deck_name, user_id=current_user.id).first()
    
    if existing_deck:
        existing_deck.card_data = deck_cards
    else:
        new_deck = SavedDeck(name=deck_name, card_data=deck_cards, user_id=current_user.id)
        db.session.add(new_deck)
        
    db.session.commit()
    return {'success': True, 'message': 'Deck saved successfully!'}

from sqlalchemy import extract, func

from datetime import datetime

@app.before_request
def check_pro_expiration():
    if current_user.is_authenticated and current_user.role == 'pro':
        if current_user.pro_expires_at and current_user.pro_expires_at < datetime.utcnow():
            current_user.role = 'free'
            db.session.commit()

from datetime import datetime, timedelta

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get("customer_details", {}).get("email")
        
        if customer_email:
            user = User.query.filter_by(email=customer_email).first()
            if user:
                now = datetime.utcnow()
                # If they already have an active expiration date in the future, stack/add 30 days to it. 
                # Otherwise, start counting 30 days from right now.
                if user.pro_expires_at and user.pro_expires_at > now:
                    user.pro_expires_at = user.pro_expires_at + timedelta(days=30)
                else:
                    user.pro_expires_at = now + timedelta(days=30)
                
                user.role = 'pro'
                db.session.commit()
                print(f"⭐ Upgraded user {customer_email} to Pro! Expires: {user.pro_expires_at}")

    return '', 200

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    now = datetime.utcnow()
    selected_year = int(request.args.get('year', now.year))
    selected_month = int(request.args.get('month', now.month))

    # Fetch users first so the list exists for counting
    user_query = request.args.get('user_q', '')
    if user_query:
        users = User.query.filter(User.username.ilike(f"%{user_query}%")).all()
        all_users = User.query.all() # Used for overall metrics if filtering search
    else:
        users = User.query.all()
        all_users = users

    admin_users = sum(1 for u in all_users if u.role == 'admin')
    pro_users = sum(1 for u in all_users if u.role == 'pro')
    free_users = sum(1 for u in all_users if u.role == 'free')
    total_users = len(all_users)

    top_cards = db.session.query(
        SearchLog.card_name, func.count(SearchLog.card_name).label('total')
    ).filter(
        extract('year', SearchLog.timestamp) == selected_year,
        extract('month', SearchLog.timestamp) == selected_month,
        SearchLog.card_name != None
    ).group_by(SearchLog.card_name).order_by(func.count(SearchLog.card_name).desc()).limit(5).all()

    top_category = db.session.query(
        SearchLog.category, func.count(SearchLog.category).label('total')
    ).filter(
        extract('year', SearchLog.timestamp) == selected_year,
        extract('month', SearchLog.timestamp) == selected_month,
        SearchLog.category != None
    ).group_by(SearchLog.category).order_by(func.count(SearchLog.category).desc()).first()

    top_rank = db.session.query(
        SearchLog.rank_searched, func.count(SearchLog.rank_searched).label('total')
    ).filter(
        extract('year', SearchLog.timestamp) == selected_year,
        extract('month', SearchLog.timestamp) == selected_month,
        SearchLog.rank_searched != None
    ).group_by(SearchLog.rank_searched).order_by(func.count(SearchLog.rank_searched).desc()).first()

    top_colors = db.session.query(
        SearchLog.colors, func.count(SearchLog.colors).label('total')
    ).filter(
        extract('year', SearchLog.timestamp) == selected_year,
        extract('month', SearchLog.timestamp) == selected_month,
        SearchLog.colors != None
    ).group_by(SearchLog.colors).order_by(func.count(SearchLog.colors).desc()).first()

    return render_template(
        'admin.html',
        users=users, 
        total_users=total_users, 
        admin_users=admin_users, 
        pro_users=pro_users, 
        free_users=free_users,
        top_cards=top_cards,
        top_category=top_category,
        top_rank=top_rank,
        top_colors=top_colors,
        selected_year=selected_year,
        selected_month=selected_month
    )

@app.route('/admin/set-role/<int:user_id>/<new_role>')
@login_required
def admin_set_role(user_id, new_role):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('home'))
        
    target_user = User.query.get_or_404(user_id)
    if new_role in ['free', 'pro', 'admin']:
        target_user.role = new_role
        db.session.commit()
        flash(f"Successfully switched {target_user.username}'s role to {new_role.upper()}!", "success")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('home'))
        
    target_user = User.query.get_or_404(user_id)
    
    if target_user.id == current_user.id:
        flash('Action blocked: You cannot delete your own active admin account!', 'error')
        return redirect(url_for('admin_dashboard'))
        
    username = target_user.username
    db.session.delete(target_user)
    db.session.commit()
    flash(f"User account '{username}' has been permanently deleted.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/quick-switch/<new_role>')
@login_required
def quick_switch_role(new_role):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('home'))
        
    if new_role in ['free', 'pro', 'admin', 'reset']:
        if new_role == 'reset':
            session.pop('sandbox_role', None)
            flash("⚡ Sandbox reset to your actual Admin account.")
        else:
            session['sandbox_role'] = new_role
            flash(f"⚡ Sandbox Active! You are now testing as: {new_role.upper()}")
            
    return redirect(url_for('account'))

# Register blueprint at the very bottom to avoid circular import issues
from news_blueprint import news_bp
app.register_blueprint(news_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 5000))

    def connect_ngrok():
        time.sleep(1.5)
        try:
            ngrok.set_auth_token("3Hm4J7DxMhKVgYGh5OeXrxjTUn3_XuwimmpHxJNfnAbiy4nU")
            forwarder = ngrok.forward(
                port, 
                basic_auth="friend:cheepcard825"
            )
            print(f"\n🌍 Your workspace is live at: {forwarder.url()}\n")
        except Exception as e:
            print(f"⚠️ Ngrok warning: {e}")

    import threading
    threading.Thread(target=connect_ngrok, daemon=True).start()

    app.run(host='0.0.0.0', port=port, debug=False)