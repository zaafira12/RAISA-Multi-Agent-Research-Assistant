import sqlite3
import os

def init_db():
    # 1. Get the path to the 'data' folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    
    # Ensure the 'data' directory exists
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    db_path = os.path.join(data_dir, 'raisa.db')
    
    # 2. Connect and Create Tables
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # User Table (For Login)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE, 
                  password TEXT)''')
    
    # Saved Papers Table (For Personal Library)
    c.execute('''CREATE TABLE IF NOT EXISTS saved_papers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id INTEGER, 
                  title TEXT, 
                  url TEXT, 
                  year INTEGER, 
                  citations INTEGER,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
                  
    conn.commit()
    conn.close()
    print(f"✅ Database initialized successfully at: {db_path}")

if __name__ == "__main__":
    init_db()