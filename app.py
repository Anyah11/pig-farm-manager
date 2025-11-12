from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import csv
import base64
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import io
import os
from dotenv import load_dotenv


# --- PATCH HERE ---
from matplotlib.path import Path

def patched_deepcopy(self, memo):
    return Path(self.vertices.copy(), self.codes.copy() if self.codes is not None else None)

Path.__deepcopy__ = patched_deepcopy
# --- PATCH END ---

# Load environment variables
load_dotenv()

# Initialize Flask app and configurations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///pigfarm.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)


# ============================================
# DATABASE MODELS
# ============================================

class User(db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Pig(db.Model):
    """Pig model - main table for pig information"""
    id = db.Column(db.String(50), primary_key=True)  # Manual Pig ID
    dob = db.Column(db.Date, nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    breed = db.Column(db.String(50), nullable=False)
    kill_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='ALIVE')
    weights = db.relationship('Weight', backref='pig', lazy=True, cascade='all, delete-orphan')


class Weight(db.Model):
    """Weight model - tracks pig weights over time"""
    id = db.Column(db.Integer, primary_key=True)
    pig_id = db.Column(db.String(50), db.ForeignKey('pig.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)


# ============================================
# AUTHENTICATION DECORATORS
# ============================================

def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    """Home page - redirects to dashboard or login"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing all pigs"""
    pigs = Pig.query.all()
    alive_count = Pig.query.filter_by(status='ALIVE').count()
    slaughtered_count = Pig.query.filter_by(status='SLAUGHTERED').count()
    
    return render_template('dashboard.html', 
                         pigs=pigs, 
                         alive_count=alive_count, 
                         slaughtered_count=slaughtered_count)


@app.route('/pig/add', methods=['GET', 'POST'])
@login_required
def add_pig():
    """Add a new pig"""
    if request.method == 'POST':
        pig_id = request.form.get('pig_id')
        dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date()
        sex = request.form.get('sex')
        breed = request.form.get('breed')
        
        # Check if pig ID already exists
        if Pig.query.get(pig_id):
            flash('Pig ID already exists! Please use a different ID.', 'danger')
            return redirect(url_for('add_pig'))
        
        # Create new pig
        new_pig = Pig(
            id=pig_id,
            dob=dob,
            sex=sex,
            breed=breed,
            status='ALIVE'
        )
        
        db.session.add(new_pig)
        db.session.commit()
        
        flash(f'Pig {pig_id} added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_pig.html')

@app.route('/pig/<pig_id>')
@login_required
def pig_detail(pig_id):
    """View pig details and weight history"""
    pig = Pig.query.get_or_404(pig_id)

    # Fetch all weights for this pig, oldest first
    weights_db = Weight.query.filter_by(pig_id=pig_id).order_by(Weight.date.asc()).all()

    # Prepare weight history with diff and percent change
    previous_weight = None
    weight_history = []

    for w in weights_db:
        if previous_weight is None:
            weight_history.append({
                "date": w.date,
                "weight": w.weight,
                "diff": None,
                "pct": None
            })
        else:
            diff = w.weight - previous_weight
            # Prevent division by zero
            if previous_weight > 0:
                pct = (diff / previous_weight) * 100
            else:
                pct = 0  # or None, or 'N/A' depending on what you want
            weight_history.append({
                "date": w.date,
                "weight": w.weight,
                "diff": diff,
                "pct": pct
            })
        previous_weight = w.weight

    # Reverse to have latest weight first in template
    weight_history.reverse()

    # Prepare chart data
    chart_data = None
    if weights_db:
        dates = [w.date.strftime('%Y-%m-%d') for w in weights_db]
        weight_values = [w.weight for w in weights_db]

        fig, ax = plt.subplots(figsize=(10, 6))

        # Bars
        bars = ax.bar(range(len(dates)), weight_values, width=0.7, color='#667eea', edgecolor='#764ba2', linewidth=2, alpha=0.8)

        # X-axis labels
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, rotation=45, ha='right')

        # Labels and title
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Weight (kg)', fontsize=12, fontweight='bold')
        ax.set_title(f'Weight Progress for Pig {pig_id}', fontsize=14, fontweight='bold', pad=20)

        # Grid
        ax.grid(True, alpha=0.2, axis='y', linestyle='--')
        ax.set_axisbelow(True)

        # Add values on bars
        for bar, weight in zip(bars, weight_values):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                    f'{weight}kg', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#2d3748')

        # Adjust y-axis
        ax.set_ylim(0, max(weight_values) * 1.1)

        plt.tight_layout()

        # Save figure to base64
        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=100, bbox_inches='tight')
        img.seek(0)
        chart_data = base64.b64encode(img.getvalue()).decode()
        plt.close(fig)

    return render_template('pig_detail.html', pig=pig, weights=weight_history, chart_data=chart_data)

@app.route('/pig/<pig_id>/weigh', methods=['POST'])
@login_required
def weigh_pig(pig_id):
    """Add weight record for a pig"""
    pig = Pig.query.get_or_404(pig_id)
    
    weight = float(request.form.get('weight'))
    date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
    
    new_weight = Weight(
        pig_id=pig_id,
        weight=weight,
        date=date
    )
    
    db.session.add(new_weight)
    db.session.commit()
    
    flash(f'Weight recorded: {weight}kg on {date}', 'success')
    return redirect(url_for('pig_detail', pig_id=pig_id))


@app.route('/pig/<pig_id>/slaughter', methods=['POST'])
@login_required
def slaughter_pig(pig_id):
    """Mark pig as slaughtered"""
    pig = Pig.query.get_or_404(pig_id)
    
    kill_date = datetime.strptime(request.form.get('kill_date'), '%Y-%m-%d').date()
    
    pig.status = 'SLAUGHTERED'
    pig.kill_date = kill_date
    
    db.session.commit()
    
    flash(f'Pig {pig_id} marked as slaughtered on {kill_date}', 'info')
    return redirect(url_for('pig_detail', pig_id=pig_id)
    )


@app.route('/export/csv')
@login_required
def export_csv():
    """Export all pig data with complete weight history to CSV"""
    pigs = Pig.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Pig ID', 'DOB', 'Sex', 'Breed', 'Status', 'Kill Date', 
                     'Weight (kg)', 'Weight Date', 'Weight Change (kg)', 'Weight Change (%)'])
    
    for pig in pigs:
        weights = Weight.query.filter_by(pig_id=pig.id).order_by(Weight.date.asc()).all()
        
        if not weights:
            # Pig with no weights
            writer.writerow([
                pig.id,
                pig.dob.strftime('%Y-%m-%d'),
                pig.sex,
                pig.breed,
                pig.status,
                pig.kill_date.strftime('%Y-%m-%d') if pig.kill_date else '',
                'No weights recorded',
                '',
                '',
                ''
            ])
        else:
            previous_weight = None
            for w in weights:
                diff = ''
                pct = ''
                if previous_weight is not None and previous_weight > 0:
                    diff = round(w.weight - previous_weight, 2)
                    pct = round((diff / previous_weight) * 100, 2)
                
                writer.writerow([
                    pig.id,
                    pig.dob.strftime('%Y-%m-%d'),
                    pig.sex,
                    pig.breed,
                    pig.status,
                    pig.kill_date.strftime('%Y-%m-%d') if pig.kill_date else '',
                    w.weight,
                    w.date.strftime('%Y-%m-%d'),
                    diff,
                    pct
                ])
                previous_weight = w.weight
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'pig_farm_complete_data_{datetime.now().strftime("%Y%m%d")}.csv'
    )



# ============================================
# USER MANAGEMENT ROUTES (ADMIN ONLY)
# ============================================

@app.route('/users')
@admin_required
def manage_users():
    """Admin only - manage users"""
    users = User.query.all()
    return render_template('manage_users.html', users=users)


@app.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    """Admin only - add new user"""
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists!', 'danger')
        return redirect(url_for('manage_users'))
    
    new_user = User(
        username=username,
        password=generate_password_hash(password),
        is_admin=is_admin
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    flash(f'User {username} created successfully!', 'success')
    return redirect(url_for('manage_users'))


@app.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Admin only - delete user"""
    if user_id == session['user_id']:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('manage_users'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.username} deleted successfully!', 'success')
    return redirect(url_for('manage_users'))


# ============================================
# DATABASE INITIALIZATION
# ============================================

def init_db():
    """Initialize database and create default admin user"""
    with app.app_context():
        db.create_all()
        
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        if not User.query.filter_by(username=admin_username).first():
            admin = User(
                username=admin_username,
                password=generate_password_hash(admin_password),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Database created!")
            print("✅ Default admin user created:")
            print(f"   Username: {admin_username}")
            print(f"   Password: {admin_password}")
            print("   ⚠️  CHANGE THE PASSWORD IMMEDIATELY!")
        else:
            print("✅ Database already exists")

# ============================================
# RUN APPLICATION
# ============================================

if __name__ == '__main__':
    init_db()
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode)