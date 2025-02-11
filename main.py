
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounting.db'
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a secure secret key
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not User.query.get(session['user_id']).is_admin:
            flash('Admin access required')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.drop_all()  # Clear all tables
    db.create_all()  # Recreate tables
    
    # Check if admin user exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='admin123', is_admin=True)
        db.session.add(admin)
    
    # Check if regular user exists
    if not User.query.filter_by(username='user').first():
        user = User(username='user', password='user123', is_admin=False)
        db.session.add(user)
    
    db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required')
            return render_template('login.html')
            
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # In production, use proper password hashing
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    try:
        page = request.args.get('page', 1, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Transaction.query
        
        if start_date and start_date.strip():
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.date >= start_datetime)
        if end_date and end_date.strip():
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Transaction.date <= end_datetime + timedelta(days=1))
        
        pagination = query.order_by(Transaction.date.desc()).paginate(page=page, per_page=10, error_out=False)
        transactions = pagination.items
        total_income = sum([t.amount for t in query.filter_by(type='income').all()])
        total_expense = sum([t.amount for t in query.filter_by(type='expense').all()])
        total = total_income - total_expense
        
        current_user = User.query.get(session['user_id'])
        return render_template('index.html', transactions=transactions, total=total,
                             total_income=total_income, total_expense=total_expense,
                             start_date=start_date, end_date=end_date,
                             pagination=pagination, current_user=current_user)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

@app.route('/add', methods=['POST'])
@admin_required
def add_transaction():
    description = request.form['description']
    amount = float(request.form['amount'])
    type = request.form['type']
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    
    transaction = Transaction(
        description=description,
        amount=amount,
        type=type,
        date=date,
        user_id=session['user_id']
    )
    db.session.add(transaction)
    db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['POST'])
@admin_required
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    transaction.description = request.form['description']
    transaction.amount = float(request.form['amount'])
    transaction.type = request.form['type']
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
@admin_required
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
