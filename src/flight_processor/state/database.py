"""SQLite database initialization and schema"""
import sqlite3
import logging

logger = logging.getLogger(__name__)


def init_database(db_path):
    """
    Initialize the SQLite database with schema
    
    Args:
        db_path: Path to the SQLite database file
    """
    logger.info(f"Initializing database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create emails table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            message_id TEXT PRIMARY KEY,
            thread_id TEXT,
            subject TEXT,
            from_email TEXT,
            msg_date TEXT,
            pnr TEXT,
            flight_number TEXT,
            departure_airport TEXT,
            arrival_airport TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create processing_state table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            retry_count INTEGER DEFAULT 0,
            FOREIGN KEY (message_id) REFERENCES emails(message_id)
        )
    """)
    
    # Create sync_checkpoints table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_synced_message_id TEXT,
            last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            failed_message_ids TEXT,
            message TEXT
        )
    """)
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_processing_phase 
        ON processing_state(phase, status)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_message_id 
        ON processing_state(message_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pnr 
        ON emails(pnr)
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")
