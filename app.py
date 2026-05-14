"""
Barkley Bites Pet Lifecycle Detection
Streamlit App v3 (Light Beige theme + verbose Sheets diagnostics)
FIX-IT-FIVE | DCP Phase 2 | Riya Ravishankar

What this version changes over v2:
- Light luxury beige palette throughout. No more dark banner or black buttons.
- Sheets connection logic exposes every step's failure with actionable detail.
- "Reset connection cache" button to bypass Streamlit's resource cache.
- Same model, same features, same Google Sheets schema as v2.

Run locally: streamlit run app.py
Deploy:      Push to GitHub, Streamlit Cloud auto-redeploys.
"""

import os
import json
import secrets as pysecrets
import string
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
    GSPREAD_IMPORT_ERROR = None
except Exception as e:
    GSPREAD_AVAILABLE = False
    GSPREAD_IMPORT_ERROR = str(e)

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except Exception:
    AUTOREFRESH_AVAILABLE = False


# ============================================================
# Page config (must be first Streamlit call)
# ============================================================
st.set_page_config(
    page_title="Barkley Bites | Pet Lifecycle Model",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# LIGHT LUXURY BEIGE PALETTE
# All previous BLACK/WHITE references map into this palette so the
# whole app shifts to a consistent warm light theme.
# ============================================================
BG_PAGE       = "#FAF7F2"   # main page warm off-white
BG_CARD       = "#F5EFE5"   # cards, banners, sections - cream
BG_HIGHLIGHT  = "#EDE4D3"   # deeper beige for emphasis
BORDER        = "#E0D5C0"   # soft tan border
TEXT_DARK     = "#3D2E20"   # warm dark brown (replaces BLACK)
TEXT_MID      = "#6B5B45"   # warm taupe
TEXT_LIGHT    = "#9B8B73"   # light taupe
ACCENT        = "#F26B1F"   # brand orange (kept punchy as accent)
ACCENT_DARK   = "#C97A4A"   # softer terracotta for hover
ACCENT_LIGHT  = "#FCE5D4"   # orange light (cards / soft fills)
SUCCESS_BG    = "#EFF3E8"   # muted sage cream
WARN_BG       = "#FAEDD9"   # warm amber cream
DANGER_BG     = "#F5DDD8"   # muted brick cream
SUCCESS_LINE  = "#7A9B6E"
WARN_LINE     = "#D49A4E"
DANGER_LINE   = "#B85040"

# Legacy aliases so the rest of the code reads naturally
ORANGE        = ACCENT
ORANGE_LIGHT  = ACCENT_LIGHT
BLACK         = TEXT_DARK     # all "BLACK" text becomes warm dark brown
WHITE         = BG_PAGE
CREAM         = BG_CARD
GRAY_DARK     = TEXT_MID
GRAY_MID      = TEXT_LIGHT
GRAY_LIGHT    = BORDER
GREEN         = SUCCESS_LINE
BLUE          = "#5B7A9B"
RED           = DANGER_LINE


# ============================================================
# CSS - rebuilt around the beige palette
# Every previous dark-bg surface now sits on cream/beige.
# ============================================================
st.markdown(f"""
<style>
#MainMenu, footer, header {{visibility: hidden;}}

html, body, [class*="css"] {{
    font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
    color: {TEXT_DARK};
    background-color: {BG_PAGE};
}}

.stApp {{
    background-color: {BG_PAGE};
}}

h1 {{ color: {TEXT_DARK} !important; font-weight: 800 !important; letter-spacing: -0.5px; }}
h2 {{ color: {TEXT_DARK} !important; font-weight: 700 !important; font-size: 1.6rem !important; }}
h3 {{ color: {TEXT_DARK} !important; font-weight: 600 !important; font-size: 1.25rem !important; }}
h4 {{ color: {TEXT_DARK} !important; font-weight: 600 !important; font-size: 1.05rem !important; }}
p, li, .stMarkdown {{ font-size: 16px !important; line-height: 1.55 !important; color: {TEXT_DARK} !important; }}

[data-testid="stMetricValue"] {{
    font-size: 2.4rem !important; font-weight: 800 !important; color: {ACCENT} !important;
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.95rem !important; font-weight: 600 !important; color: {TEXT_MID} !important;
}}

/* Primary buttons */
.stButton > button {{
    background-color: {ACCENT}; color: #FFFFFF;
    border: none; border-radius: 8px;
    padding: 0.55rem 1.4rem; font-weight: 700; font-size: 16px;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(61, 46, 32, 0.08);
}}
.stButton > button:hover {{
    background-color: {ACCENT_DARK}; transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(61, 46, 32, 0.12);
}}

/* Download buttons (no longer black) */
.stDownloadButton > button {{
    background-color: {TEXT_DARK}; color: {BG_PAGE};
    border: none; border-radius: 8px;
    padding: 0.55rem 1.4rem; font-weight: 700; font-size: 15px;
    box-shadow: 0 1px 2px rgba(61, 46, 32, 0.08);
}}
.stDownloadButton > button:hover {{
    background-color: {ACCENT}; color: #FFFFFF;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px; border-bottom: 2px solid {BORDER};
    background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent; color: {TEXT_MID};
    font-weight: 600; font-size: 16px;
    padding: 10px 20px; border-radius: 6px 6px 0 0;
}}
.stTabs [aria-selected="true"] {{
    background: {ACCENT_LIGHT}; color: {TEXT_DARK};
    border-bottom: 3px solid {ACCENT};
}}

/* Form labels */
.stSelectbox label, .stNumberInput label, .stTextInput label,
.stSlider label, .stDateInput label, .stFileUploader label,
.stRadio label {{
    font-weight: 600 !important; color: {TEXT_DARK} !important; font-size: 15px !important;
}}

/* Inputs */
.stTextInput input, .stNumberInput input, .stDateInput input,
.stSelectbox > div > div, .stTextArea textarea {{
    background-color: #FFFFFF !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_DARK} !important;
}}

/* Brand banner - cream instead of black */
.brand-banner {{
    background-color: {BG_CARD};
    color: {TEXT_DARK};
    padding: 1.4rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.0rem;
    border-left: 8px solid {ACCENT};
    border: 1px solid {BORDER};
    box-shadow: 0 1px 3px rgba(61, 46, 32, 0.06);
}}
.brand-banner h1 {{ color: {TEXT_DARK} !important; margin: 0; font-size: 1.9rem; }}
.brand-banner p {{ color: {TEXT_MID} !important; margin: 0.4rem 0 0 0; font-size: 16px !important; }}

/* Prediction card */
.pred-card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-left: 6px solid {ACCENT};
    border-radius: 12px;
    padding: 1.8rem 2rem;
    margin: 1rem 0;
    box-shadow: 0 1px 3px rgba(61, 46, 32, 0.06);
}}
.pred-card-title {{
    color: {TEXT_MID}; font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.4rem;
}}
.pred-card-value {{
    color: {ACCENT}; font-size: 2.2rem; font-weight: 800; margin: 0.3rem 0;
}}
.pred-card-action {{
    color: {TEXT_DARK}; font-size: 16px; font-weight: 500; line-height: 1.55;
}}

/* Why-explanation box */
.why-box {{
    background-color: {BG_HIGHLIGHT};
    border: 1px solid {BORDER};
    border-left: 4px solid {ACCENT};
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
}}
.why-box-title {{
    color: {TEXT_MID}; font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0.4rem;
}}
.why-box-text {{
    color: {TEXT_DARK}; font-size: 15px; line-height: 1.55; margin: 0;
}}

/* Notification boxes */
.info-box {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-left: 4px solid {ACCENT};
    padding: 1rem 1.25rem;
    border-radius: 8px;
    margin: 1rem 0;
    font-size: 15px;
    color: {TEXT_DARK};
}}
.warn-box {{
    background-color: {WARN_BG};
    border: 1px solid {BORDER};
    border-left: 4px solid {WARN_LINE};
    padding: 1rem 1.25rem;
    border-radius: 8px;
    margin: 1rem 0;
    font-size: 15px;
    color: {TEXT_DARK};
}}
.danger-box {{
    background-color: {DANGER_BG};
    border: 1px solid {BORDER};
    border-left: 4px solid {DANGER_LINE};
    padding: 1rem 1.25rem;
    border-radius: 8px;
    margin: 1rem 0;
    font-size: 15px;
    color: {TEXT_DARK};
}}
.success-box {{
    background-color: {SUCCESS_BG};
    border: 1px solid {BORDER};
    border-left: 4px solid {SUCCESS_LINE};
    padding: 1rem 1.25rem;
    border-radius: 8px;
    margin: 1rem 0;
    font-size: 15px;
    color: {TEXT_DARK};
}}

/* Empty-state cards */
.empty-state {{
    background-color: {BG_CARD};
    border: 2px dashed {BORDER};
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    color: {TEXT_MID};
}}
.empty-state-icon {{ font-size: 3rem; }}
.empty-state-text {{
    font-size: 17px; font-weight: 600; color: {TEXT_MID}; margin-top: 0.5rem;
}}
.empty-state-sub {{
    font-size: 14px; color: {TEXT_LIGHT}; margin-top: 0.5rem;
}}

/* Footer */
.footer {{
    text-align: center; padding: 2rem 0 1rem 0;
    color: {TEXT_LIGHT}; font-size: 13px;
    border-top: 1px solid {BORDER}; margin-top: 3rem;
}}

/* Diagnostic rows */
.diag-row {{
    display: flex; align-items: flex-start; padding: 6px 0;
    border-bottom: 1px solid {BORDER};
    font-size: 14px;
}}
.diag-icon {{ width: 32px; flex-shrink: 0; font-size: 16px; }}
.diag-text {{ flex: 1; color: {TEXT_DARK}; }}
.diag-detail {{
    color: {TEXT_MID}; font-size: 13px; margin-top: 2px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    word-break: break-word;
}}

/* Popover button (Tools menu) */
div[data-testid="stPopover"] button {{
    background-color: {BG_CARD} !important;
    color: {TEXT_DARK} !important;
    border: 1px solid {BORDER} !important;
}}
div[data-testid="stPopover"] button:hover {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
}}

/* Expander */
div[data-testid="stExpander"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}

/* Dataframe */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
</style>
""", unsafe_allow_html=True)


# ============================================================
# Load model + summary data
# ============================================================
@st.cache_resource
def load_model():
    base = os.path.dirname(os.path.abspath(__file__))
    art = os.path.join(base, "artifacts")
    return {
        "model": joblib.load(os.path.join(art, "lifecycle_model.pkl")),
        "encoders": joblib.load(os.path.join(art, "feature_encoders.pkl")),
        "target_encoder": joblib.load(os.path.join(art, "target_encoder.pkl")),
        "config": joblib.load(os.path.join(art, "model_config.pkl")),
        "metrics": json.load(open(os.path.join(art, "metrics.json"))),
    }


@st.cache_data
def load_summary_data():
    base = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(base, "data")
    snapshots = pd.read_csv(os.path.join(data, "pet_lifecycle_dataset.csv"),
                            usecols=["lifecycle_event"])
    products = pd.read_csv(os.path.join(data, "products.csv"))
    return {
        "class_distribution": snapshots["lifecycle_event"].value_counts(),
        "total_rows": len(snapshots),
        "products": products,
    }


bundle = load_model()
summary = load_summary_data()
metrics = bundle["metrics"]
class_names = bundle["config"]["class_names"]
feature_columns = bundle["config"]["feature_columns"]


# ============================================================
# Action playbook
# ============================================================
ACTION_PLAYBOOK = {
    "STABLE":            {"icon": "🟢", "headline": "No action needed",
                          "detail": "This pet is on a healthy ordering cadence. Continue normal communications.",
                          "priority": "normal"},
    "NEW_PUPPY":         {"icon": "🐶", "headline": "Trigger Puppy Welcome Flow",
                          "detail": "Send the 5-email Puppy Welcome series. Apply 15% off Puppy Salmon Starter for 30 days.",
                          "priority": "high"},
    "BIRTHDAY":          {"icon": "🎂", "headline": "Send birthday treat coupon",
                          "detail": "Schedule a birthday card 7 days before with a free pup-cake voucher and UGC photo prompt.",
                          "priority": "normal"},
    "SENIOR_TRANSITION": {"icon": "🦴", "headline": "Recommend senior recipe",
                          "detail": "Send a personalized email with the Senior recipe and a free nutrition consult.",
                          "priority": "normal"},
    "RE_ENGAGE":         {"icon": "💌", "headline": "Send empathetic check-in",
                          "detail": "Soft check-in: \"Just checking on Bella, need a pause or recipe change?\" No discount yet.",
                          "priority": "normal"},
    "TRAVEL_PAUSE":      {"icon": "✈️", "headline": "Offer to hold next delivery",
                          "detail": "Proactively offer to pause the next delivery. Pre-load a 10% return-from-trip credit.",
                          "priority": "normal"},
    "PET_LOSS":          {"icon": "🕊️", "headline": "Pause all marketing 30 days",
                          "detail": "MANUAL REVIEW REQUIRED. Pause automated marketing for 30 days. Schuyler sends a handwritten card.",
                          "priority": "high"},
    "FIRST_TIME":        {"icon": "🌟", "headline": "Trigger Free Trial flow",
                          "detail": "Send the Free Trial nudge email at day 3 and day 7. Onboarding QR code video in welcome materials.",
                          "priority": "normal"},
}


def build_why(pred_class: str, features: dict) -> str:
    age = features.get("pet_age_years", 0)
    dob_days = features.get("days_to_birthday", 999)
    signup = features.get("days_since_signup", 0)
    last = features.get("days_since_last_order", -1)
    n_orders = features.get("n_orders", 0)
    max_int = features.get("max_interval_days", 0)
    resumed = features.get("had_resumption", 0)

    if pred_class == "STABLE":
        return (f"This pet has placed {n_orders} orders, with the most recent one "
                f"{last} days ago. The ordering pattern is regular and within the "
                f"expected weekly cadence, so no special action is needed.")
    if pred_class == "NEW_PUPPY":
        return (f"The pet is {age:.1f} years old (under 1 year, classified as a puppy) "
                f"and the customer signed up {signup} days ago. Puppies need a tailored "
                f"welcome flow and puppy-specific nutrition recommendations.")
    if pred_class == "BIRTHDAY":
        return (f"The pet's birthday is in {dob_days} days, which falls inside the "
                f"14-day birthday window. This is the trigger for a birthday treat "
                f"coupon and UGC photo prompt.")
    if pred_class == "SENIOR_TRANSITION":
        return (f"The pet is {age:.1f} years old, crossing into the senior life stage "
                f"(7+ years). Senior dogs benefit from a recipe switch and a free "
                f"nutrition consult.")
    if pred_class == "RE_ENGAGE":
        return (f"It has been {last} days since the last order, which sits in the "
                f"14 to 60 day re-engagement window. The customer is lapsing but "
                f"hasn't resumed ordering yet. An empathetic check-in (no discount) "
                f"is the right move.")
    if pred_class == "TRAVEL_PAUSE":
        return (f"The order history shows a long gap of {max_int} days "
                f"followed by a recent resumption "
                f"({'orders detected after the gap' if resumed else 'pattern suggests travel'}). "
                f"This matches a travel pause, not a churn signal.")
    if pred_class == "PET_LOSS":
        return (f"It has been {last} days since the last order with no resumption "
                f"signal, and the gap is significantly longer than this customer's "
                f"normal cadence. This is a possible pet loss event. **Manual review "
                f"required before any action.**")
    if pred_class == "FIRST_TIME":
        return (f"The customer signed up {signup} days ago and has placed 0 orders. "
                f"They need a free-trial nudge and the onboarding video to get to the "
                f"first order.")
    return "No explanation available for this class."


SIZE_BY_BREED = {
    "French Bulldog": "small", "Labrador": "large", "Golden Retriever": "large",
    "German Shepherd": "large", "Poodle": "medium", "Bulldog": "medium",
    "Beagle": "small", "Rottweiler": "large", "Dachshund": "small",
    "German Shorthaired Pointer": "large", "Pembroke Welsh Corgi": "small",
    "Australian Shepherd": "medium", "Yorkshire Terrier": "small",
    "Cavalier King Charles": "small", "Boxer": "large", "Shih Tzu": "small",
    "Mixed Breed": "medium",
}


def auto_compute_features(simple_inputs: dict) -> dict:
    pet_age = simple_inputs["pet_age"]
    breed = simple_inputs["breed"]
    birthday = simple_inputs["birthday"]
    n_orders = simple_inputs["n_orders"]
    days_since_signup = simple_inputs["days_since_signup"]
    days_since_last = simple_inputs["days_since_last"]
    weight = simple_inputs["weight"]

    if pet_age < 1:
        life_stage = "puppy"
    elif pet_age < 7:
        life_stage = "adult"
    else:
        life_stage = "senior"

    size = SIZE_BY_BREED.get(breed, "medium")

    today = datetime.now().date()
    if isinstance(birthday, str):
        try:
            birthday = datetime.fromisoformat(birthday).date()
        except Exception:
            birthday = today + timedelta(days=100)
    bday_this_year = birthday.replace(year=today.year)
    if bday_this_year < today:
        bday_this_year = bday_this_year.replace(year=today.year + 1)
    days_to_birthday = (bday_this_year - today).days

    if n_orders == 0:
        avg_interval = 0.0
        interval_stddev = 0.0
        max_interval = 0
        had_resumption = 0
        orders_last_7d = 0
        orders_last_30d = 0
        orders_last_90d = 0
        total_spend = 0.0
        avg_order_value = 0.0
        avg_rating = 0.0
    else:
        avg_interval = max(7.0, days_since_signup / max(n_orders, 1))
        interval_stddev = 2.5
        max_interval = max(int(avg_interval) + 4, days_since_last)
        had_resumption = 1 if (days_since_last < 10 and max_interval > 20) else 0
        orders_last_7d = 1 if days_since_last <= 7 else 0
        orders_last_30d = 0 if days_since_last > 30 else min(n_orders, max(1, int(30 / max(avg_interval, 1))))
        orders_last_90d = 0 if days_since_last > 90 else min(n_orders, max(1, int(90 / max(avg_interval, 1))))
        avg_order_value = 45.0
        total_spend = n_orders * avg_order_value
        avg_rating = 4.5

    return {
        "breed": breed, "size": size, "pet_age_years": pet_age,
        "life_stage": life_stage, "weight_lbs": weight, "allergy": "none",
        "activity_level": "medium", "city": "Dallas", "signup_source": "Instagram",
        "days_since_signup": days_since_signup, "n_orders": n_orders,
        "days_since_last_order": days_since_last if n_orders > 0 else -1,
        "avg_interval_days": round(avg_interval, 2),
        "interval_stddev": interval_stddev,
        "max_interval_days": max_interval, "had_resumption": had_resumption,
        "orders_last_7d": orders_last_7d, "orders_last_30d": orders_last_30d,
        "orders_last_90d": orders_last_90d, "total_spend": total_spend,
        "avg_order_value": avg_order_value, "avg_rating": avg_rating,
        "days_to_birthday": days_to_birthday,
    }


def predict_row(feature_dict: dict):
    X_row = {}
    for col in feature_columns:
        val = feature_dict.get(col, 0)
        if col in bundle["encoders"]:
            le = bundle["encoders"][col]
            try:
                if str(val) in le.classes_:
                    X_row[col] = le.transform([str(val)])[0]
                else:
                    X_row[col] = 0
            except Exception:
                X_row[col] = 0
        else:
            X_row[col] = val
    X_in = pd.DataFrame([X_row])[feature_columns]
    pred_idx = bundle["model"].predict(X_in)[0]
    pred_class = bundle["target_encoder"].inverse_transform([pred_idx])[0]
    proba = bundle["model"].predict_proba(X_in)[0]
    return pred_class, proba


def predict_batch(df: pd.DataFrame):
    required = ["pet_name", "breed", "pet_age", "weight", "birthday",
                "days_since_signup", "n_orders", "days_since_last"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, f"Missing columns: {', '.join(missing)}"

    if df["birthday"].dtype == object:
        try:
            df["birthday"] = pd.to_datetime(df["birthday"]).dt.date
        except Exception as e:
            return None, f"Could not parse birthday column: {e}"

    predictions, confidences, actions, whys = [], [], [], []
    for _, row in df.iterrows():
        try:
            simple = {
                "pet_name": row["pet_name"], "breed": row["breed"],
                "pet_age": float(row["pet_age"]), "weight": float(row["weight"]),
                "birthday": row["birthday"],
                "days_since_signup": int(row["days_since_signup"]),
                "n_orders": int(row["n_orders"]),
                "days_since_last": int(row["days_since_last"]),
            }
            features = auto_compute_features(simple)
            pred_class, proba = predict_row(features)
            predictions.append(pred_class)
            confidences.append(round(float(proba.max()), 3))
            actions.append(ACTION_PLAYBOOK[pred_class]["headline"])
            whys.append(build_why(pred_class, features))
        except Exception as e:
            predictions.append("ERROR")
            confidences.append(0.0)
            actions.append(f"Could not predict: {e}")
            whys.append("")

    result = df.copy()
    result["predicted_lifecycle"] = predictions
    result["confidence"] = confidences
    result["recommended_action"] = actions
    result["why_explanation"] = whys
    return result, None


# ============================================================
# Google Sheets - verbose connection with per-step diagnostics
# ============================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _gen_prediction_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "PRED-" + "".join(pysecrets.choice(alphabet) for _ in range(6))


def diagnose_sheets_connection():
    """
    Walk every step of the Sheets connection and return:
        (sheet_object_or_None, list_of_(status, message, detail))

    status is one of: "ok", "warn", "error".
    No caching, no swallowed exceptions. Always re-runs.
    """
    msgs = []

    # Step 1: gspread imported?
    if not GSPREAD_AVAILABLE:
        msgs.append(("error", "gspread library not installed",
                     f"Import error: {GSPREAD_IMPORT_ERROR}. "
                     "Run: pip install gspread google-auth streamlit-autorefresh"))
        return None, msgs
    msgs.append(("ok", f"gspread imported (version {gspread.__version__})", None))

    # Step 2: secrets.toml present and readable
    try:
        _ = st.secrets  # forces secrets to load
        msgs.append(("ok", "st.secrets is accessible", None))
    except FileNotFoundError as e:
        msgs.append(("error", "secrets.toml not found",
                     f"Looking for .streamlit/secrets.toml. Error: {e}"))
        return None, msgs
    except Exception as e:
        msgs.append(("error", "st.secrets failed to load", str(e)))
        return None, msgs

    # Step 3: required top-level keys
    try:
        has_sheet_id = "sheet_id" in st.secrets
    except Exception as e:
        msgs.append(("error", "Could not check st.secrets keys", str(e)))
        return None, msgs

    if not has_sheet_id:
        msgs.append(("error", "sheet_id missing from secrets.toml",
                     'Add: sheet_id = "YOUR_SHEET_ID_HERE" at the top of secrets.toml'))
        return None, msgs

    sheet_id = st.secrets["sheet_id"]
    if not sheet_id or sheet_id == "PASTE-YOUR-GOOGLE-SHEET-ID-HERE":
        msgs.append(("error", "sheet_id is empty or still the placeholder", None))
        return None, msgs
    msgs.append(("ok", f"sheet_id present ({sheet_id[:10]}...{sheet_id[-4:]})", None))

    if "gcp_service_account" not in st.secrets:
        msgs.append(("error", "[gcp_service_account] section missing in secrets.toml",
                     "Make sure your secrets.toml has a [gcp_service_account] section "
                     "with all the fields from your downloaded JSON."))
        return None, msgs
    msgs.append(("ok", "[gcp_service_account] section found", None))

    # Step 4: service account fields
    sa = dict(st.secrets["gcp_service_account"])
    required_fields = [
        "type", "project_id", "private_key_id", "private_key",
        "client_email", "client_id", "auth_uri", "token_uri",
    ]
    sa_missing = [f for f in required_fields if f not in sa or not str(sa.get(f, "")).strip()]
    if sa_missing:
        msgs.append(("error",
                     f"Service account is missing or has empty fields: {', '.join(sa_missing)}",
                     None))
        return None, msgs
    msgs.append(("ok", f"All {len(required_fields)} required service account fields present", None))
    msgs.append(("ok", f"Service account email: {sa['client_email']}", None))

    # Step 5: private_key formatting
    pk = sa["private_key"]
    if "BEGIN PRIVATE KEY" not in pk:
        msgs.append(("error", "private_key missing the BEGIN marker",
                     "It must include -----BEGIN PRIVATE KEY----- on its own line."))
        return None, msgs
    if "END PRIVATE KEY" not in pk:
        msgs.append(("error", "private_key missing the END marker", None))
        return None, msgs

    newline_count = pk.count("\n")
    literal_slash_n = "\\n" in pk
    if literal_slash_n and newline_count < 5:
        msgs.append(("error",
                     "private_key has literal backslash-n instead of real newlines",
                     "Fix: in secrets.toml, wrap the key in triple double-quotes and "
                     "use real line breaks (press Enter), not the two characters \\n."))
        return None, msgs
    if newline_count < 20:
        msgs.append(("warn",
                     f"private_key has only {newline_count} newlines (expected 25+)",
                     "Make sure you pasted the entire key from the JSON file."))
    else:
        msgs.append(("ok", f"private_key has {newline_count} newlines", None))

    # Step 6: build credentials
    try:
        creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
        msgs.append(("ok", "Google credentials object created", None))
    except Exception as e:
        msgs.append(("error", "Could not create Google credentials",
                     f"{type(e).__name__}: {e}. The private_key is most likely corrupted. "
                     "Re-download the JSON from Google Cloud Console and re-paste."))
        return None, msgs

    # Step 7: authorize gspread
    try:
        client = gspread.authorize(creds)
        msgs.append(("ok", "gspread.authorize succeeded", None))
    except Exception as e:
        msgs.append(("error", "gspread.authorize failed",
                     f"{type(e).__name__}: {e}"))
        return None, msgs

    # Step 8: open the sheet
    try:
        sh = client.open_by_key(sheet_id)
        msgs.append(("ok", f'Opened sheet: "{sh.title}"', None))
    except Exception as e:
        err = str(e)
        if "PERMISSION_DENIED" in err or "403" in err:
            msgs.append(("error", "Permission denied when opening the sheet",
                         f"The sheet has not been shared with this service account. "
                         f"Open the sheet, click Share, and add this email as Editor: "
                         f"{sa['client_email']}"))
        elif "404" in err or "Requested entity was not found" in err.lower():
            msgs.append(("error", "Sheet not found",
                         f"sheet_id may be wrong: {sheet_id}. Verify the ID in your URL: "
                         "https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit"))
        elif "API has not been used" in err or "API has not been enabled" in err:
            msgs.append(("error", "Google Sheets/Drive API not enabled",
                         f"Enable both Google Sheets API and Google Drive API for project "
                         f"{sa['project_id']} in Google Cloud Console."))
        else:
            msgs.append(("error", "Could not open sheet", err))
        return None, msgs

    # Step 9: verify tabs
    try:
        tabs = [ws.title for ws in sh.worksheets()]
    except Exception as e:
        msgs.append(("error", "Could not list tabs", str(e)))
        return None, msgs

    msgs.append(("ok", f"Tabs in sheet: {tabs}", None))
    for required_tab in ["Registrations", "Predictions"]:
        if required_tab not in tabs:
            msgs.append(("error",
                         f'Tab "{required_tab}" missing',
                         "Tab names are case-sensitive. Rename exactly."))
            return None, msgs

    msgs.append(("ok", "Both required tabs present", None))
    return sh, msgs


def get_sheet():
    """Returns the sheet object or None. Stashes diagnostics in session_state."""
    sh, msgs = diagnose_sheets_connection()
    st.session_state["_sheet_diagnostics"] = msgs
    return sh


def fetch_registrations() -> pd.DataFrame:
    sh = get_sheet()
    if sh is None:
        return pd.DataFrame()
    try:
        ws = sh.worksheet("Registrations")
        rows = ws.get_all_records()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        st.session_state["_gspread_error"] = str(e)
        return pd.DataFrame()


def fetch_predictions() -> pd.DataFrame:
    sh = get_sheet()
    if sh is None:
        return pd.DataFrame()
    try:
        ws = sh.worksheet("Predictions")
        rows = ws.get_all_records()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        st.session_state["_gspread_error"] = str(e)
        return pd.DataFrame()


def append_prediction_rows(prediction_rows: list):
    sh = get_sheet()
    if sh is None or not prediction_rows:
        return False
    try:
        ws = sh.worksheet("Predictions")
        header = ws.row_values(1)
        values = [[str(row.get(col, "")) for col in header] for row in prediction_rows]
        ws.append_rows(values, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.session_state["_gspread_error"] = str(e)
        return False


def _safe_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default


def _safe_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def _safe_date(x):
    if not x or x == "":
        return None
    try:
        return pd.to_datetime(x).date()
    except Exception:
        return None


def registration_to_features(reg: dict) -> dict:
    breed = reg.get("pet_breed") or reg.get("breed") or "Mixed Breed"
    bday = _safe_date(reg.get("pet_birthday"))
    if bday is not None:
        today = datetime.now().date()
        pet_age = round((today - bday).days / 365.25, 2)
        if pet_age < 0:
            pet_age = 0.1
    else:
        pet_age = _safe_float(reg.get("pet_age_years"), 4.0)
        bday = datetime.now().date() + timedelta(days=100)

    weight = _safe_float(reg.get("pet_weight_lbs"), 35.0)
    reg_ts = _safe_date(reg.get("timestamp"))
    if reg_ts is None:
        days_since_signup = 0
    else:
        days_since_signup = max(0, (datetime.now().date() - reg_ts).days)

    n_orders = _safe_int(reg.get("n_orders"), 0)
    last_order = _safe_date(reg.get("last_order_date"))
    if last_order is not None:
        days_since_last = max(0, (datetime.now().date() - last_order).days)
    else:
        days_since_last = days_since_signup if n_orders > 0 else 0

    return {
        "pet_name": reg.get("pet_name", ""), "breed": breed,
        "pet_age": pet_age, "weight": weight, "birthday": bday,
        "days_since_signup": days_since_signup, "n_orders": n_orders,
        "days_since_last": days_since_last,
    }


def score_all_new_registrations():
    registrations = fetch_registrations()
    predictions = fetch_predictions()
    if registrations.empty:
        return 0, 0, predictions

    if "is_duplicate" in registrations.columns:
        registrations = registrations[
            registrations["is_duplicate"].astype(str).str.upper() != "TRUE"
        ]

    def snapshot_key(reg):
        return f"{reg.get('n_orders','')}|{reg.get('last_order_date','')}|{reg.get('pet_weight_lbs','')}"

    last_pred_by_id = {}
    if not predictions.empty and "registration_id" in predictions.columns:
        try:
            predictions["_ts"] = pd.to_datetime(predictions["timestamp"], errors="coerce")
            latest = predictions.sort_values("_ts").drop_duplicates(
                "registration_id", keep="last")
            for _, p in latest.iterrows():
                last_pred_by_id[p["registration_id"]] = p.get("snapshot_key", "")
        except Exception:
            pass

    to_append = []
    n_skipped = 0
    for _, reg in registrations.iterrows():
        reg_id = reg.get("registration_id", "")
        key_now = snapshot_key(reg)
        if reg_id in last_pred_by_id and last_pred_by_id[reg_id] == key_now:
            n_skipped += 1
            continue
        try:
            simple = registration_to_features(reg.to_dict())
            features = auto_compute_features(simple)
            pred_class, proba = predict_row(features)
            action = ACTION_PLAYBOOK[pred_class]
            why = build_why(pred_class, features)
            owner_name = f"{reg.get('owner_first_name','').strip()} {reg.get('owner_last_name','').strip()}".strip()
            to_append.append({
                "prediction_id": _gen_prediction_id(),
                "registration_id": reg_id,
                "pet_name": reg.get("pet_name", ""),
                "owner_name": owner_name,
                "owner_email": reg.get("owner_email", ""),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "lifecycle_state": pred_class,
                "confidence": round(float(proba.max()), 3),
                "recommended_action": action["headline"],
                "why_explanation": why,
                "alert_priority": action["priority"],
                "alert_sent": "FALSE",
                "n_orders_at_prediction": simple["n_orders"],
                "days_since_last_order_at_prediction": simple["days_since_last"],
                "snapshot_key": key_now,
            })
        except Exception as e:
            st.session_state["_score_error"] = f"Failed to score {reg_id}: {e}"

    if to_append:
        append_prediction_rows(to_append)
    return len(to_append), n_skipped, fetch_predictions()


# ============================================================
# Header + Tools popover
# ============================================================
top_left, top_right = st.columns([6, 1])
with top_left:
    st.markdown(f"""
    <div class="brand-banner">
        <h1>🐾 Barkley Bites Pet Lifecycle Model</h1>
        <p>Classify 8 lifecycle states for every customer-pet pair. Auto-trigger the right marketing action.</p>
    </div>
    """, unsafe_allow_html=True)

with top_right:
    st.write("")
    with st.popover("☰ Tools", use_container_width=True):
        st.markdown("**Open another view**")
        if st.button("📤 Batch CSV Upload", use_container_width=True, key="nav_batch"):
            st.session_state["view"] = "batch"; st.rerun()
        if st.button("📊 Model Performance", use_container_width=True, key="nav_perf"):
            st.session_state["view"] = "performance"; st.rerun()
        if st.button("📈 Summary Stats", use_container_width=True, key="nav_stats"):
            st.session_state["view"] = "stats"; st.rerun()
        if st.button("📖 Instructions", use_container_width=True, key="nav_instr"):
            st.session_state["view"] = "instructions"; st.rerun()
        st.markdown("---")
        if st.button("⬅️ Back to main", use_container_width=True, key="nav_main"):
            st.session_state["view"] = "main"; st.rerun()

if "view" not in st.session_state:
    st.session_state["view"] = "main"
view = st.session_state["view"]


# ============================================================
# Diagnostic panel - rendered when Sheets is not connected
# ============================================================
def render_sheets_diagnostics(msgs):
    icon = {"ok": "✅", "warn": "⚠️", "error": "❌"}
    rows_html = ""
    for status, message, detail in msgs:
        detail_html = f'<div class="diag-detail">{detail}</div>' if detail else ""
        rows_html += f"""
        <div class="diag-row">
            <div class="diag-icon">{icon.get(status, '·')}</div>
            <div class="diag-text">
                <strong>{message}</strong>
                {detail_html}
            </div>
        </div>
        """
    st.markdown(f"""
    <div class="warn-box">
        <strong>Google Sheets is not connected.</strong>
        Step-by-step diagnostic below. The first ❌ row is the failure point.
    </div>
    <div style="background:{BG_CARD}; border:1px solid {BORDER};
                border-radius:10px; padding:1rem 1.25rem; margin:1rem 0;">
        {rows_html}
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# VIEW: MAIN (Live Predictions + Quick Predict)
# ============================================================
def render_main():
    tab_live, tab_quick = st.tabs([
        "🔴 Live Predictions",
        "🎯 Quick Predict (manual)",
    ])

    with tab_live:
        sh = get_sheet()
        msgs = st.session_state.get("_sheet_diagnostics", [])

        if sh is None:
            render_sheets_diagnostics(msgs)
            colA, colB = st.columns([1, 5])
            with colA:
                if st.button("🔄 Re-test connection", use_container_width=True):
                    st.cache_resource.clear()
                    st.cache_data.clear()
                    st.rerun()
            with colB:
                st.markdown(
                    f'<div style="color:{TEXT_MID}; font-size:14px; padding-top:0.55rem;">'
                    'Click after you edit secrets.toml or share the sheet.'
                    '</div>',
                    unsafe_allow_html=True,
                )
            return

        # Show OK diagnostics on first load only (collapsed)
        if msgs and any(s == "warn" for s, _, _ in msgs):
            with st.expander("⚠️ Connection warnings (click for detail)"):
                render_sheets_diagnostics(msgs)

        if AUTOREFRESH_AVAILABLE:
            st_autorefresh(interval=30 * 1000, key="live_predictions_refresh")

        ctrl1, ctrl2, _ = st.columns([2, 2, 6])
        with ctrl1:
            if st.button("🔄 Score new registrations", use_container_width=True):
                with st.spinner("Reading registrations and scoring new ones..."):
                    n_new, n_skip, _ = score_all_new_registrations()
                st.session_state["_last_score_msg"] = (
                    f"Scored {n_new} new predictions. Skipped {n_skip} unchanged."
                )
                st.rerun()
        with ctrl2:
            view_mode = st.radio(
                "Display", ["Latest per pet", "Full history"],
                horizontal=True, label_visibility="collapsed",
            )

        if "_last_score_msg" in st.session_state:
            st.markdown(
                f'<div class="success-box">{st.session_state["_last_score_msg"]}</div>',
                unsafe_allow_html=True,
            )

        if not st.session_state.get("_auto_scored_once"):
            with st.spinner("Looking for new registrations..."):
                score_all_new_registrations()
            st.session_state["_auto_scored_once"] = True

        predictions_df = fetch_predictions()
        registrations_df = fetch_registrations()

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Registrations", f"{len(registrations_df):,}")
        with c2: st.metric("Predictions made", f"{len(predictions_df):,}")
        with c3:
            high = 0
            if not predictions_df.empty and "alert_priority" in predictions_df.columns:
                high = int((predictions_df["alert_priority"].astype(str) == "high").sum())
            st.metric("High priority", f"{high:,}")
        with c4:
            st.metric("Auto-refresh", "Every 30 s" if AUTOREFRESH_AVAILABLE else "Manual")

        st.markdown("---")

        if predictions_df.empty:
            st.markdown(f"""
            <div class="empty-state">
                <div class="empty-state-icon">🕒</div>
                <div class="empty-state-text">No predictions yet</div>
                <div class="empty-state-sub">Add a registration to the Google Sheet
                    and click "Score new registrations".</div>
            </div>
            """, unsafe_allow_html=True)
            return

        try:
            predictions_df["_ts"] = pd.to_datetime(
                predictions_df["timestamp"], errors="coerce")
            predictions_df = predictions_df.sort_values("_ts", ascending=False)
        except Exception:
            pass

        if view_mode == "Latest per pet":
            display_df = predictions_df.drop_duplicates("registration_id", keep="first")
        else:
            display_df = predictions_df

        display_cols = [
            "timestamp", "pet_name", "owner_name", "lifecycle_state",
            "confidence", "recommended_action", "why_explanation",
            "alert_priority", "alert_sent", "registration_id",
        ]
        present_cols = [c for c in display_cols if c in display_df.columns]

        st.markdown(f"#### {view_mode} ({len(display_df):,} rows)")
        st.dataframe(display_df[present_cols], use_container_width=True,
                     hide_index=True, height=420)

        st.markdown("---")
        st.markdown("#### Drill in on one pet")
        if not display_df.empty:
            options = [
                f"{r['pet_name']} | {r.get('owner_name','')} | {r['lifecycle_state']}"
                for _, r in display_df.iterrows()
            ]
            choice = st.selectbox("Select a recent prediction", options, key="drill_sel")
            idx = options.index(choice)
            row = display_df.iloc[idx]
            action = ACTION_PLAYBOOK.get(row["lifecycle_state"], {})
            st.markdown(f"""
            <div class="pred-card">
                <div class="pred-card-title">Predicted Lifecycle State for {row['pet_name']}</div>
                <div class="pred-card-value">{action.get('icon','')} {row['lifecycle_state']}</div>
                <div style="margin-top:1rem; padding-top:1rem; border-top:1px solid {BORDER};">
                    <div class="pred-card-title" style="margin-top:0;">Recommended action</div>
                    <div style="font-weight:700; font-size:1.15rem; color:{TEXT_DARK}; margin:0.4rem 0;">
                        {row.get('recommended_action','')}
                    </div>
                    <div class="pred-card-action">{action.get('detail','')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="why-box">
                <div class="why-box-title">🤔 Why this recommendation</div>
                <div class="why-box-text">{row.get('why_explanation','')}</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_quick:
        st.markdown("### Predict a single pet manually")
        st.markdown(
            '<div class="info-box">Quick check without going through the Google Sheet. '
            'Use this for demos and ad-hoc testing.</div>',
            unsafe_allow_html=True,
        )

        col_input, col_result = st.columns([3, 2], gap="large")
        with col_input:
            c1, c2 = st.columns(2)
            with c1:
                pet_name = st.text_input("Pet name", value="Bella")
                breed = st.selectbox("Breed", options=sorted(list(SIZE_BY_BREED.keys())))
                pet_age = st.slider("Pet age (years)", 0.1, 16.0, 4.0, 0.1)
                weight = st.slider("Pet weight (lbs)", 4.0, 130.0, 50.0, 1.0)
            with c2:
                birthday = st.date_input(
                    "Pet birthday",
                    value=datetime.now().date() + timedelta(days=100),
                    min_value=datetime.now().date() - timedelta(days=365 * 16),
                )
                days_since_signup = st.number_input("Days since signup", 0, 1000, 90)
                n_orders = st.number_input("Total orders placed", 0, 200, 8)
                days_since_last = st.number_input(
                    "Days since last order", 0, 500, 7,
                    help="If they've never ordered, enter 0 and set Total orders to 0.",
                )
            predict_btn = st.button("🔮 Predict lifecycle state", use_container_width=True)

        with col_result:
            if predict_btn:
                simple = {
                    "pet_name": pet_name, "breed": breed,
                    "pet_age": pet_age, "weight": weight, "birthday": birthday,
                    "days_since_signup": days_since_signup,
                    "n_orders": n_orders, "days_since_last": days_since_last,
                }
                features = auto_compute_features(simple)
                pred_class, proba = predict_row(features)
                action = ACTION_PLAYBOOK[pred_class]
                why = build_why(pred_class, features)

                st.markdown(f"""
                <div class="pred-card">
                    <div class="pred-card-title">Predicted Lifecycle State for {pet_name}</div>
                    <div class="pred-card-value">{action['icon']} {pred_class}</div>
                    <div style="margin-top:1rem; padding-top:1rem; border-top:1px solid {BORDER};">
                        <div class="pred-card-title" style="margin-top:0;">Recommended action</div>
                        <div style="font-weight:700; font-size:1.15rem; color:{TEXT_DARK}; margin:0.4rem 0;">
                            {action['headline']}
                        </div>
                        <div class="pred-card-action">{action['detail']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="why-box">
                    <div class="why-box-title">🤔 Why this recommendation</div>
                    <div class="why-box-text">{why}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### Class probabilities")
                proba_df = pd.DataFrame({
                    "Class": bundle["target_encoder"].inverse_transform(np.arange(len(proba))),
                    "Probability": proba,
                }).sort_values("Probability", ascending=False)
                chart = alt.Chart(proba_df).mark_bar().encode(
                    x=alt.X("Probability:Q", scale=alt.Scale(domain=[0, 1]),
                            axis=alt.Axis(format=".0%")),
                    y=alt.Y("Class:N", sort="-x", axis=alt.Axis(labelFontSize=13)),
                    color=alt.condition(
                        alt.datum.Class == pred_class,
                        alt.value(ACCENT), alt.value(BORDER),
                    ),
                    tooltip=["Class", alt.Tooltip("Probability:Q", format=".1%")],
                ).properties(height=320)
                st.altair_chart(chart, use_container_width=True)

                single_csv = pd.DataFrame([{
                    "pet_name": pet_name, "breed": breed, "pet_age": pet_age,
                    "weight": weight, "birthday": birthday,
                    "days_since_signup": days_since_signup,
                    "n_orders": n_orders, "days_since_last": days_since_last,
                    "predicted_lifecycle": pred_class,
                    "confidence": round(float(proba.max()), 3),
                    "recommended_action": action["headline"],
                    "why_explanation": why,
                }]).to_csv(index=False)
                st.download_button(
                    "⬇️ Save this prediction (CSV)", data=single_csv,
                    file_name=f"{pet_name}_prediction.csv", mime="text/csv",
                )
            else:
                st.markdown(f"""
                <div class="empty-state">
                    <div class="empty-state-icon">🐾</div>
                    <div class="empty-state-text">
                        Fill in the 8 fields and click
                        <span style="color:{ACCENT};">"Predict lifecycle state"</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ============================================================
# VIEW: BATCH CSV UPLOAD
# ============================================================
def render_batch():
    st.markdown("### 📤 Batch CSV Upload")
    st.markdown(
        '<div class="info-box">Upload a CSV with customer data. The model predicts a '
        'lifecycle state for every row, then you download the results.</div>',
        unsafe_allow_html=True,
    )

    with st.expander("📋 What columns should my CSV have?"):
        st.markdown("""
Your CSV must have these 8 columns (any order):

- `pet_name` - text
- `breed` - text (e.g. Labrador, Golden Retriever)
- `pet_age` - decimal (years)
- `weight` - decimal (lbs)
- `birthday` - date (YYYY-MM-DD)
- `days_since_signup` - integer
- `n_orders` - integer
- `days_since_last` - integer
""")

    today = datetime.now().date()
    sample = pd.DataFrame([
        {"pet_name": "Bella", "breed": "Labrador", "pet_age": 4.0, "weight": 60,
         "birthday": (today + timedelta(days=100)).isoformat(),
         "days_since_signup": 200, "n_orders": 18, "days_since_last": 7},
        {"pet_name": "Max", "breed": "French Bulldog", "pet_age": 0.5, "weight": 15,
         "birthday": (today + timedelta(days=180)).isoformat(),
         "days_since_signup": 5, "n_orders": 1, "days_since_last": 2},
        {"pet_name": "Luna", "breed": "Golden Retriever", "pet_age": 11.0, "weight": 65,
         "birthday": (today + timedelta(days=200)).isoformat(),
         "days_since_signup": 400, "n_orders": 30, "days_since_last": 120},
        {"pet_name": "Cooper", "breed": "Beagle", "pet_age": 7.0, "weight": 25,
         "birthday": (today + timedelta(days=300)).isoformat(),
         "days_since_signup": 300, "n_orders": 22, "days_since_last": 8},
        {"pet_name": "Daisy", "breed": "Poodle", "pet_age": 3.0, "weight": 35,
         "birthday": (today + timedelta(days=10)).isoformat(),
         "days_since_signup": 150, "n_orders": 12, "days_since_last": 6},
    ])
    st.download_button("⬇️ Download sample CSV", data=sample.to_csv(index=False),
                       file_name="sample_pets.csv", mime="text/csv")

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is None:
        return

    try:
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Loaded {len(df)} rows from {uploaded_file.name}")
        with st.expander("👀 Preview uploaded data"):
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)

        if st.button("🚀 Run predictions on all rows", use_container_width=True):
            with st.spinner(f"Predicting lifecycle for {len(df)} pets..."):
                result, error = predict_batch(df)
            if error:
                st.error(f"❌ {error}")
                return
            st.success(f"✅ Predicted {len(result)} pets successfully")
            pred_counts = result["predicted_lifecycle"].value_counts().reset_index()
            pred_counts.columns = ["Lifecycle State", "Count"]
            chart = alt.Chart(pred_counts).mark_bar(color=ACCENT).encode(
                x=alt.X("Count:Q"),
                y=alt.Y("Lifecycle State:N", sort="-x"),
                tooltip=["Lifecycle State", "Count"],
            ).properties(height=min(350, 40 * len(pred_counts) + 60))
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download all results (CSV)", data=result.to_csv(index=False),
                file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv", use_container_width=True,
            )
    except Exception as e:
        st.error(f"❌ Could not read CSV: {e}")


# ============================================================
# VIEW: MODEL PERFORMANCE
# ============================================================
def render_performance():
    st.markdown("### 📊 Model Performance")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Test Accuracy", f"{metrics['test_accuracy']:.1%}")
    with m2: st.metric("Weighted F1", f"{metrics['test_weighted_f1']:.3f}")
    with m3: st.metric("Training Samples", "400,000")
    with m4: st.metric("Test Samples", "100,000")

    st.markdown("---")
    st.markdown("### Baselines (so the accuracy has context)")
    st.markdown(
        '<div class="info-box">A model that always predicts the most common class '
        '(STABLE) gets ~43%. A random model gets ~24%. Our model gets '
        f'<b>{metrics["test_accuracy"]:.1%}</b>.</div>',
        unsafe_allow_html=True,
    )
    base_df = pd.DataFrame([
        {"Approach": "Random guess", "Accuracy": metrics["baselines"]["random_stratified_acc"]},
        {"Approach": "Always predict STABLE", "Accuracy": metrics["baselines"]["always_predict_majority_acc"]},
        {"Approach": "Our model (XGBoost)", "Accuracy": metrics["test_accuracy"]},
    ])
    base_chart = alt.Chart(base_df).mark_bar().encode(
        x=alt.X("Accuracy:Q", scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format=".0%")),
        y=alt.Y("Approach:N", sort=None),
        color=alt.condition(
            alt.datum.Approach == "Our model (XGBoost)",
            alt.value(ACCENT), alt.value(BORDER),
        ),
        tooltip=["Approach", alt.Tooltip("Accuracy:Q", format=".1%")],
    ).properties(height=200)
    st.altair_chart(base_chart, use_container_width=True)

    st.markdown("---")
    st.markdown("### Per-class F1")
    per_class_df = pd.DataFrame([
        {"Class": k, "F1": v} for k, v in metrics["per_class_f1"].items()
    ]).sort_values("F1", ascending=False)
    cls_chart = alt.Chart(per_class_df).mark_bar(color=ACCENT).encode(
        x=alt.X("F1:Q", scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("Class:N", sort="-x"),
        tooltip=["Class", alt.Tooltip("F1:Q", format=".3f")],
    ).properties(height=320)
    st.altair_chart(cls_chart, use_container_width=True)

    st.markdown("### Confusion matrix")
    cm_path = os.path.join(os.path.dirname(__file__), "artifacts", "confusion_matrix.png")
    if os.path.exists(cm_path):
        st.image(cm_path, use_container_width=True)


# ============================================================
# VIEW: SUMMARY STATS
# ============================================================
def render_stats():
    st.markdown("### 📈 Training Data Summary")
    st.markdown(
        '<div class="info-box">High-level shape of the training data. The raw dataset '
        'is delivered separately, not exposed in the app.</div>',
        unsafe_allow_html=True,
    )

    s1, s2, s3 = st.columns(3)
    with s1: st.metric("Total Samples", f"{summary['total_rows']:,}")
    with s2: st.metric("Features", "23")
    with s3: st.metric("Products", f"{len(summary['products'])}")

    st.markdown("---")
    st.markdown("### Lifecycle class distribution")
    class_dist = summary["class_distribution"].reset_index()
    class_dist.columns = ["Class", "Count"]
    cd_chart = alt.Chart(class_dist).mark_bar(color=ACCENT).encode(
        x=alt.X("Class:N", sort="-y", axis=alt.Axis(labelAngle=-25)),
        y=alt.Y("Count:Q"),
        tooltip=["Class", "Count"],
    ).properties(height=320)
    st.altair_chart(cd_chart, use_container_width=True)

    st.markdown("---")
    st.markdown("### Barkley Bites product catalog")
    st.dataframe(summary["products"], use_container_width=True, hide_index=True)


# ============================================================
# VIEW: INSTRUCTIONS
# ============================================================
def render_instructions():
    st.markdown("### 📖 Instructions")
    st.markdown(f"""
This app reads new customer registrations from a Google Sheet, predicts the
right lifecycle state for each pet using a trained XGBoost model, and writes the
result back to the same sheet. Schuyler reads predictions in the sheet. The app
is also where you can run quick manual predictions or upload a CSV.

#### 🟢 For Schuyler

1. Open the live URL of this app on any device.
2. The **Live Predictions** tab is your home view. It shows the latest
   prediction for every customer.
3. Each row tells you:
   - **Lifecycle state** (one of 8 states like NEW_PUPPY or PET_LOSS)
   - **Recommended action** (a one-line marketing instruction)
   - **Why this recommendation** (plain-English logic)
4. **High priority** rows (NEW_PUPPY, PET_LOSS) also trigger an automatic email
   alert.
5. The model never sends marketing on its own. It only recommends. You decide
   whether to act, especially on PET_LOSS rows.

#### 🔧 For the technical owner

**Architecture**

- Source of truth: Google Sheet with `Registrations` and `Predictions` tabs.
- Trigger: the website pushes a new row to `Registrations` on each signup.
- Scoring: this Streamlit app reads `Registrations`, scores changed rows, and
  appends to `Predictions`.
- Email alerts: a Google Apps Script attached to the sheet sends an email for
  every new high-priority row.

**To change the model:** re-train with `scripts/train_model.py`. New artifacts
overwrite the ones in `artifacts/`. Push. Streamlit Cloud redeploys.

**To change recommended actions or why-explanations:** edit `ACTION_PLAYBOOK`
and `build_why()` in `app.py`. Push.

See `SETUP_GUIDE.md` in the repo for full setup details.
""")


# ============================================================
# Router
# ============================================================
if view == "main":
    render_main()
elif view == "batch":
    render_batch()
elif view == "performance":
    render_performance()
elif view == "stats":
    render_stats()
elif view == "instructions":
    render_instructions()
else:
    render_main()


st.markdown(f"""
<div class="footer">
<strong>Barkley Bites Pet Lifecycle Model</strong> · Built by FIX-IT-FIVE · DCP Phase 2 · Spring 2026<br>
Champion model: XGBoost trained on 400,000 samples · {metrics['test_accuracy']:.1%} accuracy on 100,000 hold-out
</div>
""", unsafe_allow_html=True)
