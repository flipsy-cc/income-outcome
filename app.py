# pylint: disable=unused-import
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Datenbankmodell: Transaktion
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(200))

# Datenbankmodell: Kategorie
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)

# Datenbank initialisieren
with app.app_context():
    db.create_all()

# Startseite
@app.route('/')
def index():
    income = sum(t.amount for t in Transaction.query.filter_by(type='income'))
    expenses = sum(t.amount for t in Transaction.query.filter_by(type='expense'))
    balance = income - expenses

    expense_categories = Category.query.filter_by(type='expense').all()
    expense_data = [
        sum(t.amount for t in Transaction.query.filter_by(type='expense', category=cat.name))
        for cat in expense_categories
    ]

    sankey_data = generate_sankey_data()

    return render_template(
        'index.html',
        income=income,
        expenses=expenses,
        balance=balance,
        expense_categories=expense_categories,
        expense_data=expense_data,
        sankey_data=json.dumps(sankey_data),
        datetime=datetime  # Übergabe an das Template
    )

# Sankey-Diagramm generieren
def generate_sankey_data():
    nodes = [{"name": "Income"}, {"name": "Expenses"}]
    links = []

    # Einnahmen-Kategorien
    income_cats = db.session.query(Transaction.category, db.func.sum(Transaction.amount))\
                   .filter_by(type='income').group_by(Transaction.category)
    for cat, amount in income_cats:
        nodes.append({"name": cat})
        links.append({"source": 0, "target": len(nodes) - 1, "value": float(amount)})

    # Ausgaben-Kategorien
    expense_cats = db.session.query(Transaction.category, db.func.sum(Transaction.amount))\
                    .filter_by(type='expense').group_by(Transaction.category)
    for cat, amount in expense_cats:
        nodes.append({"name": cat})
        links.append({"source": len(nodes) - 1, "target": 1, "value": float(amount)})

    return {"nodes": nodes, "links": links}

# Transaktion hinzufügen
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    try:
        amount = float(request.form.get('amount', 0))
        trans_type = request.form.get('type')
        category = request.form.get('category')
        description = request.form.get('description', '')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')

        if amount <= 0:
            raise ValueError("Amount must be positive")

        transaction = Transaction(
            amount=amount,
            type=trans_type,
            category=category,
            description=description,
            date=date
        )
        db.session.add(transaction)
        db.session.commit()
        return redirect(url_for('index'))

    except Exception as e:
        print(f"Error adding transaction: {e}")
        return redirect(url_for('index'))

# Starten der App
if __name__ == '__main__':
    with app.app_context():
        if not Category.query.first():
            categories = [
                Category(name='Salary', type='income'),
                Category(name='Freelance', type='income'),
                Category(name='Rent', type='expense'),
                Category(name='Groceries', type='expense'),
                Category(name='Utilities', type='expense')
            ]
            db.session.bulk_save_objects(categories)
            db.session.commit()
    app.run(debug=True)
