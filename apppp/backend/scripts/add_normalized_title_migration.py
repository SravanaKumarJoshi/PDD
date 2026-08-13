"""Migration helper to add normalized_title column and composite unique constraint to projects table."""
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def run_migration():
    try:
        import mysql.connector
        host = os.getenv("MYSQL_HOST", "localhost")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "root123")
        db_name = os.getenv("MYSQL_DATABASE", "polysaccharide_selector")

        logger.info(f"Connecting to MySQL {host}:{port} database '{db_name}'...")
        conn = mysql.connector.connect(
            host=host,
            port=port,
            database=db_name,
            user=user,
            password=password,
            connection_timeout=5
        )
        cur = conn.cursor()

        # 1. Check if projects table exists
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='projects'"
        )
        table_exists = cur.fetchone()[0]
        if not table_exists:
            logger.info("Table 'projects' does not exist yet. It will be created by SQLAlchemy Base.metadata.create_all.")
            cur.close()
            conn.close()
            return

        # 2. Check if normalized_title column exists
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='projects' AND COLUMN_NAME='normalized_title'"
        )
        col_exists = cur.fetchone()[0]
        if not col_exists:
            logger.info("Adding column 'normalized_title' to 'projects' table...")
            cur.execute("ALTER TABLE projects ADD COLUMN normalized_title VARCHAR(255) NOT NULL DEFAULT ''")
            cur.execute("UPDATE projects SET normalized_title = LOWER(TRIM(title)) WHERE normalized_title = ''")
            conn.commit()
            logger.info("Column 'normalized_title' added and populated successfully.")
        else:
            logger.info("Column 'normalized_title' already exists in 'projects'.")

        # 3. Check if uq_user_project_normalized_title unique index exists
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='projects' AND INDEX_NAME='uq_user_project_normalized_title'"
        )
        idx_exists = cur.fetchone()[0]
        if not idx_exists:
            logger.info("Adding unique index 'uq_user_project_normalized_title' to 'projects'...")
            try:
                cur.execute("ALTER TABLE projects ADD CONSTRAINT uq_user_project_normalized_title UNIQUE (user_id, normalized_title)")
                conn.commit()
                logger.info("Unique index 'uq_user_project_normalized_title' added successfully.")
            except Exception as e:
                logger.warning(f"Could not create unique index (duplicate data may exist): {e}")

        cur.close()
        conn.close()
        logger.info("Migration complete.")
    except Exception as e:
        logger.warning(f"Migration script execution skipped: {e}")

if __name__ == "__main__":
    run_migration()
