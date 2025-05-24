from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)       # Full name field
    email = db.Column(db.String(120), unique=True, nullable=False)  # Email should be unique and required
    phone_number = db.Column(db.String(20), unique=True, nullable=True)  # Optional, but unique if provided
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # roles: admin, approver, user
    is_approved = db.Column(db.Boolean, default=False)
    def is_admin(self):
        return self.role == 'admin'

    def is_approver(self):
        return self.role == 'approver'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    
    # Optional: Add relationship for reverse lookup
    sales = db.relationship('Sale', backref='product', lazy=True)
    

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)  # <-- Add this line
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    customer_name = db.Column(db.String(100), nullable=True)
    payment_type = db.Column(db.String(50), nullable=True)  # e.g., Cash, Card, Mobile Money
    comments = db.Column(db.String(300), nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Link to User
    user = db.relationship('User', backref='sales')            # Optional: allows user.sales


