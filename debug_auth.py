from sqlmodel import Session, select
from backend.database import engine, create_db_and_tables
from backend.models import User, UserRole
from backend.auth import get_password_hash

def debug_auth():
    print("Creating DB and tables...")
    create_db_and_tables()
    
    print("Attempting to create user...")
    try:
        with Session(engine) as session:
            # Check if user exists
            statement = select(User).where(User.email == "debug@example.com")
            user = session.exec(statement).first()
            if user:
                print("User already exists, deleting...")
                session.delete(user)
                session.commit()
            
            new_user = User(
                username="debug_user",
                email="debug@example.com",
                hashed_password=get_password_hash("password"),
                role=UserRole.USER,
                name="Debug User"
            )
            print(f"User object created: {new_user}")
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            print(f"User saved successfully: {new_user}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_auth()
