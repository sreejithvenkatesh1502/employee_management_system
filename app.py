from multiprocessing.util import debug

from flask import Flask, redirect, render_template_string, request
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)


class cursor:
    """Small, context-managed wrapper around a MySQL database cursor."""

    def __init__(self, connection=None, **kwargs):
        self.connection = connection or get_db_connection()
        self._owns_connection = connection is None
        self._cursor = self.connection.cursor(**kwargs)

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def execute(self, operation, params=None):
        if params is None:
            return self._cursor.execute(operation)
        return self._cursor.execute(operation, params)

    def executemany(self, operation, seq_params):
        return self._cursor.executemany(operation, seq_params)

    def callproc(self, procname, params=None):
        if params is None:
            return self._cursor.callproc(procname)
        return self._cursor.callproc(procname, params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchmany(self, size=None):
        if size is None:
            return self._cursor.fetchmany()
        return self._cursor.fetchmany(size)

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self._cursor.close()
        if self._owns_connection:
            self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __iter__(self):
        return iter(self._cursor)

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


def get_db_connection():
    required_settings = ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")
    missing_settings = [name for name in required_settings if not os.getenv(name)]
    if missing_settings:
        raise RuntimeError(
            "Missing required database settings: " + ", ".join(missing_settings)
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=10,
    )


class employees:
    """Database operations for employee records."""

    def get_all(self):
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("""
                SELECT e.employee_id, e.first_name, e.last_name, e.email,
                       e.phone, e.dob, e.hire_date, e.salary,
                       d.department_name
                FROM employees e
                JOIN departments d ON e.department_id = d.department_id
                ORDER BY e.employee_id
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            db.close()

    def get_by_id(self, employee_id):
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM employees WHERE employee_id=%s",
                (employee_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            db.close()

    def search(self, keyword):
        db = get_db_connection()
        cursor = db.cursor()
        try:
            search_term = f"%{keyword}%"

            if keyword.isdigit():
                cursor.execute("""
                    SELECT e.employee_id, e.first_name, e.last_name,
                           e.email, e.phone, e.dob, e.hire_date,
                           e.salary, d.department_name
                    FROM employees e
                    JOIN departments d
                    ON e.department_id = d.department_id
                    WHERE e.employee_id = %s
                    ORDER BY e.employee_id
                """, (int(keyword),))
            else:
                cursor.execute("""
                    SELECT e.employee_id, e.first_name, e.last_name,
                           e.email, e.phone, e.dob, e.hire_date,
                           e.salary, d.department_name
                    FROM employees e
                    JOIN departments d
                    ON e.department_id = d.department_id
                    WHERE e.first_name LIKE %s
                       OR e.last_name LIKE %s
                       OR e.email LIKE %s
                       OR e.phone LIKE %s
                    ORDER BY e.employee_id
                """, (search_term, search_term, search_term, search_term))

            return cursor.fetchall()
        finally:
            cursor.close()
            db.close()

    def add(self, employee_id, first_name, last_name, email, phone, dob, hire_date,
            salary, department_id):
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO employees
                (employee_id, first_name, last_name, email, phone, dob, hire_date,
                 salary, department_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (employee_id, first_name, last_name, email, phone, dob, hire_date,
                  salary, department_id))
            db.commit()
            return cursor.lastrowid
        except Exception:
            db.rollback()
            raise
        finally:
            cursor.close()
            db.close()

    def update(self, employee_id, new_employee_id, first_name, last_name, email, phone, dob,
               hire_date, salary, department_id):
        db = get_db_connection()
        cursor = db.cursor()
        cursor = db.cursor()
        try:
            cursor.execute("""
                UPDATE employees
               SET employee_id=%s, first_name=%s, last_name=%s, email=%s, phone=%s,
dob=%s, hire_date=%s, salary=%s, department_id=%s
WHERE employee_id=%s 
            """, (new_employee_id,first_name, last_name, email, phone, dob, hire_date,
                  salary, department_id, employee_id))
            db.commit()
            return cursor.rowcount
        except Exception:
            db.rollback()
            raise
        finally:
            cursor.close()
            db.close()

    def delete(self, employee_id):
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute(
                "DELETE FROM employees WHERE employee_id=%s",
                (employee_id,),
            )
            db.commit()
            return cursor.rowcount
        except Exception:
            db.rollback()
            raise
        finally:
            cursor.close()
            db.close()

    def count(self):
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM employees")
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            db.close()

    def average_salary(self):
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT AVG(salary) FROM employees")
            return cursor.fetchone()[0] or 0
        finally:
            cursor.close()
            db.close()

    def department_stats(self):
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("""
                SELECT d.department_name, COUNT(e.employee_id)
                FROM departments d
                LEFT JOIN employees e ON d.department_id = e.department_id
                GROUP BY d.department_id, d.department_name
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            db.close()

    def get_employees(self):
        return self.get_all()

    def create_employee(self, *args):
        return self.add(*args)

    def update_employee(self, *args):
        return self.update(*args)

    def delete_employee(self, employee_id):
        return self.delete(employee_id)


Employees = employees


employee_store = employees()


@app.route("/search", methods=["GET", "POST"])
def search_employee():
    keyword = request.args.get("keyword", "").strip()

    if keyword:
        results = employee_store.search(keyword)
    else:
        results = []

    return render_template_string("""
        <h2>Search Employees</h2>
        <form method="GET">
            <input type="text" name="keyword"
                   placeholder="Enter employee name or email">
            <button type="submit">Search</button>
        </form>
{% if results %}
<table border="1" cellpadding="10" cellspacing="0">
    <tr>
        <th>Employee ID</th>
        <th>First Name</th>
        <th>Last Name</th>
        <th>Email</th>
        <th>Phone</th>
        <th>DOB</th>
        <th>Joining Date</th>
        <th>Salary</th>
        <th>Department</th>
    </tr>

    {% for emp in results %}
    <tr>
        {% for value in emp %}
        <td>{{ value }}</td>
        {% endfor %}
    </tr>
    {% endfor %}
</table>
{% else %}
<p>No employees found.</p>
{% endif %}
        

        <a href="/">Back to Dashboard</a>
    """, results=results)
@app.route("/")
def home():
    try:
        employee_rows = employee_store.get_all()
        department_data = employee_store.department_stats()
        avg_salary = employee_store.average_salary()
        total_employees = len(employee_rows)

        return render_template_string("""
        <html>
        <head>
            <title>Employee Management System</title>
            <style>
            body {
    font-family: Arial, sans-serif;
    background: #f1f5f9;
    margin: 0;
    padding: 30px;
    color: #1e293b;
}

h1 {
    color: #1e3a5f;
    font-size: 30px;
    margin-bottom: 25px;
}

h2, h3 {
    color: #334155;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
}

th, td {
    padding: 14px;
    border-bottom: 1px solid #e2e8f0;
    text-align: left;
}

th {
    background: #1e3a5f;
    color: white;
    font-weight: bold;
}

tr:hover {
    background: #eff6ff;
}

a {
    color: #2563eb;
    text-decoration: none;
    font-weight: bold;
}

a:hover {
    text-decoration: underline;
}

button {
    background: #2563eb;
    color: white;
    border: none;
    padding: 10px 18px;
    border-radius: 6px;
    cursor: pointer;
}

button:hover {
    background: #1d4ed8;
}
            </style>
            
                   
        </head>
        <body>
            <h1>Employee Management System</h1>
            <h3>Total Employees: {{ employees|length }}</h3>
<div style="margin:20px 0;">
    <a href="/search">Search Employee</a>
    &nbsp;&nbsp;
    <a href="/add_employee">Add Employee</a>
</div>
            <table>
            <div style="display:flex; gap:20px; margin:20px 0;">
    <div style="background:white; padding:20px; flex:1;">
        <h3>Total Employees</h3>
        <h2>{{ total_employees }}</h2>
    </div>

    <div style="background:white; padding:20px; flex:1;">
        <h3>Average Salary</h3>
        <h2>₹ {{ "%.2f"|format(avg_salary) }}</h2>
    </div>

    <div style="background:white; padding:20px; flex:1;">
        <h3>Total Departments</h3>
        <h2>{{ department_data|length }}</h2>
    </div>
</div>
<div style="margin: 20px 0;">
    <a href="/add_employee">
        <button type="button">+ Add Employee</button>
    </a>
</div>

<h2>Department Employee Chart</h2>
<canvas id="departmentChart"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
const departmentLabels = {{ department_data | map(attribute=0) | list | tojson }};
const departmentCounts = {{ department_data | map(attribute=1) | list | tojson }};

new Chart(document.getElementById('departmentChart'), {
    type: 'bar',
    data: {
        labels: departmentLabels,
        datasets: [{
            label: 'Number of Employees',
            data: departmentCounts,
            backgroundColor: 'steelblue'
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true,
                ticks: { stepSize: 1 }
            }
        }
    }
});
</script>
                <tr>
                    <th>ID</th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>DOB</th>
                    <th>Joining Date</th>
                    <th>Salary</th>
                    <th>Department</th>
                    <th>Action</th>
                </tr>

                {% for emp in employees %}
                <tr>
                    {% for value in emp %}
                    <td>{{ value }}</td>
                    {% endfor %}
                    <td>
    <a href="/edit_employee/{{ emp[0] }}">Edit</a> |
    <a href="/employee_profile/{{ emp[0] }}">View Profile</a>
</td>
                    <td>
    <form action="/delete_employee/{{ emp[0] }}" method="POST">
        <button type="submit">Delete</button>
    </form>
</td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
        """,
employees=employee_rows,
avg_salary=avg_salary,
total_employees=total_employees,
department_data=department_data)

    except mysql.connector.Error as error:
        return f"Database Connection Failed: {error}"


@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        dob = request.form["dob"]
        hire_date = request.form["hire_date"]
        salary = request.form["salary"]
        department_id = request.form["department_id"]
        employee_id = request.form["id"]

        try:
            employee_store.add(employee_id,
                first_name, last_name, email, phone,
                dob, hire_date, salary, department_id,
            )
            return "Employee added successfully! <a href='/'>Back to Home</a>"

        except mysql.connector.Error as error:
            return f"Error: {error}"

    return render_template_string("""
        <h1>Add New Employee</h1>

        <form method="POST">
            Employee ID: <input type="number" name="id" required><br><br>
            First Name: <input name="first_name" required><br><br>
            Last Name: <input name="last_name" required><br><br>
            Email: <input type="email" name="email" required><br><br>
            Phone: <input name="phone"><br><br>
            Date of Birth: <input type="date" name="dob" required><br><br>
            Joining Date: <input type="date" name="hire_date" required><br><br>
            Salary: <input type="number" name="salary" step="0.01" required><br><br>
            Department ID: <input type="number" name="department_id" required><br><br>

            <button type="submit">Add Employee</button>
        </form>
    """)


@app.route("/edit_employee/<int:employee_id>", methods=["GET", "POST"])
def edit_employee(employee_id):
    if request.method == "POST":
        new_employee_id = request.form["new_employee_id"]
        try:
            employee_store.update(
                employee_id,
                new_employee_id,
                request.form["first_name"],
                request.form["last_name"],
                request.form["email"],
                request.form["phone"],
                request.form["dob"],
                request.form["hire_date"],
                request.form["salary"],
                request.form["department_id"],
            )
            return "Employee updated successfully! <a href='/'>Back to Home</a>"
        except mysql.connector.Error as error:
            return f"Error: {error}"

    employee = employee_store.get_by_id(employee_id)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT department_id, department_name FROM departments")
    departments = cursor.fetchall()
    cursor.close()
    db.close()
    if employee is None:
        return "Employee not found"
    return render_template_string("""
           <h1>Edit Employee</h1>
           
        <form method="POST">
            <input type="hidden" name="new_employee_id"
value="{{ employee.employee_id }}">
            
            First Name: <input name="first_name" value="{{ employee.first_name }}" required><br><br>
            Last Name: <input name="last_name" value="{{ employee.last_name }}" required><br><br>
            Email: <input type="email" name="email" value="{{ employee.email }}" required><br><br>
            Phone: <input name="phone" value="{{ employee.phone }}"><br><br>
            DOB: <input type="date" name="dob" value="{{ employee.dob }}"><br><br>
            Joining Date: <input type="date" name="hire_date" value="{{ employee.hire_date }}"><br><br>
            Salary: <input type="number" step="0.01" name="salary" value="{{ employee.salary }}" required><br><br>
            Department ID:
                         <select name="department_id" required>
    {% for dept in departments %}
    <option value="{{ dept.department_id }}"
    {% if dept.department_id == employee.department_id %}selected{% endif %}>
        {{ dept.department_name }}
    </option>
    {% endfor %}
</select>
            <button type="submit">Update Employee</button>
        </form>
    """, employee=employee, departments=departments)

@app.route("/delete_employee/<int:employee_id>", methods=["POST"])
def delete_employee(employee_id):
    employee_store.delete(employee_id)
    return redirect("/")
@app.route("/departments")
def departments():
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM departments ORDER BY department_id")
    department_rows = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template_string("""
        <h1>Department Management</h1>
        <a href="/">Back to Dashboard</a>

        <table border="1" cellpadding="10">
            <tr>
                <th>ID</th>
                <th>Department Name</th>
                <th>Location</th>
            </tr>
            {% for dept in departments %}
            <tr>
                <td>{{ dept[0] }}</td>
                <td>{{ dept[1] }}</td>
                <td>{{ dept[2] }}</td>
            </tr>
            {% endfor %}
        </table>
    """, departments=department_rows)
@app.route("/employee_profile/<int:employee_id>")
def employee_profile(employee_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT e.*, d.department_name
        FROM employees e
        JOIN departments d
        ON e.department_id = d.department_id
        WHERE e.employee_id = %s
    """, (employee_id,))

    employee = cursor.fetchone()
    cursor.close()
    db.close()

    if employee is None:
        return "Employee not found"

    return render_template_string("""
        <h1>Employee Profile</h1>
        <p><b>ID:</b> {{ emp[0] }}</p>
        <p><b>First Name:</b> {{ emp[1] }}</p>
        <p><b>Last Name:</b> {{ emp[2] }}</p>
        <p><b>Email:</b> {{ emp[3] }}</p>
        <p><b>Phone:</b> {{ emp[4] }}</p>
        <p><b>Date of Birth:</b> {{ emp[8] }}</p>
        <p><b>Joining Date:</b> {{ emp[5] }}</p>
        <p><b>Salary:</b> {{ emp[6] }}</p>
        <p><b>Department:</b> {{ emp[9] }}</p>
        <a href="/">Back to Dashboard</a>
    """, emp=employee)


if __name__ == "__main__":
    app.run(debug=True)