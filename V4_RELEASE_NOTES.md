# v4 release notes

What's new since v3, in plain terms.

---

## 1. Quick Predict bug - FIXED

**Cause:** `with tab_live:` had a `return` statement when Sheets failed to
connect. Python's `return` exits the whole `render_main()` function, so the
`with tab_quick:` block never executed. The Quick Predict tab was visible but
empty.

**Fix:** Restructured `render_main()` to use two sub-renderers
(`render_live_predictions_connected` and `render_live_predictions_disconnected`)
called via an `if/else` instead of early return. Both tabs now always render.
Quick Predict is now resilient to Sheets failures.

This is the most important change in v4. Drop in the new `app.py` and the bug
is gone.

---

## 2. Production website integration - ADDED

Two new files in `web_integration/`:

- `website_webapp.gs` - Apps Script deployed as a public Web App. Accepts POST
  with a JSON body, writes to the Registrations tab, generates registration
  IDs, detects duplicates.
- `registration_form.html` - drop-in HTML signup form. Same beige palette as
  the Streamlit app. Vanilla JS, no framework dependencies. The Cursor team
  can use it as-is, embed just the form into their existing page, or take only
  the JavaScript pattern.

Setup walkthrough in `web_integration/WEBSITE_INTEGRATION.md`.

The architecture is now:

```
[Website registration form]
        v POST JSON
[Apps Script Web App] -> [Google Sheet Registrations]
                              v polled every 30 s
                       [Streamlit app] -> [Predictions tab]
                                              v new row trigger
                                       [Email alert script]
```

---

## 3. UI polish

- Tab content area now has explicit `padding-top: 1rem` so there's less
  blank space below the tabs.
- Block container padding tightened to remove a chunk of dead space at the
  top of the page.
- `max-width: 1300px` on the block container so very wide screens don't
  stretch the layout out of proportion.

---

## 4. Deployment cleanup - DOCUMENTED

`STREAMLIT_CLOUD_CHECKLIST.md` is a 10-part walkthrough covering:

- Repo structure sanity (no duplicate app files)
- requirements.txt completeness
- .gitignore protections
- config.toml placement
- **Streamlit Cloud Secrets sync (the most common Cloud-only failure)**
- Cache and deployment freshness
- API enablement
- Service account sharing
- End-to-end smoke test
- Production-ready handoff checklist

Use it whenever Cloud behaves differently from local.

---

## Files in this drop

```
barkley_v4/
├── app.py                                  Replaces existing app.py
├── STREAMLIT_CLOUD_CHECKLIST.md            New - cloud verification
├── V4_RELEASE_NOTES.md                     (this file)
└── web_integration/
    ├── website_webapp.gs                   Paste into Apps Script
    ├── registration_form.html              Hand to Cursor team
    └── WEBSITE_INTEGRATION.md              Step-by-step deployment guide
```

## What to push to GitHub

| File | Repo destination |
|---|---|
| `app.py` | root (replaces existing) |
| `STREAMLIT_CLOUD_CHECKLIST.md` | root |
| `web_integration/` (whole folder) | root |

Commit message suggestion:

> Quick Predict resilience fix, website webapp integration, cloud checklist

After push, follow the Part 5 sync instructions in
`STREAMLIT_CLOUD_CHECKLIST.md` to make sure Streamlit Cloud has the right
secrets.

---

## What to do in Apps Script (one-time)

1. Open Google Sheet -> Extensions -> Apps Script.
2. Add new file: `website_webapp` (paste in `website_webapp.gs`).
3. Save.
4. Deploy -> New deployment -> Web app -> Execute as: Me, Who has access:
   Anyone.
5. Copy the Web app URL.
6. Test by running `testRegistration` from the editor - a test row should
   appear in the Registrations tab.

---

## What to hand the Cursor team

1. The Web app URL from the Apps Script deployment.
2. `web_integration/registration_form.html` as a reference.
3. `WEBSITE_INTEGRATION.md` Step 2 (the three integration options).

They paste the URL into the website code where the JS posts to.

---

## Verification order

Before declaring the project done:

1. Local: `streamlit run app.py`. Click Quick Predict tab. Form renders even
   if Sheets is broken.
2. Push to GitHub. Wait for Streamlit Cloud to redeploy.
3. Open Cloud URL. Same Quick Predict test.
4. Deploy the Apps Script Web App. Run `testRegistration`. New row in sheet.
5. Open Cloud URL again, click "Score new registrations" on Live Predictions
   tab. Prediction lands in the Predictions tab.
6. Cursor team integrates the form. Submit one real form. End-to-end works.

You're done.
