"""Migration check helper — called by start_backend.bat"""
import sys
try:
    import mysql.connector
    conn = mysql.connector.connect(
        host='localhost', port=3306,
        database='polysaccharide_selector',
        user='root', password='root123',
        connection_timeout=5
    )
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='filtered_polymers' "
        "AND COLUMN_NAME='updated_at'"
    )
    exists = cur.fetchone()[0]
    cur.close()
    conn.close()
    if not exists:
        print("MIGRATION NEEDED: updated_at column missing. Run: scripts\\add_updated_at_migration.sql")
    else:
        print("Migration OK: updated_at column present")
except Exception as e:
    print(f"Migration check skipped: {e}")
