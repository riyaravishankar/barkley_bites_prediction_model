"""
Barkley Bites Pet Lifecycle Detection
Simplified Streamlit App
FIX-IT-FIVE | DCP Phase 2 | Riya Ravishankar

Three features:
  1. Simple 8-field prediction form (no stddev or technical features)
  2. Batch CSV upload - predict lifecycle for many customers at once
  3. Download results as CSV

Run locally:  streamlit run app.py
Deploy:       Push to GitHub, connect to share.streamlit.io
"""

import os
import json
import io
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="Barkley Bites | Pet Lifecycle Model",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============ Brand colors ============
ORANGE = "#F26B1F"
ORANGE_LIGHT = "#FCE5D4"
BLACK = "#0E0E0E"
WHITE = "#FFFFFF"
CREAM = "#F8F4EF"
GRAY_DARK = "#2D2D2D"
GRAY_MID = "#777777"
GRAY_LIGHT = "#E8E8E8"

# ============ CSS ============
st.markdown(f"""
<style>
    #MainMenu, footer, header {{visibility: hidden;}}
    html, body, [class*="css"] {{
        font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
        color: {BLACK};
    }}
    h1 {{ color: {BLACK} !important; font-weight: 800 !important; letter-spacing: -0.5px; }}
    h2 {{ color: {BLACK} !important; font-weight: 700 !important; font-size: 1.6rem !important; }}
    h3 {{ color: {BLACK} !important; font-weight: 600 !important; font-size: 1.25rem !important; }}
    p, li, .stMarkdown {{ font-size: 16px !important; line-height: 1.55 !important; color: {BLACK} !important; }}
    [data-testid="stMetricValue"] {{ font-size: 2.4rem !important; font-weight: 800 !important; color: {ORANGE} !important; }}
    [data-testid="stMetricLabel"] {{ font-size: 0.95rem !important; font-weight: 600 !important; color: {GRAY_DARK} !important; }}
    .stButton > button {{
        background-color: {ORANGE}; color: {WHITE};
        border: none; border-radius: 6px;
        padding: 0.55rem 1.4rem; font-weight: 700; font-size: 16px;
        transition: all 0.15s ease;
    }}
    .stButton > button:hover {{ background-color: {BLACK}; transform: translateY(-1px); }}
    .stDownloadButton > button {{
        background-color: {BLACK}; color: {WHITE};
        border: none; border-radius: 6px;
        padding: 0.55rem 1.4rem; font-weight: 700; font-size: 15px;
    }}
    .stDownloadButton > button:hover {{ background-color: {ORANGE}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; border-bottom: 2px solid {GRAY_LIGHT}; }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent; color: {GRAY_DARK};
        font-weight: 600; font-size: 16px;
        padding: 10px 20px; border-radius: 6px 6px 0 0;
    }}
    .stTabs [aria-selected="true"] {{
        background: {ORANGE_LIGHT}; color: {BLACK};
        border-bottom: 3px solid {ORANGE};
    }}
    .stSelectbox label, .stNumberInput label, .stTextInput label, .stSlider label, .stDateInput label, .stFileUploader label {{
        font-weight: 600 !important; color: {BLACK} !important; font-size: 15px !important;
    }}
    .brand-banner {{
        background-color: {BLACK}; color: {WHITE};
        padding: 1.8rem 2rem; border-radius: 10px;
        margin-bottom: 1.5rem; border-left: 8px solid {ORANGE};
    }}
    .brand-banner h1 {{ color: {WHITE} !important; margin: 0; font-size: 2rem; }}
    .brand-banner p {{ color: {WHITE} !important; margin: 0.4rem 0 0 0; opacity: 0.85; font-size: 16px !important; }}
    .pred-card {{
        background-color: {ORANGE_LIGHT};
        border: 2px solid {ORANGE};
        border-radius: 12px;
        padding: 2rem; margin: 1rem 0;
    }}
    .pred-card-title {{
        color: {GRAY_DARK}; font-size: 14px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;
    }}
    .pred-card-value {{
        color: {ORANGE}; font-size: 2.4rem; font-weight: 800; margin: 0.3rem 0;
    }}
    .pred-card-action {{
        color: {BLACK}; font-size: 16px; font-weight: 500; line-height: 1.5;
    }}
    .info-box {{
        background-color: {CREAM}; border-left: 4px solid {ORANGE};
        padding: 1rem 1.25rem; border-radius: 4px;
        margin: 1rem 0; font-size: 15px;
    }}
    .footer {{
        text-align: center; padding: 2rem 0 1rem 0;
        color: {GRAY_MID}; font-size: 13px;
        border-top: 1px solid {GRAY_LIGHT}; margin-top: 3rem;
    }}
</style>
""", unsafe_allow_html=True)


# ============ Load model + data ============
@st.cache_resource
def load_model():
    base = os.path.dirname(os.path.abspath(__file__))
    art = os.path.join(base, "artifacts")
    return {
        "model":          joblib.load(os.path.join(art, "lifecycle_model.pkl")),
        "encoders":       joblib.load(os.path.join(art, "feature_encoders.pkl")),
        "target_encoder": joblib.load(os.path.join(art, "target_encoder.pkl")),
        "config":         joblib.load(os.path.join(art, "model_config.pkl")),
        "metrics":        json.load(open(os.path.join(art, "metrics.json"))),
    }


@st.cache_data
def load_data():
    base = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(base, "data")
    return {
        "snapshots": pd.read_csv(os.path.join(data, "pet_lifecycle_dataset.csv")),
        "products":  pd.read_csv(os.path.join(data, "products.csv")),
    }


bundle = load_model()
data = load_data()
metrics = bundle["metrics"]
class_names = bundle["config"]["class_names"]
feature_columns = bundle["config"]["feature_columns"]


# ============ Action playbook ============
ACTION_PLAYBOOK = {
    "STABLE":            {"icon": "🟢", "headline": "No action needed",
        "detail": "This pet is on a healthy ordering cadence. Continue normal communications."},
    "NEW_PUPPY":         {"icon": "🐶", "headline": "Trigger Puppy Welcome Flow",
        "detail": "Send the 5-email Puppy Welcome series. Apply 15% off Puppy Salmon Starter for 30 days."},
    "BIRTHDAY":          {"icon": "🎂", "headline": "Send birthday treat coupon",
        "detail": "Schedule a birthday card 7 days before with a free pup-cake voucher and UGC photo prompt."},
    "SENIOR_TRANSITION": {"icon": "🦴", "headline": "Recommend senior recipe",
        "detail": "Send a personalized email with the Senior recipe and a free nutrition consult."},
    "RE_ENGAGE":         {"icon": "💌", "headline": "Send empathetic check-in",
        "detail": "Soft check-in: \"Just checking on Bella, need a pause or recipe change?\" No discount yet."},
    "TRAVEL_PAUSE":      {"icon": "✈️", "headline": "Offer to hold next delivery",
        "detail": "Proactively offer to pause the next delivery. Pre-load a 10% return-from-trip credit."},
    "PET_LOSS":          {"icon": "🕊️", "headline": "Pause all marketing 30 days",
        "detail": "MANUAL REVIEW REQUIRED. Pause automated marketing for 30 days. Schuyler sends a handwritten card."},
    "FIRST_TIME":        {"icon": "🌟", "headline": "Trigger Free Trial flow",
        "detail": "Send the Free Trial nudge email at day 3 and day 7. Onboarding QR code video in welcome materials."},
}


# ============ Feature auto-compute helpers ============
# Reduces the 23 raw features to 8 user-facing ones.
# The other 15 are derived automatically here.

def auto_compute_features(simple_inputs: dict) -> dict:
    """Given 8 user-facing inputs, compute the full 23-feature row."""
    pet_name = simple_inputs["pet_name"]
    breed = simple_inputs["breed"]
    pet_age = simple_inputs["pet_age"]
    weight = simple_inputs["weight"]
    birthday = simple_inputs["birthday"]
    days_since_signup = simple_inputs["days_since_signup"]
    n_orders = simple_inputs["n_orders"]
    days_since_last = simple_inputs["days_since_last"]

    # Derive life_stage from age
    if pet_age < 1:
        life_stage = "puppy"
    elif pet_age < 7:
        life_stage = "adult"
    else:
        life_stage = "senior"

    # Derive size from breed (simple mapping)
    SIZE_BY_BREED = {
        "French Bulldog":"small","Labrador":"large","Golden Retriever":"large",
        "German Shepherd":"large","Poodle":"medium","Bulldog":"medium",
        "Beagle":"small","Rottweiler":"large","Dachshund":"small",
        "German Shorthaired Pointer":"large","Pembroke Welsh Corgi":"small",
        "Australian Shepherd":"medium","Yorkshire Terrier":"small",
        "Cavalier King Charles":"small","Boxer":"large","Shih Tzu":"small",
        "Mixed Breed":"medium",
    }
    size = SIZE_BY_BREED.get(breed, "medium")

    # Days to next birthday
    today = datetime.now().date()
    bday_this_year = birthday.replace(year=today.year)
    if bday_this_year < today:
        bday_this_year = bday_this_year.replace(year=today.year + 1)
    days_to_birthday = (bday_this_year - today).days

    # Auto-derive behavioral features from the simple inputs
    if n_orders == 0:
        # FIRST_TIME signal
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
        # Healthy assumptions for repeat customers
        avg_interval = max(7.0, days_since_signup / max(n_orders, 1))
        interval_stddev = 2.5  # typical
        max_interval = max(int(avg_interval) + 4, days_since_last)
        had_resumption = 1 if (days_since_last < 10 and max_interval > 20) else 0
        # Recency windows: if last order was N days ago, no orders fall inside windows shorter than N
        orders_last_7d  = 1 if days_since_last <= 7  else 0
        orders_last_30d = 0 if days_since_last > 30 else min(n_orders, max(1, int(30 / max(avg_interval, 1))))
        orders_last_90d = 0 if days_since_last > 90 else min(n_orders, max(1, int(90 / max(avg_interval, 1))))
        avg_order_value = 45.0  # typical AOV
        total_spend = n_orders * avg_order_value
        avg_rating = 4.5

    return {
        "breed": breed,
        "size": size,
        "pet_age_years": pet_age,
        "life_stage": life_stage,
        "weight_lbs": weight,
        "allergy": "none",  # defaulted (not user-facing in simple form)
        "activity_level": "medium",  # defaulted
        "city": "Dallas",  # defaulted
        "signup_source": "Instagram",  # defaulted
        "days_since_signup": days_since_signup,
        "n_orders": n_orders,
        "days_since_last_order": days_since_last if n_orders > 0 else -1,
        "avg_interval_days": round(avg_interval, 2),
        "interval_stddev": interval_stddev,
        "max_interval_days": max_interval,
        "had_resumption": had_resumption,
        "orders_last_7d": orders_last_7d,
        "orders_last_30d": orders_last_30d,
        "orders_last_90d": orders_last_90d,
        "total_spend": total_spend,
        "avg_order_value": avg_order_value,
        "avg_rating": avg_rating,
        "days_to_birthday": days_to_birthday,
    }


def predict_row(feature_dict: dict):
    """Encode a single feature dict and return (predicted_class, probabilities)."""
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
    """Given a CSV with simple columns, return df with predictions + actions."""
    # Required simple columns
    required = ["pet_name", "breed", "pet_age", "weight", "birthday",
                "days_since_signup", "n_orders", "days_since_last"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, f"Missing columns: {', '.join(missing)}"

    # Parse birthday if it's a string
    if df["birthday"].dtype == object:
        try:
            df["birthday"] = pd.to_datetime(df["birthday"]).dt.date
        except Exception as e:
            return None, f"Could not parse birthday column: {e}"

    predictions = []
    confidences = []
    actions = []

    for _, row in df.iterrows():
        try:
            simple = {
                "pet_name": row["pet_name"],
                "breed": row["breed"],
                "pet_age": float(row["pet_age"]),
                "weight": float(row["weight"]),
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
        except Exception as e:
            predictions.append("ERROR")
            confidences.append(0.0)
            actions.append(f"Could not predict: {e}")

    result = df.copy()
    result["predicted_lifecycle"] = predictions
    result["confidence"] = confidences
    result["recommended_action"] = actions
    return result, None


# ============ Header ============
st.markdown(f"""
<div class="brand-banner">
    <h1>🐾 Barkley Bites Pet Lifecycle Model</h1>
    <p>Classify 8 lifecycle states for every customer-pet pair. Auto-trigger the right marketing action.</p>
</div>
""", unsafe_allow_html=True)


# ============ Tabs ============
tab_predict, tab_batch, tab_perf, tab_data = st.tabs([
    "🎯 Predict (single)",
    "📤 Predict (batch upload)",
    "📊 Model Performance",
    "🗂️ Data Explorer",
])


# ============ TAB 1: SINGLE PREDICT ============
with tab_predict:
    st.markdown("### Predict a single pet")
    st.markdown(
        '<div class="info-box">Enter just 8 things about a pet. The model handles everything else.</div>',
        unsafe_allow_html=True,
    )

    col_input, col_result = st.columns([3, 2], gap="large")

    with col_input:
        c1, c2 = st.columns(2)
        with c1:
            pet_name = st.text_input("Pet name", value="Bella")
            breed = st.selectbox("Breed", options=sorted([
                "French Bulldog","Labrador","Golden Retriever","German Shepherd","Poodle",
                "Bulldog","Beagle","Rottweiler","Dachshund","German Shorthaired Pointer",
                "Pembroke Welsh Corgi","Australian Shepherd","Yorkshire Terrier",
                "Cavalier King Charles","Boxer","Shih Tzu","Mixed Breed",
            ]))
            pet_age = st.slider("Pet age (years)", 0.1, 16.0, 4.0, 0.1)
            weight = st.slider("Pet weight (lbs)", 4.0, 130.0, 50.0, 1.0)

        with c2:
            birthday = st.date_input(
                "Pet birthday",
                value=datetime.now().date() + timedelta(days=100),
                min_value=datetime.now().date() - timedelta(days=365*16),
            )
            days_since_signup = st.number_input("Days since signup", 0, 1000, 90)
            n_orders = st.number_input("Total orders placed", 0, 200, 8)
            days_since_last = st.number_input("Days since last order", 0, 500, 7,
                help="If they've never ordered, enter 0 and set Total orders to 0.")

        predict_btn = st.button("🔮 Predict lifecycle state", use_container_width=True)

    with col_result:
        if predict_btn:
            simple = {
                "pet_name": pet_name,
                "breed": breed,
                "pet_age": pet_age,
                "weight": weight,
                "birthday": birthday,
                "days_since_signup": days_since_signup,
                "n_orders": n_orders,
                "days_since_last": days_since_last,
            }
            features = auto_compute_features(simple)
            pred_class, proba = predict_row(features)
            action = ACTION_PLAYBOOK[pred_class]

            st.markdown(f"""
            <div class="pred-card">
                <div class="pred-card-title">Predicted Lifecycle State for {pet_name}</div>
                <div class="pred-card-value">{action['icon']} {pred_class}</div>
                <div style="margin-top:1rem; padding-top:1rem; border-top:1px solid {ORANGE};">
                    <div class="pred-card-title" style="margin-top:0;">Recommended action</div>
                    <div style="font-weight:700; font-size:1.15rem; color:{BLACK}; margin:0.4rem 0;">
                        {action['headline']}
                    </div>
                    <div class="pred-card-action">{action['detail']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Confidence chart
            st.markdown("#### Class probabilities")
            proba_df = pd.DataFrame({
                "Class": bundle["target_encoder"].inverse_transform(np.arange(len(proba))),
                "Probability": proba,
            }).sort_values("Probability", ascending=False)

            chart = alt.Chart(proba_df).mark_bar().encode(
                x=alt.X("Probability:Q", scale=alt.Scale(domain=[0,1]), axis=alt.Axis(format=".0%")),
                y=alt.Y("Class:N", sort="-x", axis=alt.Axis(labelFontSize=13)),
                color=alt.condition(
                    alt.datum.Class == pred_class,
                    alt.value(ORANGE),
                    alt.value(GRAY_LIGHT),
                ),
                tooltip=["Class", alt.Tooltip("Probability:Q", format=".1%")]
            ).properties(height=320)
            st.altair_chart(chart, use_container_width=True)

            # Save single prediction as CSV
            single_csv = pd.DataFrame([{
                "pet_name": pet_name,
                "breed": breed,
                "pet_age": pet_age,
                "weight": weight,
                "birthday": birthday,
                "days_since_signup": days_since_signup,
                "n_orders": n_orders,
                "days_since_last": days_since_last,
                "predicted_lifecycle": pred_class,
                "confidence": round(float(proba.max()), 3),
                "recommended_action": action["headline"],
            }]).to_csv(index=False)

            st.download_button(
                "⬇️ Save this prediction (CSV)",
                data=single_csv,
                file_name=f"{pet_name}_prediction.csv",
                mime="text/csv",
            )
        else:
            st.markdown(f"""
            <div style="background-color:{CREAM}; padding:2rem; border-radius:12px; text-align:center; border:2px dashed {GRAY_LIGHT};">
                <div style="font-size:3rem;">🐾</div>
                <div style="font-size:18px; font-weight:600; color:{GRAY_DARK}; margin-top:0.5rem;">
                    Fill in the 8 fields and click<br>
                    <span style="color:{ORANGE};">"Predict lifecycle state"</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ============ TAB 2: BATCH UPLOAD ============
with tab_batch:
    st.markdown("### Predict many pets at once")
    st.markdown(
        f'<div class="info-box">Upload a CSV with your customer data. The model predicts a lifecycle state for every row, then you download the results.</div>',
        unsafe_allow_html=True,
    )

    # Show the expected CSV format
    with st.expander("📋 What columns should my CSV have?"):
        st.markdown("""
        Your CSV must have these 8 columns (any order):

        - `pet_name` - text
        - `breed` - text (e.g. Labrador, Golden Retriever)
        - `pet_age` - decimal (years)
        - `weight` - decimal (lbs)
        - `birthday` - date (YYYY-MM-DD format)
        - `days_since_signup` - integer
        - `n_orders` - integer (total orders)
        - `days_since_last` - integer (days since last order, use 0 if never ordered)

        **Tip:** click the button below to download a sample CSV with 5 example pets.
        """)

        # Sample CSV
        today = datetime.now().date()
        sample = pd.DataFrame([
            {"pet_name":"Bella", "breed":"Labrador",       "pet_age":4.0, "weight":60, "birthday":(today + timedelta(days=100)).isoformat(), "days_since_signup":200, "n_orders":18, "days_since_last":7},
            {"pet_name":"Max",   "breed":"French Bulldog", "pet_age":0.5, "weight":15, "birthday":(today + timedelta(days=180)).isoformat(), "days_since_signup":5,   "n_orders":1,  "days_since_last":2},
            {"pet_name":"Luna",  "breed":"Golden Retriever","pet_age":11.0,"weight":65, "birthday":(today + timedelta(days=200)).isoformat(), "days_since_signup":400, "n_orders":30, "days_since_last":120},
            {"pet_name":"Cooper","breed":"Beagle",         "pet_age":7.0, "weight":25, "birthday":(today + timedelta(days=300)).isoformat(), "days_since_signup":300, "n_orders":22, "days_since_last":8},
            {"pet_name":"Daisy", "breed":"Poodle",         "pet_age":3.0, "weight":35, "birthday":(today + timedelta(days=10)).isoformat(),  "days_since_signup":150, "n_orders":12, "days_since_last":6},
        ])
        st.download_button(
            "⬇️ Download sample CSV",
            data=sample.to_csv(index=False),
            file_name="sample_pets.csv",
            mime="text/csv",
        )

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Drag and drop or click to browse"
    )

    if uploaded_file is not None:
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
                else:
                    st.success(f"✅ Predicted {len(result)} pets successfully")

                    # Distribution of predictions
                    st.markdown("#### 📊 Prediction breakdown")
                    pred_counts = result["predicted_lifecycle"].value_counts().reset_index()
                    pred_counts.columns = ["Lifecycle State", "Count"]
                    breakdown_chart = alt.Chart(pred_counts).mark_bar(color=ORANGE).encode(
                        x=alt.X("Count:Q", axis=alt.Axis(labelFontSize=12)),
                        y=alt.Y("Lifecycle State:N", sort="-x", axis=alt.Axis(labelFontSize=12)),
                        tooltip=["Lifecycle State", "Count"]
                    ).properties(height=min(350, 40 * len(pred_counts) + 60))
                    st.altair_chart(breakdown_chart, use_container_width=True)

                    # Full table
                    st.markdown("#### 📋 All predictions")
                    st.dataframe(result, use_container_width=True, hide_index=True)

                    # Download results
                    st.download_button(
                        "⬇️ Download all results (CSV)",
                        data=result.to_csv(index=False),
                        file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
        except Exception as e:
            st.error(f"❌ Could not read CSV: {e}")
    else:
        st.markdown(f"""
        <div style="background-color:{CREAM}; padding:2.5rem; border-radius:12px; text-align:center; border:2px dashed {GRAY_LIGHT}; margin-top:1rem;">
            <div style="font-size:3rem;">📤</div>
            <div style="font-size:18px; font-weight:600; color:{GRAY_DARK}; margin-top:0.5rem;">
                Drop a CSV file above to predict lifecycle states for many pets at once.
            </div>
            <div style="font-size:14px; color:{GRAY_MID}; margin-top:0.5rem;">
                Don't have one? Download the sample CSV from the expander above.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ============ TAB 3: PERFORMANCE ============
with tab_perf:
    st.markdown("### Model performance summary")

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Test Accuracy", f"{metrics['test_accuracy']:.1%}")
    with m2: st.metric("Weighted F1", f"{metrics['test_weighted_f1']:.3f}")
    with m3: st.metric("Training Samples", "400,000")
    with m4: st.metric("Test Samples", "100,000")

    st.markdown("---")
    st.markdown("### Baselines (so the accuracy has context)")
    st.markdown(
        '<div class="info-box">A model that always predicts the most common class (STABLE) gets 43%. '
        'A random model gets 24%. Our model gets <b>90.6%</b>.</div>',
        unsafe_allow_html=True,
    )

    base_df = pd.DataFrame([
        {"Approach": "Random guess", "Accuracy": metrics["baselines"]["random_stratified_acc"]},
        {"Approach": "Always predict STABLE", "Accuracy": metrics["baselines"]["always_predict_majority_acc"]},
        {"Approach": "Our model (XGBoost)", "Accuracy": metrics["test_accuracy"]},
    ])
    base_chart = alt.Chart(base_df).mark_bar().encode(
        x=alt.X("Accuracy:Q", scale=alt.Scale(domain=[0,1]), axis=alt.Axis(format=".0%")),
        y=alt.Y("Approach:N", sort=None, axis=alt.Axis(labelFontSize=13)),
        color=alt.condition(
            alt.datum.Approach == "Our model (XGBoost)",
            alt.value(ORANGE),
            alt.value(GRAY_LIGHT),
        ),
        tooltip=["Approach", alt.Tooltip("Accuracy:Q", format=".1%")]
    ).properties(height=200)
    st.altair_chart(base_chart, use_container_width=True)

    st.markdown("---")
    st.markdown("### Per-class F1")
    per_class_df = pd.DataFrame([
        {"Class": k, "F1": v} for k, v in metrics["per_class_f1"].items()
    ]).sort_values("F1", ascending=False)
    cls_chart = alt.Chart(per_class_df).mark_bar(color=ORANGE).encode(
        x=alt.X("F1:Q", scale=alt.Scale(domain=[0,1])),
        y=alt.Y("Class:N", sort="-x", axis=alt.Axis(labelFontSize=13)),
        tooltip=["Class", alt.Tooltip("F1:Q", format=".3f")]
    ).properties(height=320)
    st.altair_chart(cls_chart, use_container_width=True)

    st.markdown("### Confusion matrix")
    cm_path = os.path.join(os.path.dirname(__file__), "artifacts", "confusion_matrix.png")
    if os.path.exists(cm_path):
        st.image(cm_path, use_container_width=True)


# ============ TAB 4: DATA EXPLORER ============
with tab_data:
    st.markdown("### Synthetic dataset (500,000 rows)")
    st.markdown(
        '<div class="info-box">Generated with seed=42 for reproducibility. '
        'Anchored to AKC breed popularity, real DFW geography, and realistic dog age distributions.</div>',
        unsafe_allow_html=True,
    )

    s1, s2, s3 = st.columns(3)
    with s1: st.metric("Total Samples", f"{len(data['snapshots']):,}")
    with s2: st.metric("Features", "23")
    with s3: st.metric("Products", f"{len(data['products'])}")

    st.markdown("---")
    st.markdown("### Lifecycle class distribution")
    class_dist = data["snapshots"]["lifecycle_event"].value_counts().reset_index()
    class_dist.columns = ["Class", "Count"]
    cd_chart = alt.Chart(class_dist).mark_bar(color=ORANGE).encode(
        x=alt.X("Class:N", sort="-y", axis=alt.Axis(labelFontSize=13, labelAngle=-25)),
        y=alt.Y("Count:Q", axis=alt.Axis(labelFontSize=12)),
        tooltip=["Class", "Count"]
    ).properties(height=320)
    st.altair_chart(cd_chart, use_container_width=True)

    st.markdown("---")
    st.markdown("### Barkley Bites product catalog")
    st.dataframe(data["products"], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Browse the dataset")
    st.caption("Showing first 100 of 500,000 rows")
    st.dataframe(data["snapshots"].head(100), use_container_width=True, hide_index=True)


# ============ Footer ============
st.markdown(f"""
<div class="footer">
    <strong>Barkley Bites Pet Lifecycle Model</strong> · Built by FIX-IT-FIVE · DCP Phase 2 · Spring 2026<br>
    Champion model: XGBoost trained on 400,000 samples · {metrics['test_accuracy']:.1%} accuracy on 100,000 hold-out
</div>
""", unsafe_allow_html=True)
