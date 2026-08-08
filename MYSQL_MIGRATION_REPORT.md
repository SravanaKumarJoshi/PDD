# MySQL-only migration report

## Configuration

The Streamlit application reads polymer records exclusively from
`polysaccharide_selector.filtered_polymers`. Configure `MYSQL_HOST`,
`MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` as shown in
`.env.example`. The FastAPI service uses `DATABASE_URL` with the `mysql+aiomysql`
dialect.

## Updated behavior

- Catalog reads, search, filters, statistics, model-training input, recommendations,
  explainability, and optimization load from MySQL.
- **Sync from Database** always executes a new `SELECT * FROM filtered_polymers`
  query and replaces the UI view, so inserts, updates, and deletes made in MySQL
  are reflected on the next click. It does not compare counts or use a data fallback.
- Dataset Browser inserts directly into `filtered_polymers`.
- Saved screening projects use the MySQL `saved_projects` table created on demand.
- FastAPI `/materials`, `/materials/sync`, search, and item lookup query
  `filtered_polymers` directly. `/admin/import/csv` was removed.

## Removed

- MongoDB client code, credentials, dependencies, scripts, and Atlas material API.
- Root CSV polymer datasets, sync samples, and bundled Android polymer JSON assets.
- Backend CSV ingestion module and CSV import endpoint.

## Manual verification

After installing the updated dependencies and setting the environment variables:

1. Start the app and click **Sync from Database**.
2. Insert, update, and delete records in MySQL Workbench using the table's primary key.
3. Click sync after each change; the current MySQL rows are displayed.
4. Save a screening result and reopen Projects to confirm it persists in MySQL.
