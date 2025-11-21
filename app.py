from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
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
    role = db.Column(db.String(20), default='HELPER')  # ADMIN, FARMER, HELPER
    barn_id = db.Column(db.Integer, db.ForeignKey('barn.id'), nullable=True)
    barn = db.relationship('Barn', backref='users')


class Barn(db.Model):
    """Barn model - separate barns on the farm"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(200))
    capacity = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sections = db.relationship('Section', backref='barn', lazy=True, cascade='all, delete-orphan')
    pigs = db.relationship('Pig', backref='barn', lazy=True, cascade='all, delete-orphan')


class Section(db.Model):
    """Section model - sections within barns"""
    id = db.Column(db.Integer, primary_key=True)
    barn_id = db.Column(db.Integer, db.ForeignKey('barn.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer)
    pigs = db.relationship('Pig', backref='section', lazy=True)
    
    __table_args__ = (db.UniqueConstraint('barn_id', 'name', name='_barn_section_uc'),)


class Pig(db.Model):
    """Pig model - main table for pig information"""
    id = db.Column(db.String(50), primary_key=True)
    barn_id = db.Column(db.Integer, db.ForeignKey('barn.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=True)
    dob = db.Column(db.Date, nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    breed = db.Column(db.String(50), nullable=False)
    kill_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='ALIVE')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
        if not user or user.role != 'ADMIN':
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def farmer_or_admin_required(f):
    """Decorator to require farmer or admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role not in ['ADMIN', 'FARMER']:
            flash('Farmer or Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def check_barn_access(barn_id):
    """Check if user can access a barn"""
    user = User.query.get(session.get('user_id'))
    if user.role == 'ADMIN':
        return True
    if user.role in ['FARMER', 'HELPER'] and user.barn_id == barn_id:
        return True
    return False


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
            session['role'] = user.role
            session['barn_id'] = user.barn_id
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
    user = User.query.get(session['user_id'])
    
    if user.role == 'ADMIN':
        pigs = Pig.query.all()
        barns = Barn.query.all()
    else:  # FARMER or HELPER
        pigs = Pig.query.filter_by(barn_id=user.barn_id).all()
        barns = Barn.query.filter_by(id=user.barn_id).all()
    
    alive_count = sum(1 for p in pigs if p.status == 'ALIVE')
    slaughtered_count = sum(1 for p in pigs if p.status == 'SLAUGHTERED')
    
    return render_template('dashboard.html', 
                         pigs=pigs, 
                         alive_count=alive_count, 
                         slaughtered_count=slaughtered_count,
                         barns=barns,
                         user_role=user.role)


# ============================================
# BARN MANAGEMENT ROUTES
# ============================================

@app.route('/barns')
@admin_required
def manage_barns():
    """Admin only - manage barns"""
    barns = Barn.query.all()
    return render_template('manage_barns.html', barns=barns)


@app.route('/barn/add', methods=['GET', 'POST'])
@admin_required
def add_barn():
    """Add a new barn"""
    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location')
        capacity = request.form.get('capacity')
        
        if Barn.query.filter_by(name=name).first():
            flash('Barn name already exists!', 'danger')
            return redirect(url_for('add_barn'))
        
        new_barn = Barn(
            name=name,
            location=location,
            capacity=int(capacity) if capacity else None
        )
        
        db.session.add(new_barn)
        db.session.commit()
        
        flash(f'Barn {name} added successfully!', 'success')
        return redirect(url_for('manage_barns'))
    
    return render_template('add_barn.html')


@app.route('/barn/<int:barn_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_barn(barn_id):
    """Edit barn details"""
    barn = Barn.query.get_or_404(barn_id)
    
    if request.method == 'POST':
        barn.name = request.form.get('name')
        barn.location = request.form.get('location')
        barn.capacity = int(request.form.get('capacity')) if request.form.get('capacity') else None
        
        db.session.commit()
        flash(f'Barn {barn.name} updated successfully!', 'success')
        return redirect(url_for('manage_barns'))
    
    return render_template('edit_barn.html', barn=barn)


@app.route('/barn/<int:barn_id>/delete', methods=['POST'])
@admin_required
def delete_barn(barn_id):
    """Delete barn"""
    barn = Barn.query.get_or_404(barn_id)
    barn_name = barn.name
    
    db.session.delete(barn)
    db.session.commit()
    
    flash(f'Barn {barn_name} deleted successfully!', 'success')
    return redirect(url_for('manage_barns'))


# ============================================
# SECTION MANAGEMENT ROUTES
# ============================================

@app.route('/barn/<int:barn_id>/sections')
@login_required
def manage_sections(barn_id):
    """Manage sections in a barn"""
    if not check_barn_access(barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    barn = Barn.query.get_or_404(barn_id)
    return render_template('manage_sections.html', barn=barn)


@app.route('/section/add', methods=['POST'])
@farmer_or_admin_required
def add_section():
    """Add a new section to a barn"""
    barn_id = request.form.get('barn_id')
    
    if not check_barn_access(int(barn_id)):
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.form.get('name')
    capacity = request.form.get('capacity')
    
    if Section.query.filter_by(barn_id=barn_id, name=name).first():
        flash('Section name already exists in this barn!', 'danger')
        return redirect(url_for('manage_sections', barn_id=barn_id))
    
    new_section = Section(
        barn_id=int(barn_id),
        name=name,
        capacity=int(capacity) if capacity else None
    )
    
    db.session.add(new_section)
    db.session.commit()
    
    flash(f'Section {name} added successfully!', 'success')
    return redirect(url_for('manage_sections', barn_id=barn_id))


@app.route('/section/<int:section_id>/edit', methods=['GET', 'POST'])
@farmer_or_admin_required
def edit_section(section_id):
    """Edit section details"""
    section = Section.query.get_or_404(section_id)
    
    if not check_barn_access(section.barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        section.name = request.form.get('name')
        section.capacity = int(request.form.get('capacity')) if request.form.get('capacity') else None
        
        db.session.commit()
        flash(f'Section {section.name} updated successfully!', 'success')
        return redirect(url_for('manage_sections', barn_id=section.barn_id))
    
    return render_template('edit_section.html', section=section)


@app.route('/section/<int:section_id>/delete', methods=['POST'])
@farmer_or_admin_required
def delete_section(section_id):
    """Delete section"""
    section = Section.query.get_or_404(section_id)
    barn_id = section.barn_id
    
    if not check_barn_access(barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    section_name = section.name
    db.session.delete(section)
    db.session.commit()
    
    flash(f'Section {section_name} deleted successfully!', 'success')
    return redirect(url_for('manage_sections', barn_id=barn_id))


# ============================================
# PIG MANAGEMENT ROUTES
# ============================================

@app.route('/pig/add', methods=['GET', 'POST'])
@farmer_or_admin_required
def add_pig():
    """Add a new pig"""
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        pig_id = request.form.get('pig_id')
        barn_id = int(request.form.get('barn_id'))
        section_id = request.form.get('section_id')
        dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date()
        sex = request.form.get('sex')
        breed = request.form.get('breed')
        notes = request.form.get('notes', '')
        
        if not check_barn_access(barn_id):
            flash('Access denied', 'danger')
            return redirect(url_for('dashboard'))
        
        if Pig.query.get(pig_id):
            flash('Pig ID already exists! Please use a different ID.', 'danger')
            return redirect(url_for('add_pig'))
        
        new_pig = Pig(
            id=pig_id,
            barn_id=barn_id,
            section_id=int(section_id) if section_id else None,
            dob=dob,
            sex=sex,
            breed=breed,
            notes=notes,
            status='ALIVE'
        )
        
        db.session.add(new_pig)
        db.session.commit()
        
        flash(f'Pig {pig_id} added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    if user.role == 'ADMIN':
        barns = Barn.query.all()
    else:
        barns = Barn.query.filter_by(id=user.barn_id).all()
    
    return render_template('add_pig.html', barns=barns)


@app.route('/pig/<pig_id>')
@login_required
def pig_detail(pig_id):
    """View pig details and weight history"""
    pig = Pig.query.get_or_404(pig_id)
    
    if not check_barn_access(pig.barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get(session['user_id'])
    weights_db = Weight.query.filter_by(pig_id=pig_id).order_by(Weight.date.asc()).all()
    
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
            pct = (diff / previous_weight) * 100 if previous_weight > 0 else 0
            weight_history.append({
                "date": w.date,
                "weight": w.weight,
                "diff": diff,
                "pct": pct
            })
        previous_weight = w.weight
    
    weight_history.reverse()
    
    chart_data = None
    if weights_db:
        dates = [w.date.strftime('%Y-%m-%d') for w in weights_db]
        weight_values = [w.weight for w in weights_db]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(range(len(dates)), weight_values, width=0.7, color='#667eea', edgecolor='#764ba2', linewidth=2, alpha=0.8)
        
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, rotation=45, ha='right')
        
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Weight (kg)', fontsize=12, fontweight='bold')
        ax.set_title(f'Weight Progress for Pig {pig_id}', fontsize=14, fontweight='bold', pad=20)
        
        ax.grid(True, alpha=0.2, axis='y', linestyle='--')
        ax.set_axisbelow(True)
        
        for bar, weight in zip(bars, weight_values):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                    f'{weight}kg', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#2d3748')
        
        ax.set_ylim(0, max(weight_values) * 1.1)
        
        plt.tight_layout()
        
        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=100, bbox_inches='tight')
        img.seek(0)
        chart_data = base64.b64encode(img.getvalue()).decode()
        plt.close(fig)
    
    return render_template('pig_detail.html', pig=pig, weights=weight_history, chart_data=chart_data, user_role=user.role)


@app.route('/pig/<pig_id>/edit', methods=['GET', 'POST'])
@farmer_or_admin_required
def edit_pig(pig_id):
    """Edit pig details"""
    pig = Pig.query.get_or_404(pig_id)
    
    if not check_barn_access(pig.barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        pig.sex = request.form.get('sex')
        pig.breed = request.form.get('breed')
        pig.notes = request.form.get('notes', '')
        
        section_id = request.form.get('section_id')
        if section_id:
            pig.section_id = int(section_id)
        
        db.session.commit()
        flash(f'Pig {pig_id} updated successfully!', 'success')
        return redirect(url_for('pig_detail', pig_id=pig_id))
    
    sections = Section.query.filter_by(barn_id=pig.barn_id).all()
    return render_template('edit_pig.html', pig=pig, sections=sections)


@app.route('/pig/<pig_id>/delete', methods=['POST'])
@farmer_or_admin_required
def delete_pig(pig_id):
    """Delete a pig"""
    pig = Pig.query.get_or_404(pig_id)
    
    if not check_barn_access(pig.barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(pig)
    db.session.commit()
    
    flash(f'Pig {pig_id} deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/pig/<pig_id>/weigh', methods=['POST'])
@farmer_or_admin_required
def weigh_pig(pig_id):
    """Add weight record for a pig"""
    pig = Pig.query.get_or_404(pig_id)
    
    if not check_barn_access(pig.barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
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
@farmer_or_admin_required
def slaughter_pig(pig_id):
    """Mark pig as slaughtered"""
    pig = Pig.query.get_or_404(pig_id)
    
    if not check_barn_access(pig.barn_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    kill_date = datetime.strptime(request.form.get('kill_date'), '%Y-%m-%d').date()
    
    pig.status = 'SLAUGHTERED'
    pig.kill_date = kill_date
    
    db.session.commit()
    
    flash(f'Pig {pig_id} marked as slaughtered on {kill_date}', 'info')
    return redirect(url_for('pig_detail', pig_id=pig_id))


# ============================================
# PLOTTING ROUTES
# ============================================

@app.route('/charts/weight-comparison', methods=['GET', 'POST'])
@login_required
def weight_comparison():
    """Compare weight progress across multiple pigs"""
    user = User.query.get(session['user_id'])
    chart_data = None
    
    if user.role == 'ADMIN':
        pigs = Pig.query.all()
    else:
        pigs = Pig.query.filter_by(barn_id=user.barn_id).all()
    
    if request.method == 'POST':
        selected_pig_ids = request.form.getlist('pig_ids')
        chart_type = request.form.get('chart_type', 'line')
        
        if selected_pig_ids:
            fig, ax = plt.subplots(figsize=(12, 7))
            
            for pig_id in selected_pig_ids:
                weights_db = Weight.query.filter_by(pig_id=pig_id).order_by(Weight.date.asc()).all()
                if weights_db:
                    dates = [w.date.strftime('%Y-%m-%d') for w in weights_db]
                    weight_values = [w.weight for w in weights_db]
                    
                    if chart_type == 'line':
                        ax.plot(dates, weight_values, marker='o', label=f'Pig {pig_id}', linewidth=2)
                    elif chart_type == 'bar':
                        x_pos = range(len(dates))
                        ax.bar([x + len(selected_pig_ids)*0.1 for x in x_pos], weight_values, label=f'Pig {pig_id}', alpha=0.7, width=0.2)
            
            ax.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax.set_ylabel('Weight (kg)', fontsize=12, fontweight='bold')
            ax.set_title('Weight Comparison Across Pigs', fontsize=14, fontweight='bold', pad=20)
            ax.legend()
            ax.grid(True, alpha=0.2, linestyle='--')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            img = io.BytesIO()
            plt.savefig(img, format='png', dpi=100, bbox_inches='tight')
            img.seek(0)
            chart_data = base64.b64encode(img.getvalue()).decode()
            plt.close(fig)
    
    return render_template('weight_comparison.html', pigs=pigs, chart_data=chart_data)


@app.route('/charts/barn-statistics')
@login_required
def barn_statistics():
    """View statistics for barn(s)"""
    user = User.query.get(session['user_id'])
    
    if user.role == 'ADMIN':
        barns = Barn.query.all()
    else:
        barns = Barn.query.filter_by(id=user.barn_id).all()
    
    stats = []
    for barn in barns:
        pigs = Pig.query.filter_by(barn_id=barn.id).all()
        alive = sum(1 for p in pigs if p.status == 'ALIVE')
        slaughtered = sum(1 for p in pigs if p.status == 'SLAUGHTERED')
        
        avg_weight = None
        if pigs:
            latest_weights = []
            for pig in pigs:
                latest = Weight.query.filter_by(pig_id=pig.id).order_by(Weight.date.desc()).first()
                if latest:
                    latest_weights.append(latest.weight)
            if latest_weights:
                avg_weight = sum(latest_weights) / len(latest_weights)
        
        stats.append({
            'barn': barn,
            'total_pigs': len(pigs),
            'alive': alive,
            'slaughtered': slaughtered,
            'avg_weight': avg_weight
        })
    
    return render_template('barn_statistics.html', stats=stats)


# ============================================
# EXPORT ROUTES
# ============================================

@app.route('/export/csv')
@login_required
def export_csv():
    """Export all pig data with complete weight history to CSV"""
    user = User.query.get(session['user_id'])
    
    if user.role == 'ADMIN':
        pigs = Pig.query.all()
    else:
        pigs = Pig.query.filter_by(barn_id=user.barn_id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Pig ID', 'Barn', 'Section', 'DOB', 'Sex', 'Breed', 'Status', 'Kill Date', 
                     'Weight (kg)', 'Weight Date', 'Weight Change (kg)', 'Weight Change (%)'])
    
    for pig in pigs:
        weights = Weight.query.filter_by(pig_id=pig.id).order_by(Weight.date.asc()).all()
        
        barn_name = pig.barn.name if pig.barn else ''
        section_name = pig.section.name if pig.section else ''
        
        if not weights:
            writer.writerow([
                pig.id,
                barn_name,
                section_name,
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
                    barn_name,
                    section_name,
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
    barns = Barn.query.all()
    return render_template('manage_users.html', users=users, barns=barns)


@app.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    """Admin only - add new user"""
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'HELPER')
    barn_id = request.form.get('barn_id')
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists!', 'danger')
        return redirect(url_for('manage_users'))
    
    new_user = User(
        username=username,
        password=generate_password_hash(password),
        role=role,
        barn_id=int(barn_id) if barn_id else None
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
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} deleted successfully!', 'success')
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
                role='ADMIN'
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