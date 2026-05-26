"""Shared database connection utilities with retry logic."""

import os
import time
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")


def connect_with_retry(url=None, retries=5, base_delay=15):
    """Connect to PostgreSQL with exponential backoff retries.

    Supabase free tier pgBouncer can drop requests when the pool is saturated
    (e.g., after auto-resume from pause or concurrent workflow overlap).
    """
    url = url or DB_URL
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(url, connect_timeout=30)
            if attempt > 1:
                print(f"Connected on attempt {attempt}")
            return conn
        except psycopg2.OperationalError as e:
            last_err = e
            if attempt < retries:
                delay = base_delay * attempt
                print(f"DB connection attempt {attempt} failed: {e}")
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
    raise last_err


def sqlalchemy_engine_with_retry(url=None, retries=5, base_delay=15):
    """Create a SQLAlchemy engine and verify connectivity with retries."""
    from sqlalchemy import create_engine, text
    url = url or DB_URL
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            engine = create_engine(url, connect_args={"connect_timeout": 30})
            with engine.connect() as test_conn:
                test_conn.execute(text("SELECT 1"))
            if attempt > 1:
                print(f"Connected on attempt {attempt}")
            return engine
        except Exception as e:
            last_err = e
            if attempt < retries:
                delay = base_delay * attempt
                print(f"DB connection attempt {attempt} failed: {e}")
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
    raise last_err
