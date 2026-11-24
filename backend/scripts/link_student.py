import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'backend/campuscare_dev.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Clean up duplicate HSINGH_BE24 placeholder
c.execute("DELETE FROM EMERGENCY_CONTACT WHERE roll_number = 'HSINGH_BE24'")
c.execute("DELETE FROM MEDICAL_PROFILE_STATUS WHERE roll_number = 'HSINGH_BE24'")
c.execute("DELETE FROM STUDENT WHERE roll_number = 'HSINGH_BE24'")
c.execute("DELETE FROM USER_ACCOUNT WHERE user_id = 5")

# Link student 1024030109 to Harshveer's Google account
c.execute("UPDATE USER_ACCOUNT SET email = 'hsingh_be24@thapar.edu', google_subject = '109225098030904306747' WHERE user_id = 8")
c.execute("UPDATE STUDENT SET email = 'hsingh_be24@thapar.edu' WHERE roll_number = '1024030109'")
conn.commit()

print("Updated successfully in:", db_path)
print("Student:", c.execute("SELECT roll_number, full_name, email, user_id FROM STUDENT WHERE roll_number = '1024030109'").fetchone())
print("User:", c.execute("SELECT user_id, email, google_subject FROM USER_ACCOUNT WHERE user_id = 8").fetchone())
print("Visits for 1024030109:", c.execute("SELECT visit_id, roll_number, status, checked_in_at FROM VISIT WHERE roll_number = '1024030109'").fetchall())
