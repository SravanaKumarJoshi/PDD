"""Quick DB connectivity test. Run with: venv\Scripts\python.exe _test_db.py"""
import sys
sys.path.insert(0, "d:/Sravan/PDD")

from src.data import _get_mysql_config, load_dataset_from_mysql

print("=== MySQL config (password hidden) ===")
cfg = _get_mysql_config()
cfg_display = {k: ("***" if k == "password" else v) for k, v in cfg.items()}
print(cfg_display)

print("\n=== Testing connection + data load ===")
df, stats, err = load_dataset_from_mysql()

if err:
    print(f"FAILED: {err}")
    sys.exit(1)

print(f"SUCCESS: {len(df)} rows loaded")
print(f"Columns: {list(df.columns)}")
print(f"Stats keys: {list(stats.keys())[:5]}")
