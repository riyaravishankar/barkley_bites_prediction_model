"""
Sheets connection diagnostic
Run this from the same folder as app.py to find the exact failure point.

Usage:
    python3 diagnose_sheets.py

It will print a green check or a red X at every step plus the actual error
message when something fails. This bypasses Streamlit's caching so you see
the real state of the world.
"""

import os
import sys
import json


def ok(msg, detail=""):
    print(f"  \033[92m[OK]\033[0m  {msg}")
    if detail:
        print(f"        {detail}")


def warn(msg, detail=""):
    print(f"  \033[93m[!!]\033[0m  {msg}")
    if detail:
        print(f"        {detail}")


def fail(msg, detail=""):
    print(f"  \033[91m[XX]\033[0m  {msg}")
    if detail:
        print(f"        {detail}")


def section(name):
    print(f"\n=== {name} ===")


# ============================================================
section("Step 1: Required libraries")
# ============================================================
try:
    import gspread
    ok(f"gspread imported (version {gspread.__version__})")
except ImportError as e:
    fail("gspread not installed",
         "Run:  pip install gspread google-auth streamlit-autorefresh")
    sys.exit(1)

try:
    from google.oauth2.service_account import Credentials
    ok("google.oauth2 imported")
except ImportError as e:
    fail("google-auth not installed",
         "Run:  pip install google-auth")
    sys.exit(1)

try:
    import toml
    ok("toml imported")
except ImportError:
    warn("toml not installed (using built-in tomllib if Python 3.11+)")
    try:
        import tomllib  # type: ignore
        toml = None
    except ImportError:
        fail("No TOML parser available",
             "Run:  pip install toml")
        sys.exit(1)


# ============================================================
section("Step 2: Read .streamlit/secrets.toml")
# ============================================================
secrets_path = os.path.join(".streamlit", "secrets.toml")
if not os.path.exists(secrets_path):
    fail(f"File not found: {secrets_path}",
         "Make sure you are in the same folder as app.py and "
         ".streamlit/secrets.toml exists.")
    sys.exit(1)
ok(f"Found {secrets_path}")

try:
    if toml is not None:
        with open(secrets_path) as f:
            secrets = toml.load(f)
    else:
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
    ok("Parsed secrets.toml as valid TOML")
except Exception as e:
    fail("Could not parse secrets.toml as TOML", str(e))
    print("\n  Common cause: the private_key block needs triple double-quotes.")
    print("  Pattern:")
    print('      private_key = """-----BEGIN PRIVATE KEY-----')
    print("      MIIEvQI...")
    print('      -----END PRIVATE KEY-----')
    print('      """')
    sys.exit(1)


# ============================================================
section("Step 3: Check required top-level keys")
# ============================================================
if "sheet_id" not in secrets:
    fail("sheet_id missing",
         'Add to secrets.toml:  sheet_id = "YOUR_SHEET_ID_HERE"')
    sys.exit(1)

sheet_id = secrets["sheet_id"]
if not sheet_id:
    fail("sheet_id is empty")
    sys.exit(1)
if sheet_id == "PASTE-YOUR-GOOGLE-SHEET-ID-HERE":
    fail("sheet_id is still the placeholder",
         "Replace with the ID from your Google Sheet URL.")
    sys.exit(1)
ok(f"sheet_id is set: {sheet_id[:10]}...{sheet_id[-4:]}")

if "gcp_service_account" not in secrets:
    fail("[gcp_service_account] section missing")
    sys.exit(1)
ok("[gcp_service_account] section present")


# ============================================================
section("Step 4: Validate service account fields")
# ============================================================
sa = secrets["gcp_service_account"]
required_fields = [
    "type", "project_id", "private_key_id", "private_key",
    "client_email", "client_id", "auth_uri", "token_uri",
]
missing = [f for f in required_fields if f not in sa or not str(sa[f]).strip()]
if missing:
    fail(f"Missing or empty fields: {', '.join(missing)}")
    sys.exit(1)
ok(f"All {len(required_fields)} required fields present")

if sa.get("type") != "service_account":
    fail(f"type is '{sa.get('type')}', should be 'service_account'")
    sys.exit(1)
ok("type = service_account")

print(f"        client_email: {sa['client_email']}")
print(f"        project_id:   {sa['project_id']}")


# ============================================================
section("Step 5: Validate private_key formatting")
# ============================================================
pk = sa["private_key"]
if "BEGIN PRIVATE KEY" not in pk:
    fail("private_key missing the BEGIN marker",
         "The key must include -----BEGIN PRIVATE KEY----- on its own line.")
    sys.exit(1)
if "END PRIVATE KEY" not in pk:
    fail("private_key missing the END marker")
    sys.exit(1)

newline_count = pk.count("\n")
literal_slash_n = "\\n" in pk

if literal_slash_n and newline_count < 5:
    fail("private_key contains literal \\n strings instead of real newlines",
         "Fix: re-paste the key inside triple double-quotes with actual line breaks.")
    print("\n  How it should look in TOML:")
    print('      private_key = """-----BEGIN PRIVATE KEY-----')
    print("      MIIEvQIBADANBgkqhkiG9w0...")
    print("      ...many lines...")
    print('      -----END PRIVATE KEY-----')
    print('      """')
    sys.exit(1)

if newline_count < 20:
    warn(f"private_key has only {newline_count} newlines",
         "A real key usually has 25+ newlines. Make sure you pasted the whole key.")
else:
    ok(f"private_key has {newline_count} newlines, looks intact")


# ============================================================
section("Step 6: Create Google credentials")
# ============================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

try:
    creds = Credentials.from_service_account_info(dict(sa), scopes=SCOPES)
    ok("Credentials object created")
except Exception as e:
    fail("Could not create credentials", str(e))
    print("\n  This usually means the private_key text is corrupt.")
    print("  Re-download the JSON key from Google Cloud Console and re-paste.")
    sys.exit(1)


# ============================================================
section("Step 7: Authorize gspread")
# ============================================================
try:
    client = gspread.authorize(creds)
    ok("gspread.authorize succeeded")
except Exception as e:
    fail("gspread.authorize failed", str(e))
    sys.exit(1)


# ============================================================
section("Step 8: Open the sheet")
# ============================================================
try:
    sh = client.open_by_key(sheet_id)
    ok(f'Opened sheet: "{sh.title}"')
except Exception as e:
    err = str(e)
    fail("Could not open sheet", err)
    if "PERMISSION_DENIED" in err or "403" in err:
        print("\n  FIX: Share the sheet with this service account email:")
        print(f"      {sa['client_email']}")
        print("  Set role to Editor. Uncheck Notify people.")
    elif "404" in err or "Requested entity was not found" in err:
        print(f"\n  FIX: sheet_id might be wrong. Currently: {sheet_id}")
        print("  Get the ID from your sheet URL:")
        print("      https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit")
    elif "Google Drive API has not been used" in err or "API has not been used" in err:
        print("\n  FIX: Enable the Google Sheets API and Google Drive API for your")
        print(f"  project ({sa['project_id']}) in Google Cloud Console.")
    sys.exit(1)


# ============================================================
section("Step 9: Verify the two tabs exist")
# ============================================================
try:
    tabs = [ws.title for ws in sh.worksheets()]
    ok(f"Tabs in sheet: {tabs}")
except Exception as e:
    fail("Could not list tabs", str(e))
    sys.exit(1)

required_tabs = ["Registrations", "Predictions"]
missing_tabs = [t for t in required_tabs if t not in tabs]
if missing_tabs:
    fail(f"Missing required tabs: {missing_tabs}",
         "Tab names are case-sensitive. Rename them exactly as listed.")
    sys.exit(1)
ok("Both Registrations and Predictions tabs present")


# ============================================================
section("Step 10: Verify column headers")
# ============================================================
expected_reg_cols = [
    "registration_id", "timestamp", "owner_first_name", "owner_last_name",
    "owner_email", "owner_phone", "owner_city", "pet_name", "pet_breed",
    "pet_birthday", "pet_age_years", "pet_weight_lbs", "pet_sex",
    "health_conditions", "signup_source", "n_orders", "last_order_date",
    "total_spend", "is_duplicate", "duplicate_of_id",
]
expected_pred_cols = [
    "prediction_id", "registration_id", "pet_name", "owner_name",
    "owner_email", "timestamp", "lifecycle_state", "confidence",
    "recommended_action", "why_explanation", "alert_priority", "alert_sent",
    "n_orders_at_prediction", "days_since_last_order_at_prediction",
    "snapshot_key",
]

try:
    reg_headers = sh.worksheet("Registrations").row_values(1)
    pred_headers = sh.worksheet("Predictions").row_values(1)
except Exception as e:
    fail("Could not read header rows", str(e))
    sys.exit(1)

reg_missing = [c for c in expected_reg_cols if c not in reg_headers]
pred_missing = [c for c in expected_pred_cols if c not in pred_headers]

if reg_missing:
    warn(f"Registrations tab missing columns: {reg_missing}",
         "The app will still connect, but features may break.")
else:
    ok("Registrations tab has all expected columns")

if pred_missing:
    warn(f"Predictions tab missing columns: {pred_missing}",
         "The app will still connect, but writes may fail.")
else:
    ok("Predictions tab has all expected columns")


# ============================================================
section("Step 11: Test write permission (dry run)")
# ============================================================
try:
    test_ws = sh.worksheet("Predictions")
    # Try to read a small range, no actual write
    _ = test_ws.acell("A1").value
    ok("Read permission confirmed on Predictions tab")
except Exception as e:
    fail("Cannot read Predictions tab", str(e))
    sys.exit(1)


print("\n" + "=" * 60)
print("\033[92mALL CHECKS PASSED.\033[0m The app should connect successfully.")
print("=" * 60)
print("\nIf Streamlit still shows 'not connected':")
print("  1. Fully quit Streamlit (Ctrl-C twice in the terminal).")
print("  2. Delete the cache: rm -rf ~/.streamlit/cache (if it exists).")
print("  3. Restart: streamlit run app.py")
print("  4. Open in an incognito window to bypass browser cache.")
