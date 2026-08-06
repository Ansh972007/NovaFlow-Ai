from app.database import SessionLocal

db = SessionLocal()
try:
    # Add new columns to users table (no default for TEXT column in MySQL)
    db.execute('ALTER TABLE users ADD COLUMN user_api_key_enc TEXT')
    db.execute('ALTER TABLE users ADD COLUMN user_api_provider VARCHAR(32) DEFAULT "openrouter"')
    db.execute('ALTER TABLE users ADD COLUMN user_api_model VARCHAR(120) DEFAULT "openai/gpt-4o-mini"')
    db.execute('ALTER TABLE users ADD COLUMN user_api_base_url VARCHAR(512) DEFAULT ""')
    
    # Update default role to admin
    db.execute('UPDATE users SET role = "admin" WHERE role = "editor"')
    
    db.commit()
    print('Database columns added successfully')
except Exception as e:
    print(f'Error: {e}')
    db.rollback()
finally:
    db.close()