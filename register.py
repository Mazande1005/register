import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, date
import json

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Mazande_1005',
    'database': 'northlea_high'
}

class SchoolRegisterSystem:
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect_db(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except Error as e:
            st.error(f"Database connection error: {e}")
            return False
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def setup_database(self):
        """Create attendance and register tables"""
        if not self.connect_db():
            return False
        
        try:
            # Create daily_attendance table
            create_attendance_table = '''
            CREATE TABLE IF NOT EXISTS daily_attendance (
                attendance_id INT PRIMARY KEY AUTO_INCREMENT,
                student_id INT NOT NULL,
                admission_number VARCHAR(20) NOT NULL,
                attendance_date DATE NOT NULL,
                form INT NOT NULL,
                class_name VARCHAR(50) NOT NULL,
                
                -- Attendance status
                morning_status ENUM('Present', 'Absent', 'Late', 'Excused') DEFAULT 'Present',
                afternoon_status ENUM('Present', 'Absent', 'Late', 'Excused') DEFAULT 'Present',
                
                -- Daily performance
                completed_homework BOOLEAN DEFAULT TRUE,
                uniform_proper BOOLEAN DEFAULT TRUE,
                books_brought BOOLEAN DEFAULT TRUE,
                participation_level ENUM('Excellent', 'Good', 'Fair', 'Poor') DEFAULT 'Good',
                
                -- Teacher notes
                teacher_notes TEXT,
                recorded_by VARCHAR(100),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign key
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                UNIQUE KEY unique_student_date (student_id, attendance_date)
            )
            '''
            self.cursor.execute(create_attendance_table)
            
            # Create monthly_summary table
            create_summary_table = '''
            CREATE TABLE IF NOT EXISTS monthly_attendance_summary (
                summary_id INT PRIMARY KEY AUTO_INCREMENT,
                student_id INT NOT NULL,
                admission_number VARCHAR(20) NOT NULL,
                month_year VARCHAR(7) NOT NULL, -- Format: YYYY-MM
                form INT NOT NULL,
                class_name VARCHAR(50) NOT NULL,
                
                -- Attendance counts
                total_days INT DEFAULT 0,
                days_present INT DEFAULT 0,
                days_absent INT DEFAULT 0,
                days_late INT DEFAULT 0,
                days_excused INT DEFAULT 0,
                
                -- Percentage
                attendance_percentage DECIMAL(5,2) DEFAULT 0,
                
                -- Performance
                homework_completion_rate DECIMAL(5,2) DEFAULT 0,
                uniform_compliance_rate DECIMAL(5,2) DEFAULT 0,
                books_brought_rate DECIMAL(5,2) DEFAULT 0,
                average_participation VARCHAR(20),
                
                -- Notes
                comments TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                -- Foreign key
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                UNIQUE KEY unique_student_month (student_id, month_year)
            )
            '''
            self.cursor.execute(create_summary_table)
            
            # Create incidents table for special cases
            create_incidents_table = '''
            CREATE TABLE IF NOT EXISTS student_incidents (
                incident_id INT PRIMARY KEY AUTO_INCREMENT,
                student_id INT NOT NULL,
                incident_date DATE NOT NULL,
                incident_type ENUM('Positive', 'Negative', 'Neutral') NOT NULL,
                incident_category VARCHAR(100),
                description TEXT NOT NULL,
                action_taken TEXT,
                recorded_by VARCHAR(100),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            )
            '''
            self.cursor.execute(create_incidents_table)
            
            # Create class_register table (static register data)
            create_register_table = '''
            CREATE TABLE IF NOT EXISTS class_register (
                register_id INT PRIMARY KEY AUTO_INCREMENT,
                form INT NOT NULL,
                class_name VARCHAR(50) NOT NULL,
                academic_year VARCHAR(9) NOT NULL, -- Format: YYYY-YYYY
                term INT NOT NULL,
                
                -- Register details
                total_students INT DEFAULT 0,
                class_teacher VARCHAR(100),
                class_prefect VARCHAR(100),
                assistant_prefect VARCHAR(100),
                
                -- Class performance
                average_attendance DECIMAL(5,2) DEFAULT 0,
                top_performer VARCHAR(100),
                most_improved VARCHAR(100),
                
                -- Notes
                class_goals TEXT,
                special_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE KEY unique_class_term (form, class_name, academic_year, term)
            )
            '''
            self.cursor.execute(create_register_table)
            
            self.connection.commit()
            st.success("✅ Database tables created successfully!")
            return True
            
        except Error as e:
            st.error(f"Database setup error: {e}")
            return False
        finally:
            self.close_db()
    
    def get_classes(self):
        """Get all unique classes"""
        if not self.connect_db():
            return []
        
        try:
            query = """
                SELECT DISTINCT form, class_name 
                FROM students 
                WHERE form IS NOT NULL AND class_name IS NOT NULL
                ORDER BY form, class_name
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Error as e:
            st.error(f"Error fetching classes: {e}")
            return []
        finally:
            self.close_db()
    
    def get_class_students(self, form, class_name):
        """Get all students in a specific class"""
        if not self.connect_db():
            return []
        
        try:
            query = """
                SELECT student_id, admission_number, first_name, last_name, 
                       gender, date_of_birth, guardian_name, guardian_phone,
                       stream, suburb
                FROM students 
                WHERE form = %s AND class_name = %s
                ORDER BY last_name, first_name
            """
            self.cursor.execute(query, (form, class_name))
            return self.cursor.fetchall()
        except Error as e:
            st.error(f"Error fetching class students: {e}")
            return []
        finally:
            self.close_db()
    
    def save_attendance(self, attendance_data):
        """Save daily attendance for multiple students"""
        if not self.connect_db():
            return False
        
        try:
            inserted_count = 0
            for student_data in attendance_data:
                query = """
                    INSERT INTO daily_attendance 
                    (student_id, admission_number, attendance_date, form, class_name,
                     morning_status, afternoon_status, completed_homework, uniform_proper,
                     books_brought, participation_level, teacher_notes, recorded_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    morning_status = VALUES(morning_status),
                    afternoon_status = VALUES(afternoon_status),
                    completed_homework = VALUES(completed_homework),
                    uniform_proper = VALUES(uniform_proper),
                    books_brought = VALUES(books_brought),
                    participation_level = VALUES(participation_level),
                    teacher_notes = VALUES(teacher_notes),
                    recorded_by = VALUES(recorded_by)
                """
                
                self.cursor.execute(query, (
                    student_data['student_id'],
                    student_data['admission_number'],
                    student_data['attendance_date'],
                    student_data['form'],
                    student_data['class_name'],
                    student_data['morning_status'],
                    student_data['afternoon_status'],
                    student_data['completed_homework'],
                    student_data['uniform_proper'],
                    student_data['books_brought'],
                    student_data['participation_level'],
                    student_data.get('teacher_notes', ''),
                    student_data['recorded_by']
                ))
                
                if self.cursor.rowcount > 0:
                    inserted_count += 1
            
            self.connection.commit()
            return inserted_count
            
        except Error as e:
            st.error(f"Error saving attendance: {e}")
            self.connection.rollback()
            return 0
        finally:
            self.close_db()
    
    def get_todays_attendance(self, form=None, class_name=None, date_filter=None):
        """Get today's attendance records"""
        if not self.connect_db():
            return []
        
        try:
            if date_filter is None:
                date_filter = date.today()
            
            query = """
                SELECT da.*, s.first_name, s.last_name, s.gender
                FROM daily_attendance da
                JOIN students s ON da.student_id = s.student_id
                WHERE da.attendance_date = %s
            """
            params = [date_filter]
            
            if form:
                query += " AND da.form = %s"
                params.append(form)
            
            if class_name:
                query += " AND da.class_name = %s"
                params.append(class_name)
            
            query += " ORDER BY s.last_name, s.first_name"
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Error as e:
            st.error(f"Error fetching attendance: {e}")
            return []
        finally:
            self.close_db()
    
    def save_class_register(self, register_data):
        """Save class register information"""
        if not self.connect_db():
            return False
        
        try:
            query = """
                INSERT INTO class_register 
                (form, class_name, academic_year, term, total_students,
                 class_teacher, class_prefect, assistant_prefect,
                 average_attendance, top_performer, most_improved,
                 class_goals, special_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_students = VALUES(total_students),
                class_teacher = VALUES(class_teacher),
                class_prefect = VALUES(class_prefect),
                assistant_prefect = VALUES(assistant_prefect),
                average_attendance = VALUES(average_attendance),
                top_performer = VALUES(top_performer),
                most_improved = VALUES(most_improved),
                class_goals = VALUES(class_goals),
                special_notes = VALUES(special_notes)
            """
            
            self.cursor.execute(query, (
                register_data['form'],
                register_data['class_name'],
                register_data['academic_year'],
                register_data['term'],
                register_data['total_students'],
                register_data['class_teacher'],
                register_data['class_prefect'],
                register_data['assistant_prefect'],
                register_data.get('average_attendance', 0),
                register_data.get('top_performer', ''),
                register_data.get('most_improved', ''),
                register_data.get('class_goals', ''),
                register_data.get('special_notes', '')
            ))
            
            self.connection.commit()
            return True
            
        except Error as e:
            st.error(f"Error saving register: {e}")
            self.connection.rollback()
            return False
        finally:
            self.close_db()
    
    def get_class_register(self, form, class_name, academic_year, term):
        """Get class register information"""
        if not self.connect_db():
            return None
        
        try:
            query = """
                SELECT * FROM class_register 
                WHERE form = %s AND class_name = %s 
                AND academic_year = %s AND term = %s
            """
            self.cursor.execute(query, (form, class_name, academic_year, term))
            return self.cursor.fetchone()
        except Error as e:
            st.error(f"Error fetching register: {e}")
            return None
        finally:
            self.close_db()
    
    def save_incident(self, incident_data):
        """Save student incident"""
        if not self.connect_db():
            return False
        
        try:
            query = """
                INSERT INTO student_incidents 
                (student_id, incident_date, incident_type, incident_category,
                 description, action_taken, recorded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            self.cursor.execute(query, (
                incident_data['student_id'],
                incident_data['incident_date'],
                incident_data['incident_type'],
                incident_data.get('incident_category', ''),
                incident_data['description'],
                incident_data.get('action_taken', ''),
                incident_data['recorded_by']
            ))
            
            self.connection.commit()
            return True
            
        except Error as e:
            st.error(f"Error saving incident: {e}")
            self.connection.rollback()
            return False
        finally:
            self.close_db()
    
    def get_student_incidents(self, student_id=None, form=None, class_name=None):
        """Get student incidents"""
        if not self.connect_db():
            return []
        
        try:
            query = """
                SELECT si.*, s.first_name, s.last_name, s.admission_number,
                       s.form, s.class_name
                FROM student_incidents si
                JOIN students s ON si.student_id = s.student_id
                WHERE 1=1
            """
            params = []
            
            if student_id:
                query += " AND si.student_id = %s"
                params.append(student_id)
            
            if form:
                query += " AND s.form = %s"
                params.append(form)
            
            if class_name:
                query += " AND s.class_name = %s"
                params.append(class_name)
            
            query += " ORDER BY si.incident_date DESC"
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Error as e:
            st.error(f"Error fetching incidents: {e}")
            return []
        finally:
            self.close_db()
    
    def calculate_monthly_summary(self, month_year=None):
        """Calculate monthly attendance summary"""
        if not self.connect_db():
            return False
        
        try:
            if month_year is None:
                month_year = datetime.now().strftime("%Y-%m")
            
            # Calculate for each student
            query = """
                SELECT student_id, admission_number, form, class_name
                FROM students 
                WHERE form IS NOT NULL
            """
            self.cursor.execute(query)
            students = self.cursor.fetchall()
            
            updated_count = 0
            
            for student in students:
                # Get attendance for the month
                month_start = f"{month_year}-01"
                query = """
                    SELECT 
                        COUNT(*) as total_days,
                        SUM(CASE WHEN morning_status = 'Present' OR afternoon_status = 'Present' THEN 1 ELSE 0 END) as days_present,
                        SUM(CASE WHEN morning_status = 'Absent' AND afternoon_status = 'Absent' THEN 1 ELSE 0 END) as days_absent,
                        SUM(CASE WHEN morning_status = 'Late' OR afternoon_status = 'Late' THEN 1 ELSE 0 END) as days_late,
                        SUM(CASE WHEN morning_status = 'Excused' OR afternoon_status = 'Excused' THEN 1 ELSE 0 END) as days_excused,
                        AVG(CASE WHEN completed_homework THEN 1 ELSE 0 END) * 100 as homework_rate,
                        AVG(CASE WHEN uniform_proper THEN 1 ELSE 0 END) * 100 as uniform_rate,
                        AVG(CASE WHEN books_brought THEN 1 ELSE 0 END) * 100 as books_rate
                    FROM daily_attendance 
                    WHERE student_id = %s 
                    AND attendance_date >= %s 
                    AND attendance_date < DATE_ADD(%s, INTERVAL 1 MONTH)
                """
                self.cursor.execute(query, (student['student_id'], month_start, month_start))
                stats = self.cursor.fetchone()
                
                if stats['total_days'] > 0:
                    attendance_percentage = (stats['days_present'] / stats['total_days']) * 100
                    
                    # Determine average participation
                    query = """
                        SELECT participation_level, COUNT(*) as count
                        FROM daily_attendance 
                        WHERE student_id = %s 
                        AND attendance_date >= %s 
                        AND attendance_date < DATE_ADD(%s, INTERVAL 1 MONTH)
                        GROUP BY participation_level
                        ORDER BY count DESC
                        LIMIT 1
                    """
                    self.cursor.execute(query, (student['student_id'], month_start, month_start))
                    participation = self.cursor.fetchone()
                    
                    # Insert/update summary
                    query = """
                        INSERT INTO monthly_attendance_summary 
                        (student_id, admission_number, month_year, form, class_name,
                         total_days, days_present, days_absent, days_late, days_excused,
                         attendance_percentage, homework_completion_rate, uniform_compliance_rate,
                         books_brought_rate, average_participation, comments)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        total_days = VALUES(total_days),
                        days_present = VALUES(days_present),
                        days_absent = VALUES(days_absent),
                        days_late = VALUES(days_late),
                        days_excused = VALUES(days_excused),
                        attendance_percentage = VALUES(attendance_percentage),
                        homework_completion_rate = VALUES(homework_completion_rate),
                        uniform_compliance_rate = VALUES(uniform_compliance_rate),
                        books_brought_rate = VALUES(books_brought_rate),
                        average_participation = VALUES(average_participation),
                        comments = VALUES(comments)
                    """
                    
                    self.cursor.execute(query, (
                        student['student_id'],
                        student['admission_number'],
                        month_year,
                        student['form'],
                        student['class_name'],
                        stats['total_days'],
                        stats['days_present'],
                        stats['days_absent'],
                        stats['days_late'],
                        stats['days_excused'],
                        attendance_percentage,
                        stats['homework_rate'] or 0,
                        stats['uniform_rate'] or 0,
                        stats['books_rate'] or 0,
                        participation['participation_level'] if participation else 'Good',
                        f"Monthly summary for {month_year}"
                    ))
                    
                    updated_count += 1
            
            self.connection.commit()
            return updated_count
            
        except Error as e:
            st.error(f"Error calculating summary: {e}")
            self.connection.rollback()
            return 0
        finally:
            self.close_db()
    
    def get_monthly_summary(self, month_year=None, form=None, class_name=None):
        """Get monthly attendance summary"""
        if not self.connect_db():
            return []
        
        try:
            if month_year is None:
                month_year = datetime.now().strftime("%Y-%m")
            
            query = """
                SELECT mas.*, s.first_name, s.last_name, s.gender
                FROM monthly_attendance_summary mas
                JOIN students s ON mas.student_id = s.student_id
                WHERE mas.month_year = %s
            """
            params = [month_year]
            
            if form:
                query += " AND mas.form = %s"
                params.append(form)
            
            if class_name:
                query += " AND mas.class_name = %s"
                params.append(class_name)
            
            query += " ORDER BY mas.attendance_percentage DESC"
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Error as e:
            st.error(f"Error fetching summary: {e}")
            return []
        finally:
            self.close_db()

def main():
    """Main Streamlit app"""
    
    # Page configuration
    st.set_page_config(
        page_title="School Register System",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #1E40AF;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3B82F6;
    }
    .attendance-card {
        background-color: #F8FAFC;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 4px solid #3B82F6;
    }
    .present { color: #10B981; font-weight: bold; }
    .absent { color: #EF4444; font-weight: bold; }
    .late { color: #F59E0B; font-weight: bold; }
    .excused { color: #6B7280; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
    
    # App title
    st.markdown('<h1 class="main-header">📚 School Class Register System</h1>', unsafe_allow_html=True)
    
    # Initialize system
    register = SchoolRegisterSystem()
    
    # Setup database on first run
    if 'db_setup' not in st.session_state:
        if register.setup_database():
            st.session_state.db_setup = True
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/classroom.png", width=100)
        st.markdown("### Navigation")
        
        menu = st.radio(
            "Select Section:",
            ["📋 Daily Attendance", "👥 Class Register", "📊 View Records", 
             "⚠️ Incidents Log", "📈 Monthly Reports", "⚙️ Settings"]
        )
        
        st.markdown("---")
        st.markdown("### Quick Info")
        
        # Get today's date
        today = date.today()
        st.info(f"**Date:** {today.strftime('%A, %d %B %Y')}")
        
        # Get classes count
        classes = register.get_classes()
        st.metric("Total Classes", len(classes))
        
        st.markdown("---")
        st.caption(f"© {datetime.now().year} Northlea High School")
    
    # Main content
    if menu == "📋 Daily Attendance":
        daily_attendance_section(register)
    
    elif menu == "👥 Class Register":
        class_register_section(register)
    
    elif menu == "📊 View Records":
        view_records_section(register)
    
    elif menu == "⚠️ Incidents Log":
        incidents_section(register)
    
    elif menu == "📈 Monthly Reports":
        monthly_reports_section(register)
    
    elif menu == "⚙️ Settings":
        settings_section(register)

def daily_attendance_section(register):
    """Daily attendance marking section"""
    
    st.markdown('<h2 class="section-header">📋 Daily Attendance</h2>', unsafe_allow_html=True)
    
    # Get classes
    classes = register.get_classes()
    
    if not classes:
        st.warning("No classes found in database.")
        return
    
    # Select class
    class_options = [f"Form {c['form']} {c['class_name']}" for c in classes]
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_class = st.selectbox("Select Class:", class_options)
        selected_index = class_options.index(selected_class)
        selected_class_data = classes[selected_index]
    
    with col2:
        attendance_date = st.date_input("Attendance Date", date.today())
        recorded_by = st.text_input("Recorded By", "Teacher")
    
    # Get students in selected class
    students = register.get_class_students(
        selected_class_data['form'], 
        selected_class_data['class_name']
    )
    
    if not students:
        st.warning(f"No students found in {selected_class}")
        return
    
    st.markdown(f"### Class: {selected_class}")
    st.info(f"Total Students: {len(students)}")
    
    # Check if attendance already exists for today
    existing_attendance = register.get_todays_attendance(
        form=selected_class_data['form'],
        class_name=selected_class_data['class_name'],
        date_filter=attendance_date
    )
    
    # Create attendance form
    attendance_data = []
    
    st.markdown("### Mark Attendance")
    
    # Create columns for student list
    with st.form("attendance_form"):
        for i, student in enumerate(students):
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1, 1, 1])
            
            with col1:
                st.write(f"**{student['first_name']} {student['last_name']}**")
                st.caption(f"Adm: {student['admission_number']}")
            
            # Check if attendance already exists
            existing_record = next(
                (rec for rec in existing_attendance if rec['student_id'] == student['student_id']), 
                None
            )
            
            with col2:
                morning_status = st.selectbox(
                    "Morning",
                    ["Present", "Absent", "Late", "Excused"],
                    index=0 if not existing_record else 
                    ["Present", "Absent", "Late", "Excused"].index(existing_record['morning_status']),
                    key=f"morning_{i}"
                )
            
            with col3:
                afternoon_status = st.selectbox(
                    "Afternoon",
                    ["Present", "Absent", "Late", "Excused"],
                    index=0 if not existing_record else 
                    ["Present", "Absent", "Late", "Excused"].index(existing_record['afternoon_status']),
                    key=f"afternoon_{i}"
                )
            
            with col4:
                homework = st.checkbox(
                    "Homework ✓",
                    value=True if not existing_record else existing_record['completed_homework'],
                    key=f"homework_{i}"
                )
            
            with col5:
                uniform = st.checkbox(
                    "Uniform ✓",
                    value=True if not existing_record else existing_record['uniform_proper'],
                    key=f"uniform_{i}"
                )
            
            with col6:
                books = st.checkbox(
                    "Books ✓",
                    value=True if not existing_record else existing_record['books_brought'],
                    key=f"books_{i}"
                )
            
            # Participation
            participation = st.selectbox(
                "Participation Level",
                ["Excellent", "Good", "Fair", "Poor"],
                index=1 if not existing_record else 
                ["Excellent", "Good", "Fair", "Poor"].index(existing_record['participation_level']),
                key=f"participation_{i}"
            )
            
            # Teacher notes
            notes = st.text_area(
                "Teacher Notes (Optional)",
                value="" if not existing_record else (existing_record.get('teacher_notes') or ''),
                key=f"notes_{i}",
                height=50
            )
            
            st.markdown("---")
            
            # Prepare attendance data
            student_attendance = {
                'student_id': student['student_id'],
                'admission_number': student['admission_number'],
                'attendance_date': attendance_date,
                'form': selected_class_data['form'],
                'class_name': selected_class_data['class_name'],
                'morning_status': morning_status,
                'afternoon_status': afternoon_status,
                'completed_homework': homework,
                'uniform_proper': uniform,
                'books_brought': books,
                'participation_level': participation,
                'teacher_notes': notes,
                'recorded_by': recorded_by
            }
            
            attendance_data.append(student_attendance)
        
        # Submit button
        submit_button = st.form_submit_button("💾 Save Attendance")
        
        if submit_button:
            # Calculate summary
            total_students = len(attendance_data)
            present_morning = sum(1 for s in attendance_data if s['morning_status'] == 'Present')
            present_afternoon = sum(1 for s in attendance_data if s['afternoon_status'] == 'Present')
            
            # Save attendance
            saved_count = register.save_attendance(attendance_data)
            
            if saved_count > 0:
                st.success(f"✅ Attendance saved for {saved_count} students!")
                
                # Show summary
                with st.expander("Attendance Summary", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Students", total_students)
                    with col2:
                        st.metric("Morning Present", f"{present_morning} ({present_morning/total_students*100:.1f}%)")
                    with col3:
                        st.metric("Afternoon Present", f"{present_afternoon} ({present_afternoon/total_students*100:.1f}%)")
                    with col4:
                        absent_count = sum(1 for s in attendance_data if s['morning_status'] == 'Absent' and s['afternoon_status'] == 'Absent')
                        st.metric("Fully Absent", absent_count)

def class_register_section(register):
    """Class register information section"""
    
    st.markdown('<h2 class="section-header">👥 Class Register Information</h2>', unsafe_allow_html=True)
    
    # Get classes
    classes = register.get_classes()
    
    if not classes:
        st.warning("No classes found.")
        return
    
    # Select class
    class_options = [f"Form {c['form']} {c['class_name']}" for c in classes]
    selected_class = st.selectbox("Select Class:", class_options)
    selected_index = class_options.index(selected_class)
    selected_class_data = classes[selected_index]
    
    # Get academic year and term
    col1, col2, col3 = st.columns(3)
    
    with col1:
        current_year = datetime.now().year
        academic_year = st.selectbox(
            "Academic Year",
            [f"{current_year-1}-{current_year}", f"{current_year}-{current_year+1}"],
            index=1
        )
    
    with col2:
        term = st.selectbox("Term", [1, 2, 3])
    
    with col3:
        # Get students count
        students = register.get_class_students(
            selected_class_data['form'], 
            selected_class_data['class_name']
        )
        st.metric("Total Students", len(students))
    
    # Check if register already exists
    existing_register = register.get_class_register(
        selected_class_data['form'],
        selected_class_data['class_name'],
        academic_year,
        term
    )
    
    # Register form
    with st.form("register_form"):
        st.markdown("### Class Leadership")
        
        col1, col2 = st.columns(2)
        
        with col1:
            class_teacher = st.text_input(
                "Class Teacher",
                value="" if not existing_register else existing_register['class_teacher']
            )
        
        with col2:
            total_students = st.number_input(
                "Total Students",
                min_value=0,
                max_value=100,
                value=len(students) if not existing_register else existing_register['total_students']
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            class_prefect = st.text_input(
                "Class Prefect",
                value="" if not existing_register else existing_register['class_prefect']
            )
        
        with col2:
            assistant_prefect = st.text_input(
                "Assistant Prefect",
                value="" if not existing_register else existing_register['assistant_prefect']
            )
        
        st.markdown("### Performance Recognition")
        
        col1, col2 = st.columns(2)
        
        with col1:
            top_performer = st.text_input(
                "Top Performer",
                value="" if not existing_register else existing_register['top_performer']
            )
        
        with col2:
            most_improved = st.text_input(
                "Most Improved Student",
                value="" if not existing_register else existing_register['most_improved']
            )
        
        with col1:
            average_attendance = st.number_input(
                "Target Attendance %",
                min_value=0,
                max_value=100,
                value=95 if not existing_register else existing_register['average_attendance']
            )
        
        st.markdown("### Class Goals & Notes")
        
        class_goals = st.text_area(
            "Class Goals for this Term",
            value="" if not existing_register else existing_register.get('class_goals', ''),
            height=100
        )
        
        special_notes = st.text_area(
            "Special Notes",
            value="" if not existing_register else existing_register.get('special_notes', ''),
            height=100
        )
        
        # Submit button
        submit_button = st.form_submit_button("💾 Save Class Register")
        
        if submit_button:
            register_data = {
                'form': selected_class_data['form'],
                'class_name': selected_class_data['class_name'],
                'academic_year': academic_year,
                'term': term,
                'total_students': total_students,
                'class_teacher': class_teacher,
                'class_prefect': class_prefect,
                'assistant_prefect': assistant_prefect,
                'average_attendance': average_attendance,
                'top_performer': top_performer,
                'most_improved': most_improved,
                'class_goals': class_goals,
                'special_notes': special_notes
            }
            
            if register.save_class_register(register_data):
                st.success("✅ Class register saved successfully!")
            else:
                st.error("❌ Failed to save register.")

def view_records_section(register):
    """View attendance records section"""
    
    st.markdown('<h2 class="section-header">📊 View Attendance Records</h2>', unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        view_type = st.radio(
            "View:",
            ["Today's Attendance", "Date Range", "Student History"]
        )
    
    with col2:
        if view_type != "Student History":
            date_filter = st.date_input("Select Date", date.today())
        else:
            # Get students for dropdown
            classes = register.get_classes()
            if classes:
                selected_class = st.selectbox(
                    "Select Class:",
                    [f"Form {c['form']} {c['class_name']}" for c in classes]
                )
    
    with col3:
        if view_type == "Date Range":
            end_date = st.date_input("End Date", date.today())
    
    if view_type == "Today's Attendance":
        # Get today's attendance for all classes
        today_attendance = register.get_todays_attendance(date_filter=date_filter)
        
        if not today_attendance:
            st.info(f"No attendance records for {date_filter.strftime('%d %B %Y')}")
        else:
            # Group by class
            classes_data = {}
            for record in today_attendance:
                class_key = f"Form {record['form']} {record['class_name']}"
                if class_key not in classes_data:
                    classes_data[class_key] = []
                classes_data[class_key].append(record)
            
            # Display each class
            for class_name, records in classes_data.items():
                with st.expander(f"{class_name} ({len(records)} students)", expanded=True):
                    # Calculate stats
                    total = len(records)
                    present = sum(1 for r in records if r['morning_status'] == 'Present' or r['afternoon_status'] == 'Present')
                    absent = sum(1 for r in records if r['morning_status'] == 'Absent' and r['afternoon_status'] == 'Absent')
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Present", f"{present} ({present/total*100:.1f}%)")
                    with col2:
                        st.metric("Absent", f"{absent} ({absent/total*100:.1f}%)")
                    with col3:
                        late = sum(1 for r in records if r['morning_status'] == 'Late' or r['afternoon_status'] == 'Late')
                        st.metric("Late", late)
                    
                    # Display table
                    display_data = []
                    for record in records:
                        status = ""
                        if record['morning_status'] == 'Present' and record['afternoon_status'] == 'Present':
                            status = "✅ Full Day"
                        elif record['morning_status'] == 'Absent' and record['afternoon_status'] == 'Absent':
                            status = "❌ Absent"
                        elif record['morning_status'] == 'Late' or record['afternoon_status'] == 'Late':
                            status = "⚠️ Late"
                        else:
                            status = "⏰ Half Day"
                        
                        display_data.append({
                            'Student': f"{record['first_name']} {record['last_name']}",
                            'Admission': record['admission_number'],
                            'Morning': record['morning_status'],
                            'Afternoon': record['afternoon_status'],
                            'Status': status,
                            'Homework': '✓' if record['completed_homework'] else '✗',
                            'Uniform': '✓' if record['uniform_proper'] else '✗',
                            'Participation': record['participation_level']
                        })
                    
                    df = pd.DataFrame(display_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
    
    elif view_type == "Student History":
        st.info("Student history feature coming soon...")

def incidents_section(register):
    """Student incidents logging section"""
    
    st.markdown('<h2 class="section-header">⚠️ Student Incidents Log</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 Log New Incident", "📋 View Incidents"])
    
    with tab1:
        # Get classes
        classes = register.get_classes()
        
        if not classes:
            st.warning("No classes found.")
        else:
            # Select class
            class_options = [f"Form {c['form']} {c['class_name']}" for c in classes]
            selected_class = st.selectbox("Select Class:", class_options, key="incident_class")
            selected_index = class_options.index(selected_class)
            selected_class_data = classes[selected_index]
            
            # Get students in class
            students = register.get_class_students(
                selected_class_data['form'], 
                selected_class_data['class_name']
            )
            
            if not students:
                st.warning("No students in selected class.")
            else:
                # Incident form
                with st.form("incident_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Student selection
                        student_options = [f"{s['admission_number']} - {s['first_name']} {s['last_name']}" 
                                         for s in students]
                        selected_student = st.selectbox("Select Student:", student_options)
                        student_index = student_options.index(selected_student)
                        student_data = students[student_index]
                    
                    with col2:
                        incident_date = st.date_input("Incident Date", date.today())
                        recorded_by = st.text_input("Recorded By", "Teacher")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        incident_type = st.selectbox(
                            "Incident Type",
                            ["Positive", "Negative", "Neutral"]
                        )
                    
                    with col2:
                        incident_category = st.selectbox(
                            "Category",
                            ["Academic", "Behavior", "Attendance", "Sports", "Other"]
                        )
                    
                    description = st.text_area("Description", height=100)
                    action_taken = st.text_area("Action Taken (if any)", height=100)
                    
                    submit_button = st.form_submit_button("💾 Log Incident")
                    
                    if submit_button:
                        incident_data = {
                            'student_id': student_data['student_id'],
                            'incident_date': incident_date,
                            'incident_type': incident_type,
                            'incident_category': incident_category,
                            'description': description,
                            'action_taken': action_taken,
                            'recorded_by': recorded_by
                        }
                        
                        if register.save_incident(incident_data):
                            st.success("✅ Incident logged successfully!")
                        else:
                            st.error("❌ Failed to log incident.")
    
    with tab2:
        # View incidents with filters
        col1, col2 = st.columns(2)
        
        with col1:
            incident_type_filter = st.selectbox(
                "Filter by Type:",
                ["All", "Positive", "Negative", "Neutral"]
            )
        
        with col2:
            # Get classes for filter
            classes = register.get_classes()
            if classes:
                class_filter = st.selectbox(
                    "Filter by Class:",
                    ["All"] + [f"Form {c['form']} {c['class_name']}" for c in classes]
                )
            else:
                class_filter = "All"
        
        # Get incidents
        incidents = register.get_student_incidents()
        
        if not incidents:
            st.info("No incidents recorded yet.")
        else:
            # Apply filters
            filtered_incidents = incidents
            
            if incident_type_filter != "All":
                filtered_incidents = [i for i in filtered_incidents if i['incident_type'] == incident_type_filter]
            
            if class_filter != "All":
                form = int(class_filter.split()[1])
                class_name = class_filter.split()[2]
                filtered_incidents = [i for i in filtered_incidents if i['form'] == form and i['class_name'] == class_name]
            
            # Display incidents
            st.metric("Total Incidents", len(filtered_incidents))
            
            for incident in filtered_incidents:
                # Color based on type
                if incident['incident_type'] == 'Positive':
                    border_color = "#10B981"
                    icon = "✅"
                elif incident['incident_type'] == 'Negative':
                    border_color = "#EF4444"
                    icon = "❌"
                else:
                    border_color = "#6B7280"
                    icon = "ℹ️"
                
                st.markdown(f"""
                <div style='border-left: 4px solid {border_color}; padding: 10px; margin: 10px 0; background-color: #F8FAFC; border-radius: 5px;'>
                    <strong>{icon} {incident['incident_type']} - {incident['incident_category']}</strong><br>
                    <small>Date: {incident['incident_date']} | Student: {incident['first_name']} {incident['last_name']} ({incident['admission_number']})</small><br>
                    {incident['description']}<br>
                    <small><strong>Action:</strong> {incident.get('action_taken', 'None recorded')}</small>
                </div>
                """, unsafe_allow_html=True)

def monthly_reports_section(register):
    """Monthly reports section"""
    
    st.markdown('<h2 class="section-header">📈 Monthly Attendance Reports</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 Generate Report", "📋 View Reports"])
    
    with tab1:
        st.markdown("### Generate Monthly Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_month = datetime.now().strftime("%Y-%m")
            month_year = st.text_input(
                "Month-Year (YYYY-MM)",
                value=current_month
            )
        
        with col2:
            st.write("")  # Spacing
            if st.button("📊 Generate Monthly Summary", type="primary"):
                with st.spinner("Calculating monthly summary..."):
                    updated_count = register.calculate_monthly_summary(month_year)
                    
                    if updated_count > 0:
                        st.success(f"✅ Monthly summary generated for {updated_count} students!")
                    else:
                        st.info("No attendance data found for calculation.")
    
    with tab2:
        st.markdown("### View Monthly Reports")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_month = datetime.now().strftime("%Y-%m")
            report_month = st.text_input(
                "Select Month (YYYY-MM)",
                value=current_month,
                key="report_month"
            )
        
        with col2:
            # Get classes for filter
            classes = register.get_classes()
            if classes:
                class_filter = st.selectbox(
                    "Filter by Class:",
                    ["All"] + [f"Form {c['form']} {c['class_name']}" for c in classes],
                    key="report_class"
                )
            else:
                class_filter = "All"
        
        # Get monthly summary
        if st.button("📋 Load Report"):
            with st.spinner("Loading report..."):
                # Parse class filter
                if class_filter != "All":
                    form = int(class_filter.split()[1])
                    class_name = class_filter.split()[2]
                    summary = register.get_monthly_summary(
                        month_year=report_month,
                        form=form,
                        class_name=class_name
                    )
                else:
                    summary = register.get_monthly_summary(month_year=report_month)
                
                if not summary:
                    st.info(f"No monthly report found for {report_month}")
                else:
                    st.success(f"✅ Loaded report for {len(summary)} students")
                    
                    # Overall statistics
                    total_students = len(summary)
                    avg_attendance = np.mean([s['attendance_percentage'] for s in summary])
                    perfect_attendance = sum(1 for s in summary if s['attendance_percentage'] == 100)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Students", total_students)
                    with col2:
                        st.metric("Average Attendance", f"{avg_attendance:.1f}%")
                    with col3:
                        st.metric("Perfect Attendance", perfect_attendance)
                    
                    # Display report
                    display_data = []
                    for record in summary:
                        # Determine attendance status
                        if record['attendance_percentage'] >= 90:
                            status = "Excellent"
                            color = "green"
                        elif record['attendance_percentage'] >= 80:
                            status = "Good"
                            color = "blue"
                        elif record['attendance_percentage'] >= 70:
                            status = "Fair"
                            color = "orange"
                        else:
                            status = "Poor"
                            color = "red"
                        
                        display_data.append({
                            'Student': f"{record['first_name']} {record['last_name']}",
                            'Admission': record['admission_number'],
                            'Class': f"Form {record['form']} {record['class_name']}",
                            'Attendance %': f"{record['attendance_percentage']:.1f}%",
                            'Status': status,
                            'Present': record['days_present'],
                            'Absent': record['days_absent'],
                            'Late': record['days_late'],
                            'Homework %': f"{record['homework_completion_rate']:.1f}%",
                            'Participation': record['average_participation']
                        })
                    
                    df = pd.DataFrame(display_data)
                    st.dataframe(
                        df.style.background_gradient(subset=['Attendance %'], cmap='RdYlGn'),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Download option
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"attendance_report_{report_month}.csv",
                        mime="text/csv"
                    )

def settings_section(register):
    """Settings section"""
    
    st.markdown('<h2 class="section-header">⚙️ System Settings</h2>', unsafe_allow_html=True)
    
    st.markdown("### Database Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Recreate Database Tables", type="secondary"):
            with st.spinner("Recreating tables..."):
                if register.setup_database():
                    st.success("✅ Database tables recreated successfully!")
                else:
                    st.error("❌ Failed to recreate tables.")
    
    with col2:
        if st.button("🧹 Clear Test Data", type="secondary"):
            st.warning("This will delete all attendance and incident records!")
            confirm = st.checkbox("I understand this action cannot be undone")
            if confirm and st.button("⚠️ Confirm Delete", type="primary"):
                # Add delete logic here
                st.info("Delete functionality coming soon...")
    
    st.markdown("### Export Data")
    
    if st.button("📤 Export All Data to CSV", type="primary"):
        # Get all data
        incidents = register.get_student_incidents()
        # Add more data exports as needed
        
        if incidents:
            incidents_df = pd.DataFrame(incidents)
            csv = incidents_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Incidents CSV",
                data=csv,
                file_name="school_incidents_export.csv",
                mime="text/csv"
            )
    
    st.markdown("### System Information")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.info("""
        **System Features:**
        - Daily attendance tracking
        - Class register management
        - Incident logging
        - Monthly reports
        - Student performance tracking
        """)
    
    with info_col2:
        st.info("""
        **Current Status:**
        - Database: Connected
        - Tables: Ready
        - Students: Loaded from database
        - Classes: Available
        """)
    
    st.markdown("### About")
    st.caption("""
    **School Register System v1.0**  
    Developed for Northlea High School  
    Last updated: December 2024  
    For support, contact the IT Department
    """)

if __name__ == "__main__":
    main()
