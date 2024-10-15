from flask import Flask, render_template, request, redirect, url_for,send_file
import sqlite3
import csv
import os

app = Flask(__name__)

def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                subject TEXT,
                grade INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        try:
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO students (name, roll_number) VALUES (?, ?)", (name, roll_number))
                conn.commit()
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            return "Roll number must be unique."
    return render_template('add_student.html')

@app.route('/assign_grade', methods=['GET', 'POST'])
def assign_grade():
    if request.method == 'POST':
        roll_number = request.form['roll_number']
        subject = request.form['subject']
        grade = request.form['grade']
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM students WHERE roll_number = ?", (roll_number,))
            student = cursor.fetchone()
            
            if student:
                cursor.execute("INSERT INTO grades (student_id, subject, grade) VALUES (?, ?, ?)", (student[0], subject, grade))
                conn.commit()
                return redirect(url_for('index'))
            else:
                return "Student not found."
    return render_template('assign_grade.html')

@app.route('/student/<roll_number>')
def student_details(roll_number):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM students WHERE roll_number = ?", (roll_number,))
        student = cursor.fetchone()

        if student:
            student_id = student[0]
            cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
            grades = cursor.fetchall()
            
            average = round(sum(grade[1] for grade in grades) / len(grades), 2) if grades else 0
            student_data = {
                'name': student[1],
                'roll_number': roll_number,
                'grades': grades,
                'average': average
            }
        else:
            student_data = None
    
    return render_template('average.html', student=student_data)

@app.route('/students')
def list_students():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        
        student_data = []
        for student in students:
            cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student[0],))
            grades = cursor.fetchall()
            student_data.append({
                'id': student[0],
                'name': student[1],
                'roll_number': student[2],
                'grades': grades
            })
    
    return render_template('list_students.html', students=student_data)
@app.route('/average', methods=['GET', 'POST'])
def average():
    average_grade = None
    roll_number = None
    student = None

    if request.method == 'POST':
        roll_number = request.form['roll_number']
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM students WHERE roll_number = ?", (roll_number,))
            student_data = cursor.fetchone()

            if student_data:
                student_id, student_name = student_data
                cursor.execute("SELECT AVG(grade) FROM grades WHERE student_id = ?", (student_id,))
                average_grade = round(cursor.fetchone()[0], 2)

                # Fetching grades for the student
                cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
                grades = cursor.fetchall()

                student = {
                    'name': student_name,
                    'grades': grades
                }
            else:
                return "Student not found."

    return render_template('average.html', average=average_grade, roll_number=roll_number, student=student)

@app.route('/topper', methods=['GET', 'POST'])
def topper():
    if request.method == 'POST':
        subject = request.form['subject']
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT students.name, grades.grade 
                FROM grades 
                JOIN students ON grades.student_id = students.id 
                WHERE grades.subject = ?
                ORDER BY grades.grade DESC 
                LIMIT 1
            ''', (subject,))
            topper = cursor.fetchone()
        return render_template('topper.html', subject=subject, topper=topper)
    return render_template('topper.html')
@app.route('/class_average', methods=['GET', 'POST'])
def class_average():
    average_score = None
    subject = None

    if request.method == 'POST':
        subject = request.form['subject']
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT AVG(grade) FROM grades WHERE subject = ?", (subject,))
            result = cursor.fetchone()
            average_score = round(result[0], 2) if result and result[0] is not None else 0  # Handle None case

        return render_template('class_average.html', average=average_score, subject=subject)

    # Render the form when method is GET
    return render_template('class_average.html')  # Make sure this template has the input form

@app.route('/save_data', methods=['GET'])
def save_data():
    # Use an absolute path to ensure the file is created in the expected location
    csv_filename = os.path.join(os.getcwd(), 'student_data_backup.csv')

    try:
        # Create the CSV file
        with open(csv_filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Name', 'Roll Number', 'Subject', 'Grade'])  # Header
            
            # Connect to the database and fetch data
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, roll_number FROM students")
                students = cursor.fetchall()

                for student in students:
                    student_id = student[0]
                    student_name = student[1]
                    student_roll_number = student[2]
                    
                    # Fetch grades for the student
                    cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
                    grades = cursor.fetchall()
                    
                    if grades:
                        for grade in grades:
                            csvwriter.writerow([student_name, student_roll_number, grade[0], grade[1]])
                    else:
                        # If no grades, write just the student details with empty values for Subject and Grade
                        csvwriter.writerow([student_name, student_roll_number, '', ''])

        # Send the file to the user for download
        return send_file(csv_filename, as_attachment=True)

    except Exception as e:
        return f"An error occurred: {str(e)}", 500

    finally:
        # Clean up: Remove the CSV file after sending it
        if os.path.exists(csv_filename):
            os.remove(csv_filename)



if __name__ == "__main__":
    init_db()
    app.run(debug=True)
