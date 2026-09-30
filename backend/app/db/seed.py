"""
Database seed — runs on startup if tables are empty.
Creates services, queues, counters, and staff accounts with hashed passwords.
Staff credentials (printed once to console on first run):
  admin / sevaflow_admin
  staff01..06 / sevaflow_staff
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.security import hash_password
from app.models.schema import Service, Queue, Counter, Staff, Token


async def seed_db(db: AsyncSession):
    # Already seeded?
    result = await db.execute(select(Service).limit(1))
    if result.scalars().first():
        return

    print("[SevaFlow] Seeding database with initial data...")

    # --- Services ---
    services = [
        Service(id="svc-aadhaar", name="KYC",               expected_duration_sec=300),
        Service(id="svc-pan",     name="New account",       expected_duration_sec=240),
        Service(id="svc-income",  name="Cash Transactions", expected_duration_sec=360),
        Service(id="svc-land",    name="Help desk",         expected_duration_sec=480),
    ]
    db.add_all(services)
    await db.flush()

    # --- Queues (one per service) ---
    queues = [
        Queue(id="q-aadhaar", service_id="svc-aadhaar"),
        Queue(id="q-pan",     service_id="svc-pan"),
        Queue(id="q-income",  service_id="svc-income"),
        Queue(id="q-land",    service_id="svc-land"),
    ]
    db.add_all(queues)
    await db.flush()

    # --- Staff ---
    staff_password = hash_password("sevaflow_staff")
    admin_password = hash_password("sevaflow_admin")

    staff_members = [
        Staff(id="stf-admin", name="Admin",     username="admin",   hashed_password=admin_password,  role="ADMIN"),
        Staff(id="stf-01",    name="Anjali S.", username="staff01", hashed_password=staff_password,  role="STAFF"),
        Staff(id="stf-02",    name="Rahul M.",  username="staff02", hashed_password=staff_password,  role="STAFF"),
        Staff(id="stf-03",    name="Priya K.",  username="staff03", hashed_password=staff_password,  role="STAFF"),
        Staff(id="stf-04",    name="Amit V.",   username="staff04", hashed_password=staff_password,  role="STAFF"),
        Staff(id="stf-05",    name="Neha P.",   username="staff05", hashed_password=staff_password,  role="STAFF"),
        Staff(id="stf-06",    name="Vikram D.", username="staff06", hashed_password=staff_password,  role="STAFF"),
    ]
    db.add_all(staff_members)
    await db.flush()

    # --- Counters ---
    counters = [
        Counter(id="ctr-01", label="Counter 01", service_id="svc-aadhaar", queue_id="q-aadhaar", status="ACTIVE", staff_id="stf-01"),
        Counter(id="ctr-02", label="Counter 02", service_id="svc-pan",    queue_id="q-pan",     status="ACTIVE", staff_id="stf-02"),
        Counter(id="ctr-03", label="Counter 03", service_id="svc-income",  queue_id="q-income",  status="ACTIVE", staff_id="stf-03"),
        Counter(id="ctr-04", label="Counter 04", service_id="svc-income",  queue_id="q-income",  status="ACTIVE", staff_id="stf-04"),
        Counter(id="ctr-05", label="Counter 05", service_id="svc-land",    queue_id="q-land",    status="ACTIVE", staff_id="stf-05"),
        Counter(id="ctr-06", label="Counter 06", service_id="svc-aadhaar", queue_id="q-aadhaar", status="PAUSED", staff_id="stf-06"),
    ]
    db.add_all(counters)
    await db.flush()

    # --- Mock Tokens (Customers) for Demo ---
    now = datetime.now(timezone.utc)
    future = now + timedelta(minutes=30)
    
    tokens = [
        # WAITING tokens
        Token(id="tok-01", display_number="A001", queue_id="q-aadhaar", status="WAITING", 
              hardware_reservation_id="hw-01", claim_secret_hash="fakehash", 
              customer_name="Ramesh Kumar", phone_number="9876543210", 
              scan_sequence=1, sort_key=1, reservation_expires_at=future, registered_at=now - timedelta(minutes=10)),
        Token(id="tok-02", display_number="A002", queue_id="q-aadhaar", status="WAITING", 
              hardware_reservation_id="hw-02", claim_secret_hash="fakehash", 
              customer_name="Sita Devi", phone_number="9876543211", 
              scan_sequence=2, sort_key=2, reservation_expires_at=future, registered_at=now - timedelta(minutes=5)),
        Token(id="tok-03", display_number="P001", queue_id="q-pan", status="WAITING", 
              hardware_reservation_id="hw-03", claim_secret_hash="fakehash", 
              customer_name="Vijay Singh", phone_number="9876543212", 
              scan_sequence=1, sort_key=1, reservation_expires_at=future, registered_at=now - timedelta(minutes=15)),
        
        # SERVING tokens
        Token(id="tok-04", display_number="I001", queue_id="q-income", status="SERVING", 
              hardware_reservation_id="hw-04", claim_secret_hash="fakehash", 
              customer_name="Anita Roy", phone_number="9876543213", 
              scan_sequence=1, sort_key=1, reservation_expires_at=future, registered_at=now - timedelta(minutes=20),
              called_at=now - timedelta(minutes=10), serving_started_at=now - timedelta(minutes=9)),
        
        # COMPLETED tokens
        Token(id="tok-05", display_number="L001", queue_id="q-land", status="COMPLETED", 
              hardware_reservation_id="hw-05", claim_secret_hash="fakehash", 
              customer_name="Karan Patel", phone_number="9876543214", 
              scan_sequence=1, sort_key=1, reservation_expires_at=future, registered_at=now - timedelta(minutes=60),
              called_at=now - timedelta(minutes=50), serving_started_at=now - timedelta(minutes=45), completed_at=now - timedelta(minutes=30)),
    ]
    db.add_all(tokens)
    
    # Assign SERVING token to a counter
    counters[2].current_token_id = "tok-04" # ctr-03 is serving I001

    await db.commit()
    print("[SevaFlow] Seed complete.")
    print("[SevaFlow]   admin / sevaflow_admin")
    print("[SevaFlow]   staff01-06 / sevaflow_staff")
