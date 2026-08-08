"""Add missing columns to filtered_polymers so the sync endpoint works."""
import mysql.connector

conn = mysql.connector.connect(
    host="localhost", port=3306,
    user="root", password="root123",
    database="polysaccharide_selector"
)
cur = conn.cursor()

# Check existing columns
cur.execute("SHOW COLUMNS FROM filtered_polymers")
existing = {row[0] for row in cur.fetchall()}
print("Existing columns:", existing)

# Add columns only if they don't already exist
if "updated_at" not in existing:
    print("Adding updated_at...")
    cur.execute(
        "ALTER TABLE filtered_polymers "
        "ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP "
        "ON UPDATE CURRENT_TIMESTAMP"
    )
    conn.commit()
    print("  added updated_at")
    cur.execute(
        "CREATE INDEX idx_fp_updated_at ON filtered_polymers(updated_at)"
    )
    conn.commit()
    print("  created index on updated_at")
else:
    print("updated_at already exists, skipping")

if "source_doi" not in existing:
    print("Adding source_doi...")
    cur.execute("ALTER TABLE filtered_polymers ADD COLUMN source_doi TEXT")
    conn.commit()
    print("  added source_doi")
else:
    print("source_doi already exists, skipping")

if "id" not in existing:
    print("Adding id (virtual column = polymer name)...")
    cur.execute(
        "ALTER TABLE filtered_polymers "
        "ADD COLUMN id VARCHAR(255) GENERATED ALWAYS AS (polymer) VIRTUAL"
    )
    conn.commit()
    print("  added id")
else:
    print("id already exists, skipping")

cur.close()
conn.close()
print("\nMigration complete.")
