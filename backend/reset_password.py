"""
One-time password reset script for existing Staff users.
Uses the existing Staff model, database session, and bcrypt hash function.
"""
import asyncio
import getpass
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.schema import Staff


async def reset_password():
    username = input("Enter staff username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    new_password = getpass.getpass("Enter new password: ")
    if not new_password:
        print("Password cannot be empty.")
        sys.exit(1)

    confirm_password = getpass.getpass("Confirm new password: ")
    if new_password != confirm_password:
        print("Passwords do not match.")
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Staff).where(Staff.username == username))
        staff = result.scalars().first()

        if not staff:
            print("Staff user not found.")
            sys.exit(1)

        # Hash securely using existing bcrypt logic
        staff.hashed_password = hash_password(new_password)
        await session.commit()
        print("Password updated successfully.")


if __name__ == "__main__":
    asyncio.run(reset_password())
