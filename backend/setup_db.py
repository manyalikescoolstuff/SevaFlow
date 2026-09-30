import asyncio
import asyncpg
import getpass
import sys

async def setup():
    print("=== SevaFlow Database Setup ===")
    pg_password = getpass.getpass("Enter your master PostgreSQL password (the one you set during installation): ")
    app_password = getpass.getpass("Create a new secure password for the 'sevaflow_user' application account: ")
    
    print("\nConnecting to PostgreSQL...")
    try:
        # Connect to the default 'postgres' database as the 'postgres' superuser
        conn = await asyncpg.connect(user='postgres', password=pg_password, database='postgres', host='localhost')
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
        
    try:
        # Create database and user
        print("Creating 'sevaflow' database and 'sevaflow_user'...")
        
        # asyncpg runs commands in a transaction by default if we use transaction(), 
        # but connection.execute runs outside transaction if not explicitly requested
        # However, CREATE DATABASE cannot run inside a transaction block in postgres.
        # We must use connection.execute directly.
        
        # Check if user exists
        user_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname='sevaflow_user'")
        if not user_exists:
            await conn.execute(f"CREATE USER sevaflow_user WITH ENCRYPTED PASSWORD '{app_password}';")
            print("- User 'sevaflow_user' created.")
        else:
            print("- User 'sevaflow_user' already exists.")

        # Check if database exists
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='sevaflow'")
        if not db_exists:
            await conn.execute("CREATE DATABASE sevaflow;")
            print("- Database 'sevaflow' created.")
        else:
            print("- Database 'sevaflow' already exists.")

        await conn.execute("GRANT ALL PRIVILEGES ON DATABASE sevaflow TO sevaflow_user;")
        
        await conn.close()
        
        # Now connect to the new 'sevaflow' database to grant schema permissions
        print("Granting schema permissions...")
        conn_seva = await asyncpg.connect(user='postgres', password=pg_password, database='sevaflow', host='localhost')
        await conn_seva.execute("GRANT ALL ON SCHEMA public TO sevaflow_user;")
        await conn_seva.close()
        
        print("\n✅ Database setup complete!")
        print("\nMake sure your backend/.env file has the following DATABASE_URL:")
        print(f"DATABASE_URL=postgresql+asyncpg://sevaflow_user:{app_password}@localhost/sevaflow")
        
    except Exception as e:
        print(f"Error during setup: {e}")
    finally:
        if not conn.is_closed():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(setup())
