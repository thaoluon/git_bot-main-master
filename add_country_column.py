"""
Script to add country column to users table.
Run this script to add the country column if migration doesn't work.
"""
from sqlalchemy import text
from app.database import engine

def add_country_column():
    """Add country column to users table if it doesn't exist"""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='country'
        """))
        
        if result.fetchone():
            print("Column 'country' already exists. Skipping.")
            return
        
        # Add country column
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN country VARCHAR(10)
        """))
        
        # Add index on country column
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_users_country ON users(country)
        """))
        
        # Check if git_username column exists, if not add it
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='git_username'
        """))
        
        if not result.fetchone():
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN git_username VARCHAR(255) UNIQUE
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_git_username ON users(git_username)
            """))
        
        conn.commit()
        print("Successfully added 'country' column to users table.")

if __name__ == "__main__":
    try:
        add_country_column()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()



