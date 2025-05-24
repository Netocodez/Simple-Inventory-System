from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from models import db, Product, Sale, Expense, User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import io

app = Flask(__name__)
app.secret_key = 'dev-secret-key-1234'  # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            return "Username already exists", 400
        password = generate_password_hash(request.form['password'])
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_sales = db.session.query(db.func.sum(Sale.total_price)).scalar() or 0
    total_expenses = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    total_stock = db.session.query(db.func.sum(Product.quantity)).scalar() or 0
    total_cogs = db.session.query(db.func.sum(Sale.cost_price * Sale.quantity)).scalar() or 0
    
    profit = total_sales - total_cogs - total_expenses

    return render_template('dashboard.html', 
                           total_sales=total_sales, 
                           total_expenses=total_expenses, 
                           total_stock=total_stock,
                           profit=profit)

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        new_expense = Expense(description=description, amount=amount)
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for('expenses'))

    expenses = Expense.query.all()
    return render_template('expenses.html', expenses=expenses)

@app.route('/expenses/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if request.method == 'POST':
        expense.description = request.form['description']
        expense.amount = float(request.form['amount'])
        db.session.commit()
        flash("Expense updated successfully", "success")
        return redirect(url_for('expenses'))

    return render_template('edit_expense.html', expense=expense)

@app.route('/expenses/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted successfully", "success")
    return redirect(url_for('expenses'))



@app.route('/products')
@login_required
def index():
    search = request.args.get('q')
    if search:
        products = Product.query.filter(Product.name.ilike(f"%{search}%")).all()
    else:
        products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        cost_price = float(request.form['cost_price'])
        price = float(request.form['price'])
        new_product = Product(name=name, quantity=quantity, cost_price=cost_price, price=price)
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_product.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.quantity = int(request.form['quantity'])
        product.price = float(request.form['price'])
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_product.html', product=product)

@app.route('/delete/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/sale', methods=['GET', 'POST'])
@login_required
def record_sale():
    products = Product.query.all()
    if request.method == 'POST':
        product_id = int(request.form['product_id'])
        quantity = int(request.form['quantity'])
        cost_price = float(request.form['cost_price'])
        unit_price = float(request.form['unit_price'])
        customer_name = request.form.get('customer_name', '').strip()
        payment_type = request.form.get('payment_type', 'Cash')
        comments = request.form.get('comments', '').strip()

        product = Product.query.get_or_404(product_id)
        if product.quantity >= quantity:
            total_price = unit_price * quantity
            sale = Sale(
                product_id=product_id, 
                quantity=quantity, 
                cost_price=cost_price, 
                unit_price=unit_price, 
                total_price=total_price,
                customer_name=customer_name or None,
                payment_type=payment_type,
                comments=comments or None
            )
            product.quantity -= quantity
            db.session.add(sale)
            db.session.commit()
            return redirect(url_for('view_receipt', sale_id=sale.id))
        else:
            return "Insufficient stock", 400
    return render_template('record_sale.html', products=products)


@app.route('/receipt/<int:sale_id>')
@login_required
def view_receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    product = Product.query.get(sale.product_id)
    return render_template('receipt.html', sale=sale, product=product)


@app.route('/sales')
@login_required
def sales_list():
    search = request.args.get('q', '').strip()
    sales_query = Sale.query.join(Product, Sale.product_id == Product.id)

    if search:
        sales_query = sales_query.filter(Product.name.ilike(f"%{search}%"))

    sales_query = sales_query.order_by(Sale.timestamp.desc())
    sales = sales_query.all()

    sales_data = []
    for s in sales:
        product = Product.query.get(s.product_id)
        sales_data.append({
            'id': s.id,  # Add this line
            'product_name': product.name if product else "Unknown Product",
            'quantity': s.quantity,
            'unit_price': s.unit_price,
            'total_price': s.total_price,
            'customer_name': s.customer_name,
            'payment_type': s.payment_type,
            'comments': s.comments,
            'timestamp': s.timestamp.strftime("%Y-%m-%d %H:%M") if s.timestamp else ''
        })

    return render_template('sales_list.html', sales=sales_data)

"""
@app.route('/receipt/<int:sale_id>')
def view_receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template('receipt.html', sale=sale)
"""

@app.route('/expense', methods=['GET', 'POST'])
@login_required
def record_expense():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        expense = Expense(description=description, amount=amount)
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('record_expense.html')

@app.route('/export/products')
@login_required
def export_products():
    products = Product.query.all()
    data = [{'Name': p.name, 'Quantity': p.quantity, 'Price': p.price} for p in products]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Products')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='products.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export/sales')
@login_required
def export_sales():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None
    except ValueError:
        start_date = end_date = None

    sales_query = Sale.query
    if start_date:
        sales_query = sales_query.filter(Sale.timestamp >= start_date)
    if end_date:
        sales_query = sales_query.filter(Sale.timestamp < end_date + timedelta(days=1))

    sales = sales_query.all()
    data = []
    for s in sales:
        product = Product.query.get(s.product_id)
        data.append({
            'id': s.id,
            'Product': product.name if product else "Unknown Product",
            'Quantity': s.quantity,
            'Cost Price': s.cost_price,
            'Unit Price': s.unit_price,
            'Total': s.total_price,
            'Custumer': s.customer_name,
            'Date': s.timestamp.strftime("%Y-%m-%d") if s.timestamp else ''
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='sales.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/export')
@login_required
def export_reports():
    # Get optional start and end date from query params
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Parse dates if provided
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None
    except ValueError:
        start_date = end_date = None  # Ignore bad format

    # Base query
    sales_query = Sale.query

    # Apply date filter if available
    if start_date:
        sales_query = sales_query.filter(Sale.timestamp >= start_date)
    if end_date:
        # To include the end_date whole day, add one day and use less than that
        sales_query = sales_query.filter(Sale.timestamp < end_date + timedelta(days=1))

    sales = sales_query.all()

    sales_data = []
    for s in sales:
        product = Product.query.get(s.product_id)
        sales_data.append({
            'id': s.id,
            'product_name': product.name if product else "Unknown Product",
            'quantity': s.quantity,
            'unit_price': s.unit_price,
            'total_price': s.total_price,
            'timestamp': s.timestamp.strftime("%Y-%m-%d") if s.timestamp else ''
        })

    return render_template('export_reports.html', sales=sales_data, start_date=start_date_str or '', end_date=end_date_str or '')

@app.route('/restock', methods=['GET', 'POST'])
@login_required
def restock_product():
    products = Product.query.all()
    if request.method == 'POST':
        product_id = int(request.form['product_id'])
        additional_quantity = int(request.form['quantity'])
        new_price = float(request.form['price'])

        product = Product.query.get_or_404(product_id)
        product.quantity += additional_quantity
        product.price = new_price  # update price to new value
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('restock_product.html', products=products)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
