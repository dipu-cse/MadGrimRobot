
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounting.db'
db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Transaction.query
    
    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1))
    
    transactions = query.order_by(Transaction.date.desc()).all()
    total_income = sum([t.amount for t in transactions if t.type == 'income'])
    total_expense = sum([t.amount for t in transactions if t.type == 'expense'])
    total = total_income - total_expense
    
    return render_template('index.html', transactions=transactions, total=total,
                         total_income=total_income, total_expense=total_expense,
                         start_date=start_date, end_date=end_date)

@app.route('/add', methods=['POST'])
def add_transaction():
    description = request.form['description']
    amount = float(request.form['amount'])
    type = request.form['type']
    
    transaction = Transaction(description=description, amount=amount, type=type)
    db.session.add(transaction)
    db.session.commit()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
