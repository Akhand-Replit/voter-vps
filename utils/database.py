import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

class Database:
    """
    Handles all database operations for the application, including connecting to
    PostgreSQL, creating tables, and managing records, batches, and events.
    """
    def __init__(self):
        """Initializes the database connection using credentials from Streamlit secrets."""
        try:
            self.conn = psycopg2.connect(
                dbname=st.secrets["DB_NAME"],
                user=st.secrets["DB_USER"],
                password=st.secrets["DB_PASSWORD"],
                host=st.secrets["DB_HOST"],
                port=st.secrets["DB_PORT"],
            )
            self.create_tables()
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            st.error("ডাটাবেস সংযোগ করতে ব্যর্থ। অনুগ্রহ করে আপনার শংসাপত্রগুলি পরীক্ষা করুন।")
            raise Exception("Failed to connect to database.")

    def create_tables(self):
        """Creates all necessary tables if they do not already exist."""
        with self.conn.cursor() as cur:
            # Batches Table: Stores information about data batches.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Records Table: Stores the main data records.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    batch_id INTEGER REFERENCES batches(id) ON DELETE CASCADE,
                    file_name VARCHAR(255),
                    ক্রমিক_নং VARCHAR(50),
                    নাম TEXT,
                    ভোটার_নং VARCHAR(100),
                    পিতার_নাম TEXT,
                    মাতার_নাম TEXT,
                    পেশা TEXT,
                    জন্ম_তারিখ VARCHAR(100),
                    ঠিকানা TEXT,
                    phone_number VARCHAR(50),
                    facebook_link TEXT,
                    photo_link TEXT,
                    description TEXT,
                    relationship_status VARCHAR(20) DEFAULT 'Regular',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Events Table: Stores event information.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Record-Events Junction Table: Manages the many-to-many relationship between records and events.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS record_events (
                    record_id INTEGER REFERENCES records(id) ON DELETE CASCADE,
                    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                    PRIMARY KEY (record_id, event_id)
                )
            """)
            self.conn.commit()

    # --- Event Management ---
    def add_event(self, event_name):
        """Adds a new event to the database."""
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO events (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (event_name,))
            self.conn.commit()

    def get_all_events(self):
        """Retrieves all events from the database."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM events ORDER BY name")
            return cur.fetchall()

    def delete_event(self, event_id):
        """Deletes an event and its associations from the database."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM record_events WHERE event_id = %s", (event_id,))
            cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
            self.conn.commit()

    def get_events_for_record(self, record_id):
        """Retrieves all event names assigned to a specific record."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT e.name
                FROM events e
                JOIN record_events re ON e.id = re.event_id
                WHERE re.record_id = %s
                ORDER BY e.name
            """, (record_id,))
            return [row[0] for row in cur.fetchall()]

    def assign_events_to_record(self, record_id, event_ids):
        """Assigns a list of events to a record, replacing any existing assignments."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM record_events WHERE record_id = %s", (record_id,))
            if event_ids:
                args_str = ','.join(cur.mogrify("(%s,%s)", (record_id, event_id)).decode('utf-8') for event_id in event_ids)
                cur.execute("INSERT INTO record_events (record_id, event_id) VALUES " + args_str)
            self.conn.commit()

    def get_records_for_event(self, event_id):
        """Gets all records associated with a specific event ID."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT r.*, b.name as batch_name
                FROM records r
                JOIN record_events re ON r.id = re.record_id
                JOIN batches b ON r.batch_id = b.id
                WHERE re.event_id = %s
                ORDER BY r.id
            """, (event_id,))
            records = cur.fetchall()
        # Fetch associated events for each record (though they should all include the filtered event)
        for record in records:
            record['events'] = self.get_events_for_record(record['id'])
        return records

    # --- Record & Batch Management ---
    def add_batch(self, batch_name):
        """Adds a new batch or returns the ID of an existing one."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO batches (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id",
                (batch_name,)
            )
            result = cur.fetchone()
            self.conn.commit()
            return result['id']

    def add_record(self, batch_id, file_name, record_data):
        """Adds a new record to the database."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO records (
                    batch_id, file_name, ক্রমিক_নং, নাম, ভোটার_নং,
                    পিতার_নাম, মাতার_নাম, পেশা, জন্ম_তারিখ, ঠিকানা,
                    phone_number, facebook_link, photo_link, description,
                    relationship_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                batch_id, file_name,
                record_data.get('ক্রমিক_নং'), record_data.get('নাম'),
                record_data.get('ভোটার_নং'), record_data.get('পিতার_নাম'),
                record_data.get('মাতার_নাম'), record_data.get('পেশা'),
                record_data.get('জন্ম_তারিখ'), record_data.get('ঠিকানা'),
                record_data.get('phone_number'), record_data.get('facebook_link'),
                record_data.get('photo_link'), record_data.get('description'),
                'Regular'
            ))
            self.conn.commit()

    def update_record(self, record_id, updated_data):
        """Updates an existing record with new data."""
        with self.conn.cursor() as cur:
            query = """
                UPDATE records SET
                    ক্রমিক_নং = %s, নাম = %s, ভোটার_নং = %s, পিতার_নাম = %s,
                    মাতার_নাম = %s, পেশা = %s, ঠিকানা = %s, জন্ম_তারিখ = %s,
                    phone_number = %s, facebook_link = %s, photo_link = %s,
                    description = %s, relationship_status = %s
                WHERE id = %s
            """
            values = (
                str(updated_data.get('ক্রমিক_নং', '')), str(updated_data.get('নাম', '')),
                str(updated_data.get('ভোটার_নং', '')), str(updated_data.get('পিতার_নাম', '')),
                str(updated_data.get('মাতার_নাম', '')), str(updated_data.get('পেশা', '')),
                str(updated_data.get('ঠিকানা', '')), str(updated_data.get('জন্ম_তারিখ', '')),
                str(updated_data.get('phone_number', '')), str(updated_data.get('facebook_link', '')),
                str(updated_data.get('photo_link', '')), str(updated_data.get('description', '')),
                str(updated_data.get('relationship_status', 'Regular')), record_id
            )
            cur.execute(query, values)
            self.conn.commit()

    def search_records_advanced(self, criteria):
        """Performs an advanced search for records based on multiple criteria."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT r.*, b.name as batch_name FROM records r JOIN batches b ON r.batch_id = b.id WHERE 1=1"
            params = []
            for field, value in criteria.items():
                if value:
                    query += f" AND {field} ILIKE %s"
                    params.append(f"%{value}%")
            query += " ORDER BY r.id"
            cur.execute(query, params)
            records = cur.fetchall()
        for record in records:
            record['events'] = self.get_events_for_record(record['id'])
        return records

    def get_all_batches(self):
        """Retrieves all batches from the database."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM batches ORDER BY created_at DESC")
            return cur.fetchall()

    def get_batch_records(self, batch_id):
        """Retrieves all records for a specific batch."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT r.*, b.name as batch_name
                FROM records r
                JOIN batches b ON r.batch_id = b.id
                WHERE r.batch_id = %s
                ORDER BY r.id
            """, (batch_id,))
            records = cur.fetchall()
        for record in records:
            record['events'] = self.get_events_for_record(record['id'])
        return records
        
    def get_batch_files(self, batch_id):
        """Get unique files in a batch"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT file_name
                FROM records
                WHERE batch_id = %s
                ORDER BY file_name
            """, (batch_id,))
            return cur.fetchall()

    def get_file_records(self, batch_id, file_name):
        """Get records for a specific file in a batch"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT r.*, b.name as batch_name
                FROM records r
                JOIN batches b ON r.batch_id = b.id
                WHERE r.batch_id = %s AND r.file_name = %s
                ORDER BY r.id
            """, (batch_id, file_name))
            records = cur.fetchall()
        for record in records:
            record['events'] = self.get_events_for_record(record['id'])
        return records

    def get_batch_occupation_stats(self, batch_id):
        """Retrieves occupation statistics for a specific batch."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT পেশা, COUNT(*) as count
                FROM records
                WHERE batch_id = %s AND পেশা IS NOT NULL AND পেশা != ''
                GROUP BY পেশা ORDER BY count DESC
            """, (batch_id,))
            return cur.fetchall()

    def get_occupation_stats(self):
        """Retrieves overall occupation statistics across all batches."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT পেশা, COUNT(*) as count
                FROM records
                WHERE পেশা IS NOT NULL AND পেশা != ''
                GROUP BY পেশা ORDER BY count DESC
            """)
            return cur.fetchall()

    def update_relationship_status(self, record_id: int, status: str):
        """Updates the relationship status for a specific record."""
        with self.conn.cursor() as cur:
            cur.execute("UPDATE records SET relationship_status = %s WHERE id = %s", (status, record_id))
            self.conn.commit()

    def get_relationship_records(self, status: str):
        """Retrieves all records with a specific relationship status."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT r.*, b.name as batch_name
                FROM records r
                JOIN batches b ON r.batch_id = b.id
                WHERE r.relationship_status = %s
                ORDER BY r.created_at DESC
            """, (status,))
            return cur.fetchall()

    def get_batch_by_name(self, batch_name):
        """Retrieves batch information by its name."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM batches WHERE name = %s", (batch_name,))
            return cur.fetchone()

    def get_batch_by_id(self, batch_id):
        """Retrieves batch information by its ID."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM batches WHERE id = %s", (batch_id,))
            return cur.fetchone()

    def delete_batch(self, batch_id: int):
        """Deletes a batch and all its associated records."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM records WHERE batch_id = %s", (batch_id,))
            cur.execute("DELETE FROM batches WHERE id = %s", (batch_id,))
            self.conn.commit()

