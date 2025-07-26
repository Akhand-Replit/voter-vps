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
            # Ensure auto-commit is off to manage transactions manually
            self.conn.autocommit = False 
            self.create_tables()
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            st.error("ডাটাবেস সংযোগ করতে ব্যর্থ। অনুগ্রহ করে আপনার শংসাপত্রগুলি পরীক্ষা করুন।")
            raise Exception("Failed to connect to database.")

    def create_tables(self):
        """
        Creates all necessary tables if they do not already exist.
        Includes dropping tables for development purposes to ensure schema updates.
        """
        with self.conn.cursor() as cur:
            # --- For Development: Drop tables to ensure fresh schema ---
            # In a production environment, you would use ALTER TABLE statements for schema migrations
            cur.execute("DROP TABLE IF EXISTS record_events CASCADE")
            cur.execute("DROP TABLE IF EXISTS records CASCADE")
            cur.execute("DROP TABLE IF EXISTS events CASCADE")
            cur.execute("DROP TABLE IF EXISTS batches CASCADE")
            self.conn.commit() # Commit drops immediately

            # Batches Table: Stores information about data batches.
            cur.execute("""
                CREATE TABLE batches (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL, -- Ensure UNIQUE constraint is applied
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Records Table: Stores the main data records.
            # Added 'gender' column
            cur.execute("""
                CREATE TABLE records (
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
                    gender VARCHAR(10), -- Added gender column
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Events Table: Stores event information.
            cur.execute("""
                CREATE TABLE events (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Record-Events Junction Table: Manages the many-to-many relationship between records and events.
            cur.execute("""
                CREATE TABLE record_events (
                    record_id INTEGER REFERENCES records(id) ON DELETE CASCADE,
                    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                    PRIMARY KEY (record_id, event_id)
                )
            """)
            self.conn.commit()

    def get_dashboard_stats(self):
        """Retrieves key statistics for the main dashboard."""
        stats = {}
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total records
            cur.execute("SELECT COUNT(*) as total_records FROM records")
            stats['total_records'] = cur.fetchone()['total_records']

            # Total batches
            cur.execute("SELECT COUNT(*) as total_batches FROM batches")
            stats['total_batches'] = cur.fetchone()['total_batches']

            # Total events
            cur.execute("SELECT COUNT(*) as total_events FROM events")
            stats['total_events'] = cur.fetchone()['total_events']

            # Relationship counts
            cur.execute("SELECT relationship_status, COUNT(*) as count FROM records GROUP BY relationship_status")
            relationship_counts = cur.fetchall()
            stats['relationships'] = {item['relationship_status']: item['count'] for item in relationship_counts}

            # Gender counts
            cur.execute("SELECT gender, COUNT(*) as count FROM records WHERE gender IS NOT NULL AND gender != '' GROUP BY gender")
            gender_counts = cur.fetchall()
            stats['genders'] = {item['gender']: item['count'] for item in gender_counts}

        return stats

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
        """
        Adds a new record to the database.
        This function only executes the INSERT statement; the calling function
        is responsible for committing or rolling back the transaction.
        """
        with self.conn.cursor() as cur:
            # logger.info(f"Attempting to insert record: {record_data}") # Keep this for debugging if needed
            cur.execute("""
                INSERT INTO records (
                    batch_id, file_name, ক্রমিক_নং, নাম, ভোটার_নং,
                    পিতার_নাম, মাতার_নাম, পেশা, জন্ম_তারিখ, ঠিকানা,
                    phone_number, facebook_link, photo_link, description,
                    relationship_status, gender
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                batch_id, file_name,
                record_data.get('ক্রমিক_নং'), record_data.get('নাম'),
                record_data.get('ভোটার_নং'), record_data.get('পিতার_নাম'),
                record_data.get('মাতার_নাম'), record_data.get('পেশা'),
                record_data.get('জন্ম_তারিখ'), record_data.get('ঠিকানা'),
                record_data.get('phone_number'), record_data.get('facebook_link'),
                record_data.get('photo_link'), record_data.get('description'),
                record_data.get('relationship_status', 'Regular'),
                record_data.get('gender')
            ))
            # logger.info("Record prepared for insertion.") # Log that it's ready, not yet committed

    def commit_changes(self):
        """Commits the current database transaction."""
        try:
            self.conn.commit()
            logger.info("Database changes committed successfully.")
        except psycopg2.Error as e:
            logger.error(f"Error committing transaction: {e}")
            self.conn.rollback() # Rollback on commit failure
            raise

    def rollback_changes(self):
        """Rolls back the current database transaction."""
        self.conn.rollback()
        logger.warning("Database transaction rolled back.")

    def update_record(self, record_id, updated_data):
        """Updates an existing record with new data."""
        with self.conn.cursor() as cur:
            query = """
                UPDATE records SET
                    ক্রমিক_নং = %s, নাম = %s, ভোটার_নং = %s, পিতার_নাম = %s,
                    মাতার_নাম = %s, পেশা = %s, ঠিকানা = %s, জন্ম_তারিখ = %s,
                    phone_number = %s, facebook_link = %s, photo_link = %s,
                    description = %s, relationship_status = %s,
                    gender = %s
                WHERE id = %s
            """
            values = (
                str(updated_data.get('ক্রমিক_নং', '')), str(updated_data.get('নাম', '')),
                str(updated_data.get('ভোটার_নং', '')), str(updated_data.get('পিতার_নাম', '')),
                str(updated_data.get('মাতার_নাম', '')), str(updated_data.get('পেশা', '')),
                str(updated_data.get('ঠিকানা', '')), str(updated_data.get('জন্ম_তারিখ', '')),
                str(updated_data.get('phone_number', '')), str(updated_data.get('facebook_link', '')),
                str(updated_data.get('photo_link', '')), str(updated_data.get('description', '')),
                str(updated_data.get('relationship_status', 'Regular')),
                str(updated_data.get('gender', '')),
                record_id
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
                    # Special handling for 'gender' to allow exact match or 'সব' for all
                    if field == 'gender' and value != 'সব':
                        query += f" AND {field} = %s"
                        params.append(value)
                    elif field != 'gender': # For other fields, use ILIKE
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

    def get_gender_stats(self, batch_id=None):
        """Retrieves gender statistics for a specific batch or all batches."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT gender, COUNT(*) as count
                FROM records
                WHERE gender IS NOT NULL AND gender != ''
            """
            if batch_id:
                query += " AND batch_id = %s"
                params = (batch_id,)
            else:
                params = ()
            query += " GROUP BY gender ORDER BY count DESC"
            cur.execute(query, params)
            return cur.fetchall()

    def update_relationship_status(self, record_id: int, status: str):
        """Updates the relationship status for a specific record."""
        with self.conn.cursor() as cur:
            cur.execute("UPDATE records SET relationship_status = %s WHERE id = %s", (status, record_id))
            self.conn.commit()

    def get_relationship_records(self, status: str):
        """Retrieves all records with a specific relationship status, including their events."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT r.*, b.name as batch_name
                FROM records r
                JOIN batches b ON r.batch_id = b.id
                WHERE r.relationship_status = %s
                ORDER BY r.created_at DESC
            """, (status,))
            records = cur.fetchall()
        for record in records:
            record['events'] = self.get_events_for_record(record['id'])
        return records

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

    def get_total_records_count(self):
        """Retrieves the total number of records in the database."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM records")
            return cur.fetchone()[0]
