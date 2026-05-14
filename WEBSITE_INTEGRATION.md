# Website integration - production guide

End-to-end path: **Website form -> Google Sheet (Registrations) -> Streamlit
app scores it -> Predictions tab gets new row -> email alert if high priority.**

This guide walks through wiring up the production website to the Google Sheet.
The Cursor team's HTML/CSS/JS site is the upstream, the Google Sheet stays
the source of truth in the middle, and the Streamlit app is the downstream.

---

## What you're deploying

Two new things in your Apps Script project, plus one change in the website:

1. **`website_webapp.gs`** - a new Apps Script file that accepts POST requests
   from the website and writes them into the Registrations tab.
2. **Web App deployment** - exposes a public URL the website can POST to.
3. **`registration_form.html`** - a drop-in form (or just the form structure
   for the Cursor team to restyle) that knows how to POST to that URL.

Architecture diagram:

```
[Customer fills out form on website]
            |
            | POST  (Content-Type: text/plain, body: JSON)
            v
[Apps Script Web App URL  https://script.google.com/macros/s/.../exec]
            |
            | Validates, generates registration_id, detects duplicates
            v
[Google Sheet  ->  Registrations tab gets a new row]
            |
            | Streamlit app polls every 30 seconds
            v
[Streamlit reads new row, runs XGBoost, appends to Predictions tab]
            |
            | Apps Script email script runs every minute
            v
[High-priority predictions trigger an email to alert recipient]
```

---

## Step 1: Deploy the Web App (5 min)

1. Open your Google Sheet -> Extensions -> Apps Script.
2. In the file list on the left, click `+` -> Script. Name it
   `website_webapp`.
3. Paste the entire contents of `website_webapp.gs` into the editor.
4. Click Save.
5. **Deploy -> New deployment**:
   - Click the gear icon next to "Select type" -> choose **Web app**.
   - Description: "Barkley Bites registration intake v1"
   - Execute as: **Me** (your Google account)
   - Who has access: **Anyone**
   - Click Deploy.
6. Google asks you to authorize. Click through the "isn't verified" page
   (Advanced -> Go to {project} (unsafe)). This is expected for personal
   scripts.
7. Copy the **Web app URL**. It looks like:
   `https://script.google.com/macros/s/AKfycbx.../exec`

This URL is what the website POSTs to. Save it somewhere safe.

### Verifying the deployment

Open the Web app URL in a browser. You should see a JSON health check:

```json
{"success":true,"service":"Barkley Bites Registration Intake","status":"live", ...}
```

If you see that, the endpoint is live. If you see a permission error, your
deployment is set to "Only me" instead of "Anyone" - redeploy with Anyone.

### Test the write path before involving the website

Inside the Apps Script editor:

1. Select `testRegistration` from the function dropdown at the top.
2. Click Run (the play icon).
3. Open your Google Sheet -> Registrations tab.

A new row should appear with a `BB-XXXXXX` registration ID and a test pet.
This proves the Web App can write to the sheet end-to-end.

---

## Step 2: Hand the form to the Cursor team

Three options, pick whichever matches the website's stack:

### Option A: Drop in the full HTML file

The simplest path. Open `registration_form.html` and:

1. Change the line `const WEB_APP_URL = "PASTE_..."` to the URL from Step 1.
2. Save the file into the website project as `signup.html` or any other name
   the Cursor team prefers.
3. Link to it from the main page.

The included CSS uses the same beige palette as the Streamlit app, so the
brand stays consistent across the website and the lifecycle model.

### Option B: Embed just the form + script blocks into an existing page

If the website already has its own design and the Cursor team only needs the
data plumbing:

1. Copy the `<form>...</form>` block from `registration_form.html` into the
   existing signup page.
2. Copy the `<script>...</script>` block at the bottom (including the
   submission handler and the WEB_APP_URL constant).
3. Restyle the form freely. Keep the `name=` attribute on every input
   exact - those map directly to Google Sheet columns and must not change.

### Option C: Just plug in the fetch() call

If the Cursor team already has a form built and just needs the submit logic:

```javascript
async function submitRegistration(payload) {
  const response = await fetch(WEB_APP_URL, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { "Content-Type": "text/plain;charset=utf-8" },
    redirect: "follow"
  });
  return await response.json();
}
```

The `text/plain` content type is intentional. It makes the request a "simple"
CORS request so the browser does not send an OPTIONS preflight (which Apps
Script Web Apps cannot respond to). The body is still JSON, parsed manually
by the Apps Script.

The payload shape the Web App expects:

```json
{
  "owner_first_name": "Jane",
  "owner_last_name": "Doe",
  "owner_email": "jane@example.com",
  "owner_phone": "555-0100",
  "owner_city": "Dallas",
  "pet_name": "Bella",
  "pet_breed": "Labrador",
  "pet_birthday": "2023-06-15",
  "pet_age_years": "",
  "pet_weight_lbs": "62",
  "pet_sex": "Female",
  "health_conditions": "",
  "signup_source": "Website"
}
```

Response on success:

```json
{
  "success": true,
  "registration_id": "BB-A7F3K9",
  "is_duplicate": "FALSE",
  "message": "Registration recorded successfully"
}
```

Response on failure:

```json
{
  "success": false,
  "error": "Invalid JSON body: ..."
}
```

---

## Step 3: End-to-end test (after the website goes live)

Do these in sequence and you've verified the production pipeline.

1. **Submit a real form** on the website using a fake email.
2. **Open the Google Sheet -> Registrations tab.** A new row should appear
   within 1-2 seconds with a `BB-XXXXXX` registration ID.
3. **Open the live Streamlit app.** Within 30 seconds (auto-refresh) the
   "Registrations" metric on the Live Predictions tab should tick up by 1.
4. **Click "Score new registrations"** (or wait for the next auto-refresh).
   A new row appears in the Sheet's Predictions tab with the lifecycle state.
5. **If the predicted state is NEW_PUPPY or PET_LOSS**, an email arrives at
   the configured alert recipient within 60 seconds.
6. **In the Streamlit app's Live Predictions table**, the new pet shows up
   with its predicted state, recommended action, and why-explanation.

---

## Updating the Web App later

If you change anything inside `website_webapp.gs`:

1. Save in the Apps Script editor.
2. Deploy -> **Manage deployments** -> the pencil edit icon next to your
   deployment.
3. Set "Version" to "New version".
4. Click Deploy.

The URL stays the same across versions, so the website does not need an
update. The next request hits the new code.

---

## Security notes

The Web App URL is technically public - anyone with the URL can POST to it.
Two cheap defenses are baked into `website_webapp.gs`:

1. **SHARED_SECRET** (optional). Set a non-empty value at the top of
   `website_webapp.gs`, and put the same value in `SHARED_SECRET` inside the
   website's JavaScript. Requests without that secret are rejected.
2. **Duplicate detection.** Rapid repeated submissions from the same
   email + pet name get flagged `is_duplicate = TRUE`, and the Streamlit app
   skips them when scoring.

For a true production setup you would also want a CAPTCHA on the website form
to stop automated spam. That is outside the scope of this deliverable but
easy to add (Google reCAPTCHA v3 is free and a single script tag).

---

## What can go wrong, and how to spot it

| Symptom | Likely cause | Fix |
|---|---|---|
| Network error in the browser console | WEB_APP_URL is wrong or the deployment is "Only me" | Redeploy with access set to Anyone, copy the new URL |
| CORS error in the browser console | The website is sending `Content-Type: application/json` | Change to `Content-Type: text/plain;charset=utf-8` |
| Form submits OK but no row appears | The Apps Script wrote to a different sheet | Confirm the Apps Script project is bound to the right sheet (open from Extensions menu of the correct sheet) |
| Row appears but Streamlit shows 0 predictions | `is_duplicate = TRUE` on every row | Check duplicate logic; clear duplicate rows if needed |
| `Authorization required` on first call | Web App was redeployed and needs re-auth | Open Web App URL in browser; click through the auth flow once |
| Tab name not found error | Tab renamed | Restore the exact name `Registrations` (case-sensitive) |
