# Streamlit Cloud deployment - verification and cleanup

Your live URL: https://barkley-bites-prediction-model.streamlit.app/
Your repo:    https://github.com/riyaravishankar/barkley_bites_prediction_model

Run through this checklist top to bottom whenever something looks off on
Cloud while working locally. Each section is independent.

---

## Part 1: Repo structure sanity check

In your local clone, run:

```bash
ls -la
ls -la .streamlit/
```

You should see exactly these top-level files:

```
app.py                          (only one - delete any app_v1.py, app_old.py)
requirements.txt
README.md
SETUP_GUIDE.md
GITHUB_STREAMLIT_UPDATE.md
WEBSITE_INTEGRATION.md          (new in v4)
diagnose_sheets.py
.gitignore
.streamlit/
artifacts/                      (model files)
data/                           (training data)
scripts/                        (build_dataset.py, train_model.py)
google_sheets/                  (apps script + form setup)
web_integration/                (new in v4)
```

And inside `.streamlit/`:

```
config.toml
secrets.toml.example
secrets.toml                    (local only - must be in .gitignore)
```

If you see duplicates like `app_v2.py` or `app copy.py`, delete them. Push the
deletes:

```bash
git rm app_old.py
git commit -m "Remove old app versions"
git push
```

---

## Part 2: requirements.txt sanity check

Open `requirements.txt`. It must include these lines:

```
streamlit>=1.32,<2.0
streamlit-autorefresh>=1.0.1
pandas>=2.0
numpy>=1.24,<2.0
scikit-learn>=1.3
xgboost>=2.0
lightgbm>=4.0
joblib>=1.3
altair>=5.0
matplotlib>=3.7
seaborn>=0.12
gspread>=6.0
google-auth>=2.27
```

If any of `gspread`, `google-auth`, or `streamlit-autorefresh` is missing,
add it, commit, push. Streamlit Cloud reinstalls dependencies on every push.

---

## Part 3: .gitignore sanity check

Open `.gitignore` and make sure it contains at least:

```
.streamlit/secrets.toml
*.json
__pycache__/
.DS_Store
venv/
.venv/
```

If `secrets.toml` is missing from `.gitignore`, fix it immediately. Then check
whether you ever accidentally pushed it:

```bash
git log --all --full-history -- .streamlit/secrets.toml
```

If anything comes back, your service account credentials are public. Rotate
them: Google Cloud Console -> IAM & Admin -> Service Accounts -> select
your service account -> Keys -> delete the leaked key -> generate a new one.

---

## Part 4: config.toml in the right place

The theme config must live at `.streamlit/config.toml` (note: inside the
`.streamlit/` folder, NOT at the repo root).

```bash
cat .streamlit/config.toml
```

Expected content:

```toml
[theme]
base = "light"
primaryColor = "#F26B1F"
backgroundColor = "#FAF7F2"
secondaryBackgroundColor = "#F5EFE5"
textColor = "#3D2E20"
font = "sans serif"

[server]
headless = true
runOnSave = false

[browser]
gatherUsageStats = false
```

If it's at the repo root, move it:

```bash
mkdir -p .streamlit
mv config.toml .streamlit/config.toml
git add .streamlit/config.toml
git rm config.toml 2>/dev/null
git commit -m "Move config.toml into .streamlit folder"
git push
```

---

## Part 5: Streamlit Cloud Secrets sync (the part that bites)

`.streamlit/secrets.toml` is local-only and never gets pushed (because of
`.gitignore`). For Streamlit Cloud, secrets live in a separate UI. They are
NOT synced automatically.

### Sync your local secrets to Cloud

1. Open `.streamlit/secrets.toml` locally. Select all, copy.
2. Go to https://share.streamlit.io
3. Find `barkley-bites-prediction-model` in your app list.
4. Click the three-dot menu -> **Settings** -> **Secrets**.
5. Paste everything into the text area, replacing whatever was there.
6. Click **Save**.

The app restarts automatically. Wait 30-60 seconds.

### Cloud-specific private_key formatting trap

In your local `secrets.toml`, the private key uses triple double-quotes with
real newlines:

```toml
private_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0...
...many lines...
-----END PRIVATE KEY-----
"""
```

When you paste this into Streamlit Cloud's Secrets text box, **keep the
triple quotes and the real newlines**. The Cloud text box accepts TOML, so
the format is identical to your local file. Do NOT collapse the newlines
into `\n` literals.

The most common Cloud-only failure is a private_key with literal `\n` strings
because someone copy-pasted from a single-line representation. If your
Streamlit Cloud Sheets connection diagnostic shows:

> ❌ private_key has literal backslash-n instead of real newlines

go back to step 1 above and re-paste preserving the newlines.

### Quick way to verify Cloud secrets match local

After saving Cloud secrets, open the live app and click the Live Predictions
tab. If Sheets connects on Cloud the same way it does locally, the secrets
match. If you see the diagnostic panel on Cloud but not locally, look at the
first ❌ row - it tells you exactly which field differs.

---

## Part 6: Cache and deployment freshness

Streamlit Cloud caches aggressively. After pushing new code:

1. Wait 2-4 minutes for the auto-redeploy to finish.
2. Click the three-dot menu on your app -> **Reboot app**. This wipes the
   resource cache (`@st.cache_resource`) and the data cache (`@st.cache_data`).
3. In your browser, hard-refresh the page (Cmd-Shift-R on Mac, Ctrl-Shift-R
   on Windows). Better, open the live URL in an incognito window to bypass
   browser cache entirely.

If after a reboot you still see old behavior, check the **Manage app** ->
**Logs** in Streamlit Cloud. Look at the top of the log for the line:

> Cloning repository...
> Cloned: riyaravishankar/barkley_bites_prediction_model (main, abc1234)

The `abc1234` is the commit hash. If it's not your latest commit, the redeploy
didn't pick up your push - this happens occasionally. Fix:

1. Push an empty commit to force a redeploy:
   ```bash
   git commit --allow-empty -m "Force redeploy"
   git push
   ```
2. Or in Streamlit Cloud, three-dot menu -> **Reboot**.

---

## Part 7: API enablement on Google Cloud

For Sheets to work, both APIs must be enabled in your Google Cloud project:

1. Open https://console.cloud.google.com
2. Select your project (`barkley-bites-lifecycle` or whatever you named it).
3. Top search bar: "Google Sheets API" -> should say **Enabled**.
4. Top search bar: "Google Drive API" -> should say **Enabled**.

If either says "Enable" instead of "Manage", click Enable. Wait 30 seconds
for it to propagate, then reboot your Streamlit Cloud app.

---

## Part 8: Service account sharing

The service account email (the one in your secrets, looks like
`barkley-streamlit@project-id.iam.gserviceaccount.com`) must be a sharer on
your Sheet.

1. Open your Google Sheet.
2. Click Share (top right).
3. The sharer list must include the service account email with **Editor**
   role.
4. If it's not there, paste the email, set Editor, uncheck Notify, click
   Share.

The service account email is printed by the Streamlit app's connection
diagnostic panel (step 4 of the diagnostic) - copy it from there.

---

## Part 9: End-to-end smoke test

After everything above is green, run this sequence to confirm the whole
pipeline works on Cloud:

1. Open the live app: https://barkley-bites-prediction-model.streamlit.app/
2. **Live Predictions tab** loads without a warning banner.
3. The Registrations counter shows your real count.
4. Click "Score new registrations" - the action completes without errors.
5. Switch to **Quick Predict** tab - the form renders and predicts.
6. Click ☰ Tools -> **Model Performance** - the chart renders.
7. Back to main, click ☰ Tools -> **Batch CSV Upload** - the upload area
   appears.

If any step fails, go back to the relevant Part above.

---

## Part 10: Production-ready checklist

Before handing off to Schuyler, all of these should be true:

- [ ] Local app boots clean: `streamlit run app.py`
- [ ] `python3 diagnose_sheets.py` reports all green
- [ ] Cloud app loads and Sheets connects without the diagnostic panel
- [ ] Quick Predict works on Cloud regardless of Sheets state
- [ ] Apps Script email alert script is deployed and triggered every minute
- [ ] Apps Script Web App is deployed for website submissions
- [ ] Web App URL works (returns JSON health check when opened in browser)
- [ ] Test form submission lands in Registrations tab
- [ ] Streamlit auto-refresh picks it up and adds to Predictions tab
- [ ] High-priority test triggers an email to riya@utdallas.edu
- [ ] `secrets.toml` is NOT in the repo (`git log` returns nothing for it)
- [ ] No duplicate `app_old.py` or `app_v1.py` files
- [ ] `requirements.txt` has gspread, google-auth, streamlit-autorefresh
- [ ] `.streamlit/config.toml` is in the right place
- [ ] Theme is consistent (no black banner, no black buttons)
