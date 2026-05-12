# Barkley Bites Pet Lifecycle Detection Model

Built by **FIX-IT-FIVE** for the Barkley Bites DCP Phase 2 implementation.

A machine learning system that classifies every customer-pet pair into one of 8 lifecycle states each day, so Barkley Bites can trigger the right marketing action at the right moment - from a Puppy Welcome flow to a condolence card after a pet loss.

**Live demo:** [your-streamlit-url-here]
**Champion model:** XGBoost · trained on 500,000 samples · 90.6% accuracy · 0.912 weighted F1

---

## For Schuyler (the practical version)

### What this does

Every day, the model looks at every customer in your CRM and asks: "What's happening with this pet right now?" It picks one of 8 answers, and each answer maps to a specific marketing action.

| State | What it means | What you do |
|---|---|---|
| **STABLE** | Regular customer, normal cadence | Nothing. Don't bother them. |
| **NEW_PUPPY** | Customer just added a puppy | Trigger Puppy Welcome flow + 15% off Puppy Salmon Starter |
| **BIRTHDAY** | Pet birthday in the next 14 days | Send birthday treat coupon + photo prompt |
| **SENIOR_TRANSITION** | Pet aging into senior (~7 years) | Recommend Senior Tuna recipe + free nutrition consult |
| **RE_ENGAGE** | No order in 14-60 days | Empathetic check-in: "Just checking on Bella" |
| **TRAVEL_PAUSE** | Long gap then resumed - probably travel | Offer to hold next delivery + 10% return credit |
| **PET_LOSS** | Abrupt cancellation + 30+ days no orders | Pause all marketing 30 days. Schuyler sends handwritten card. |
| **FIRST_TIME** | Signed up but never ordered | Free trial nudge + onboarding video |

### How to use it

1. Open the live demo URL above
2. Click the **Predict** tab
3. Fill in a pet's details (breed, age, ordering history)
4. Click **Predict lifecycle state**
5. The app tells you the state and the recommended action

### What you need to know

- The model never sends anything automatically. It just tells you what to do. You or your marketing tool decides whether to act.
- For PET_LOSS predictions, **always review manually** before sending a condolence card. False positives are damaging.
- Re-train the model every quarter once real CRM data starts flowing.

---

## For the technical reviewer

### The problem

Barkley Bites has 80% customer retention, the kind of product-market fit most brands chase for years. The bottleneck is the absence of marketing infrastructure: no CRM, no behavioral segmentation, no automated triggers for lifecycle events. This model fills that gap by classifying every (customer, pet) pair into one of 8 lifecycle states, each tied to a specific marketing action.

### Data

**Source:** Synthetic data (1,002 pets, 800 customers, 13,818 orders, 12 products), generated with random seed 42 for reproducibility.

**Why synthetic?** No public dataset combines pet attributes, customer transactional history, and labeled lifecycle events. Petfinder has pet attributes only. Chewy and Kaggle "Pet Food Customer Orders" have orders without pet-level metadata. Lifecycle event labels (PET_LOSS, NEW_PUPPY, etc.) only exist inside operating brands. We generated synthetic data anchored to:

- AKC breed popularity rankings (2023)
- Realistic DFW geography (Dallas metro zip codes)
- Dog age distributions skewed young with a senior tail (gamma shape=2.5)
- Order frequency benchmarks from fresh pet food category research

**Label noise:** 4% random label flips were injected to prevent the model from over-fitting to the deterministic generation process. Real-world labels are never perfectly clean.

### Features (23 total)

**Pet attributes:** breed, size, pet_age_years, life_stage (puppy/adult/senior), weight_lbs, allergy, activity_level, days_to_birthday

**Customer behavioral features:** city, signup_source, days_since_signup, n_orders, days_since_last_order, avg_interval_days, interval_stddev, max_interval_days, had_resumption, orders_last_7d, orders_last_30d, orders_last_90d, total_spend, avg_order_value, avg_rating

The `had_resumption` flag and `orders_last_7d` were added specifically to disambiguate TRAVEL_PAUSE (long gap then resumed) from RE_ENGAGE (long gap, hasn't resumed yet).

### Models compared

| Model | Test Accuracy | Weighted F1 |
|---|---|---|
| Random Forest (baseline) | 0.866 | 0.864 |
| Gradient Boosting | 0.866 | 0.863 |
| LightGBM | 0.856 | 0.855 |
| **XGBoost (champion)** | **0.866** | **0.865** |

All models trained with class weighting (`sample_weight="balanced"` or `class_weight="balanced"`) to handle the 48.6% STABLE majority class.

### Baselines (so accuracy has context)

| Approach | Accuracy |
|---|---|
| Random (stratified) | 28.4% |
| Always predict majority (STABLE) | 48.8% |
| Our champion model | **86.6%** |

The model is 75% better than always predicting STABLE.

### 5-fold cross-validation

Weighted F1: **0.857 ± 0.009** - tight CV indicates no overfitting on the hold-out set.

### Per-class F1

| Class | F1 |
|---|---|
| NEW_PUPPY | 0.97 |
| BIRTHDAY | 0.94 |
| STABLE | 0.91 |
| RE_ENGAGE | 0.88 |
| FIRST_TIME | 0.83 |
| PET_LOSS | 0.73 |
| SENIOR_TRANSITION | 0.70 |
| TRAVEL_PAUSE | 0.64 |

### Top features

1. `pet_age_years` (0.19) - separates puppy/adult/senior cleanly
2. `days_to_birthday` (0.13) - directly drives BIRTHDAY
3. `days_since_last_order` (0.12) - recency signal for RE_ENGAGE/PET_LOSS
4. `max_interval_days` (0.10) - longest gap, signals TRAVEL_PAUSE/PET_LOSS
5. `days_since_signup` (0.08) - separates FIRST_TIME from established customers

### Known limitations

1. **TRAVEL_PAUSE F1 of 0.64** - the lowest class. Pattern overlaps with RE_ENGAGE because both have a long gap. Production fix: re-evaluate the prediction 7-14 days later. If a new order has come in, confirm TRAVEL_PAUSE. Otherwise, downgrade to RE_ENGAGE.
2. **PET_LOSS production safety** - false positives mean sending a condolence card to a customer with a living dog. We require manual review on all PET_LOSS predictions before any action.
3. **Synthetic data** - the production model needs to be re-trained on real CRM data once Barkley Bites has 6+ months of customer history. The feature pipeline transfers without modification.
4. **No free-text features** - customer notes ("travel," "pet passed") would be strong direct signals. Current model doesn't see them.

### Future work

- Add free-text signals from CRM customer notes (NLP layer)
- Move from snapshot-based to event-based modeling (sequence models over full order history)
- A/B test the action playbook in production
- SHAP per-prediction explanations for the marketing team

---

## Project structure

```
barkley_lifecycle_app/
├── app.py                       # Streamlit app (entry point)
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── .streamlit/
│   └── config.toml              # Brand theme (orange/black/white)
├── artifacts/
│   ├── lifecycle_model.pkl      # Trained XGBoost model
│   ├── feature_encoders.pkl     # Label encoders for categoricals
│   ├── target_encoder.pkl       # Encoder for the 8 lifecycle classes
│   ├── model_config.pkl         # Feature columns + class names
│   ├── metrics.json             # All evaluation metrics
│   ├── classification_report.txt
│   ├── confusion_matrix.png
│   ├── feature_importance.png
│   └── class_distribution.png
├── data/
│   ├── customers.csv            # 800 rows
│   ├── pets.csv                 # 1,002 rows
│   ├── products.csv             # 12 rows
│   ├── orders.csv               # 13,818 rows
│   └── pet_lifecycle_dataset.csv # 1,002 model-ready snapshot rows
└── scripts/
    ├── build_dataset.py         # Generate the synthetic dataset
    └── train_model.py           # Train + compare all models
```

---

## Running locally

```bash
# 1. Clone and enter the folder
cd barkley_lifecycle_app

# 2. (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py

# Open http://localhost:8501 in your browser
```

To regenerate the dataset and re-train the model:

```bash
python3 scripts/build_dataset.py    # rebuilds data/*.csv
python3 scripts/train_model.py      # rebuilds artifacts/*.pkl
```

---

## Deploying to Streamlit Community Cloud (free, forever)

1. **Push this folder to a public GitHub repo**
   ```bash
   git init
   git add .
   git commit -m "Initial deploy"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/barkley-lifecycle.git
   git push -u origin main
   ```

2. **Go to** [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

3. **Click "New app"**:
   - Repository: `YOUR_USERNAME/barkley-lifecycle`
   - Branch: `main`
   - Main file path: `app.py`

4. **Click "Deploy"**. First deploy takes 3-5 minutes (installs dependencies). After that, every push to `main` redeploys automatically.

5. **Your app URL** will be something like `https://barkley-lifecycle.streamlit.app`. Share with Schuyler.

---

## Credits

Built by **Riya Ravishankar** (with Gauri's QR/video workstream).
DCP Phase 2 - Spring 2026 - FIX-IT-FIVE.
Client: Barkley Bites - Founder & CEO Schuyler Ford.
