"""
Generate a 500K-sample pet lifecycle dataset.

Strategy: skip the per-pet order generation (slow on 500K) and directly
sample features from realistic distributions per lifecycle scenario.
Same 8 classes, same feature schema as the 1K version, scales to 500K
in seconds.

Each scenario has a "feature signature" — a set of distributions for
behavioral features that match the real pattern for that scenario.
We sample from those distributions to populate the snapshot.
"""

import csv
import os
import time
from datetime import datetime
import numpy as np

np.random.seed(42)

OUT_DIR = "/home/claude/barkley_lifecycle_app/data"
N_SAMPLES = 500_000

# ---------- Reference distributions ----------
BREEDS = [
    "French Bulldog","Labrador","Golden Retriever","German Shepherd","Poodle",
    "Bulldog","Beagle","Rottweiler","Dachshund","German Shorthaired Pointer",
    "Pembroke Welsh Corgi","Australian Shepherd","Yorkshire Terrier",
    "Cavalier King Charles","Boxer","Shih Tzu","Mixed Breed",
]
breed_weights = np.array([0.10,0.12,0.09,0.07,0.07,0.05,0.05,0.04,0.05,0.04,
                          0.04,0.04,0.03,0.03,0.03,0.03,0.12])
breed_weights = breed_weights / breed_weights.sum()

breed_size = {
    "French Bulldog":"small","Labrador":"large","Golden Retriever":"large",
    "German Shepherd":"large","Poodle":"medium","Bulldog":"medium",
    "Beagle":"small","Rottweiler":"large","Dachshund":"small",
    "German Shorthaired Pointer":"large","Pembroke Welsh Corgi":"small",
    "Australian Shepherd":"medium","Yorkshire Terrier":"small",
    "Cavalier King Charles":"small","Boxer":"large","Shih Tzu":"small",
    "Mixed Breed":"medium",
}
breed_min_w = {
    "French Bulldog":18,"Labrador":55,"Golden Retriever":55,"German Shepherd":55,
    "Poodle":40,"Bulldog":40,"Beagle":20,"Rottweiler":80,"Dachshund":16,
    "German Shorthaired Pointer":45,"Pembroke Welsh Corgi":22,
    "Australian Shepherd":40,"Yorkshire Terrier":4,"Cavalier King Charles":13,
    "Boxer":50,"Shih Tzu":9,"Mixed Breed":20,
}
breed_max_w = {
    "French Bulldog":28,"Labrador":80,"Golden Retriever":75,"German Shepherd":90,
    "Poodle":70,"Bulldog":50,"Beagle":30,"Rottweiler":130,"Dachshund":32,
    "German Shorthaired Pointer":70,"Pembroke Welsh Corgi":30,
    "Australian Shepherd":65,"Yorkshire Terrier":7,"Cavalier King Charles":18,
    "Boxer":80,"Shih Tzu":16,"Mixed Breed":70,
}

CITIES = ["Dallas","Plano","Frisco","Richardson","Irving","Addison","Fort Worth",
          "Arlington","McKinney","Allen","Coppell","Carrollton"]
SIGNUP_SOURCES = ["Instagram","Friend Referral","Google Search","Vet Referral","Pop-up Event","TikTok"]
ALLERGIES = ["","chicken","grain","dairy","beef"]
ACTIVITY = ["low","medium","high"]

# Class distribution
SCENARIO_DIST = {
    "STABLE":            0.45,
    "RE_ENGAGE":         0.13,
    "BIRTHDAY":          0.10,
    "NEW_PUPPY":         0.08,
    "TRAVEL_PAUSE":      0.07,
    "SENIOR_TRANSITION": 0.07,
    "PET_LOSS":          0.05,
    "FIRST_TIME":        0.05,
}
scenarios = list(SCENARIO_DIST.keys())
probs = np.array([SCENARIO_DIST[s] for s in scenarios])


def sample_features_for_scenario(scenario, n):
    """Sample n rows of features for a given scenario.
    Returns dict of arrays."""

    # Common: pet attributes
    breed = np.random.choice(BREEDS, n, p=breed_weights)
    sizes = np.array([breed_size[b] for b in breed])
    weights = np.array([np.random.uniform(breed_min_w[b], breed_max_w[b]) for b in breed]).round(1)

    # Age depends on scenario
    if scenario == "NEW_PUPPY":
        age = np.random.uniform(0.15, 0.95, n).round(1)
    elif scenario == "SENIOR_TRANSITION":
        age = np.random.uniform(6.5, 7.8, n).round(1)
    else:
        age = np.clip(np.random.gamma(2.5, 2.2, n), 0.2, 16).round(1)

    life_stage = np.where(age < 1, "puppy",
                  np.where(age < 7, "adult", "senior"))

    has_allergy = np.random.random(n) < 0.15
    allergy = np.where(has_allergy,
                       np.random.choice(["chicken","grain","dairy","beef"],
                                        n, p=[0.5,0.25,0.15,0.10]),
                       "")
    activity = np.random.choice(ACTIVITY, n, p=[0.25,0.55,0.20])
    city = np.random.choice(CITIES, n)
    source = np.random.choice(SIGNUP_SOURCES, n, p=[0.30,0.25,0.15,0.12,0.10,0.08])

    # Days to birthday: scenario-dependent
    if scenario == "BIRTHDAY":
        days_to_bday = np.random.randint(0, 14, n)
    else:
        days_to_bday = np.random.randint(15, 365, n)

    # Behavioral features per scenario
    if scenario == "STABLE":
        days_since_signup = np.random.randint(60, 540, n)
        days_since_last_order = np.random.randint(2, 12, n)
        n_orders = np.maximum(np.random.poisson(15, n), 3)
        avg_interval = np.random.uniform(7, 14, n).round(2)
        interval_stddev = np.random.uniform(0.5, 3.5, n).round(2)
        max_interval = (avg_interval + np.random.uniform(2, 6, n)).astype(int)
        had_resumption = np.zeros(n, dtype=int)
        orders_last_7d = np.random.choice([0, 1], n, p=[0.4, 0.6])
        orders_last_30d = np.random.randint(2, 5, n)
        orders_last_90d = np.random.randint(6, 14, n)
        total_spend = (n_orders * np.random.uniform(40, 70, n)).round(2)
        avg_order_value = (total_spend / n_orders).round(2)
        avg_rating = np.random.choice([0, 4.0, 4.5, 5.0], n, p=[0.3, 0.1, 0.3, 0.3])

    elif scenario == "RE_ENGAGE":
        days_since_signup = np.random.randint(30, 540, n)
        days_since_last_order = np.random.randint(14, 60, n)
        n_orders = np.maximum(np.random.poisson(8, n), 2)
        avg_interval = np.random.uniform(7, 14, n).round(2)
        interval_stddev = np.random.uniform(1, 5, n).round(2)
        max_interval = days_since_last_order  # the current gap is the max
        had_resumption = np.zeros(n, dtype=int)
        orders_last_7d = np.zeros(n, dtype=int)
        orders_last_30d = np.where(days_since_last_order <= 30, 1, 0)
        orders_last_90d = np.random.randint(0, 5, n)
        total_spend = (n_orders * np.random.uniform(40, 70, n)).round(2)
        avg_order_value = (total_spend / n_orders).round(2)
        avg_rating = np.random.choice([0, 3.5, 4.0, 4.5], n, p=[0.4, 0.2, 0.2, 0.2])

    elif scenario == "BIRTHDAY":
        days_since_signup = np.random.randint(60, 540, n)
        days_since_last_order = np.random.randint(2, 12, n)
        n_orders = np.maximum(np.random.poisson(12, n), 3)
        avg_interval = np.random.uniform(7, 14, n).round(2)
        interval_stddev = np.random.uniform(0.5, 3, n).round(2)
        max_interval = (avg_interval + np.random.uniform(2, 5, n)).astype(int)
        had_resumption = np.zeros(n, dtype=int)
        orders_last_7d = np.random.choice([0, 1], n, p=[0.4, 0.6])
        orders_last_30d = np.random.randint(2, 5, n)
        orders_last_90d = np.random.randint(6, 13, n)
        total_spend = (n_orders * np.random.uniform(40, 70, n)).round(2)
        avg_order_value = (total_spend / n_orders).round(2)
        avg_rating = np.random.choice([0, 4.0, 4.5, 5.0], n, p=[0.3, 0.1, 0.3, 0.3])

    elif scenario == "NEW_PUPPY":
        days_since_signup = np.random.randint(0, 30, n)
        days_since_last_order = np.random.randint(0, 7, n)
        n_orders = np.random.choice([1, 2], n, p=[0.7, 0.3])
        avg_interval = np.random.uniform(0, 7, n).round(2)
        interval_stddev = np.zeros(n)
        max_interval = avg_interval.astype(int)
        had_resumption = np.zeros(n, dtype=int)
        orders_last_7d = np.minimum(n_orders, 2)
        orders_last_30d = n_orders
        orders_last_90d = n_orders
        total_spend = (n_orders * np.random.uniform(30, 60, n)).round(2)
        avg_order_value = (total_spend / np.maximum(n_orders, 1)).round(2)
        avg_rating = np.random.choice([0, 5.0], n, p=[0.6, 0.4])

    elif scenario == "TRAVEL_PAUSE":
        days_since_signup = np.random.randint(120, 540, n)
        # The customer just resumed: last order was recent
        days_since_last_order = np.random.randint(2, 12, n)
        n_orders = np.maximum(np.random.poisson(12, n), 4)
        avg_interval = np.random.uniform(7, 14, n).round(2)
        interval_stddev = np.random.uniform(8, 18, n).round(2)  # high variance
        # Big gap somewhere in history
        max_interval = np.random.randint(21, 45, n)
        had_resumption = np.ones(n, dtype=int)  # KEY FEATURE
        orders_last_7d = np.random.choice([0, 1], n, p=[0.4, 0.6])
        orders_last_30d = np.random.randint(1, 4, n)
        orders_last_90d = np.random.randint(3, 10, n)
        total_spend = (n_orders * np.random.uniform(40, 70, n)).round(2)
        avg_order_value = (total_spend / n_orders).round(2)
        avg_rating = np.random.choice([0, 4.0, 4.5, 5.0], n, p=[0.3, 0.2, 0.3, 0.2])

    elif scenario == "SENIOR_TRANSITION":
        days_since_signup = np.random.randint(60, 540, n)
        days_since_last_order = np.random.randint(2, 12, n)
        n_orders = np.maximum(np.random.poisson(15, n), 4)
        avg_interval = np.random.uniform(7, 14, n).round(2)
        interval_stddev = np.random.uniform(0.5, 3.5, n).round(2)
        max_interval = (avg_interval + np.random.uniform(2, 6, n)).astype(int)
        had_resumption = np.zeros(n, dtype=int)
        orders_last_7d = np.random.choice([0, 1], n, p=[0.4, 0.6])
        orders_last_30d = np.random.randint(2, 5, n)
        orders_last_90d = np.random.randint(6, 14, n)
        total_spend = (n_orders * np.random.uniform(40, 70, n)).round(2)
        avg_order_value = (total_spend / n_orders).round(2)
        avg_rating = np.random.choice([0, 4.0, 4.5, 5.0], n, p=[0.3, 0.1, 0.3, 0.3])

    elif scenario == "PET_LOSS":
        days_since_signup = np.random.randint(120, 540, n)
        days_since_last_order = np.random.randint(30, 180, n)  # long absence
        n_orders = np.maximum(np.random.poisson(10, n), 3)
        avg_interval = np.random.uniform(7, 14, n).round(2)
        interval_stddev = np.random.uniform(1, 4, n).round(2)
        max_interval = days_since_last_order  # the absence IS the max gap
        had_resumption = np.zeros(n, dtype=int)  # NO resumption
        orders_last_7d = np.zeros(n, dtype=int)
        orders_last_30d = np.zeros(n, dtype=int)
        orders_last_90d = np.where(days_since_last_order <= 90, 0, 0)
        total_spend = (n_orders * np.random.uniform(40, 70, n)).round(2)
        avg_order_value = (total_spend / n_orders).round(2)
        avg_rating = np.random.choice([0, 4.0, 4.5, 5.0], n, p=[0.4, 0.2, 0.2, 0.2])

    elif scenario == "FIRST_TIME":
        days_since_signup = np.random.randint(0, 30, n)
        days_since_last_order = np.full(n, -1)  # never ordered
        n_orders = np.zeros(n, dtype=int)
        avg_interval = np.zeros(n)
        interval_stddev = np.zeros(n)
        max_interval = np.zeros(n, dtype=int)
        had_resumption = np.zeros(n, dtype=int)
        orders_last_7d = np.zeros(n, dtype=int)
        orders_last_30d = np.zeros(n, dtype=int)
        orders_last_90d = np.zeros(n, dtype=int)
        total_spend = np.zeros(n)
        avg_order_value = np.zeros(n)
        avg_rating = np.zeros(n)

    return {
        "breed": breed,
        "size": sizes,
        "pet_age_years": age,
        "life_stage": life_stage,
        "weight_lbs": weights,
        "allergy": allergy,
        "activity_level": activity,
        "city": city,
        "signup_source": source,
        "days_since_signup": days_since_signup.astype(int),
        "n_orders": n_orders.astype(int),
        "days_since_last_order": days_since_last_order.astype(int),
        "avg_interval_days": avg_interval,
        "interval_stddev": interval_stddev,
        "max_interval_days": max_interval.astype(int),
        "had_resumption": had_resumption,
        "orders_last_7d": orders_last_7d.astype(int),
        "orders_last_30d": orders_last_30d.astype(int),
        "orders_last_90d": orders_last_90d.astype(int),
        "total_spend": total_spend.round(2),
        "avg_order_value": avg_order_value.round(2),
        "avg_rating": avg_rating,
        "days_to_birthday": days_to_bday.astype(int),
        "lifecycle_event": np.full(n, scenario),
    }


# ---------- Generate ----------
print(f"Generating {N_SAMPLES:,} samples...")
t0 = time.time()

# Sample scenarios
scenario_assignments = np.random.choice(scenarios, N_SAMPLES, p=probs)

# Build per-scenario chunks then concatenate
chunks = {}
for sc in scenarios:
    n = (scenario_assignments == sc).sum()
    print(f"  Sampling {sc:20s}: {n:,}")
    chunks[sc] = sample_features_for_scenario(sc, n)

# Concatenate
print(f"\nConcatenating chunks...")
all_data = {}
for key in chunks[scenarios[0]].keys():
    all_data[key] = np.concatenate([chunks[sc][key] for sc in scenarios])

# Shuffle
print(f"Shuffling...")
n_total = len(all_data["breed"])
shuffle_idx = np.random.permutation(n_total)
for key in all_data:
    all_data[key] = all_data[key][shuffle_idx]

# Inject 4% label noise
print(f"Injecting 4% label noise...")
noise_idx = np.random.choice(n_total, int(0.04 * n_total), replace=False)
for i in noise_idx:
    current = all_data["lifecycle_event"][i]
    other = np.random.choice([s for s in scenarios if s != current])
    all_data["lifecycle_event"][i] = other

# Write CSV
print(f"Writing CSV...")
import pandas as pd
df = pd.DataFrame(all_data)
# Add identifier columns
df.insert(0, "snapshot_date", "2026-05-07")
df.insert(1, "customer_id", [f"C{i:07d}" for i in range(n_total)])
df.insert(2, "pet_id", [f"PET{i:07d}" for i in range(n_total)])
df.insert(3, "pet_name", "Pet")  # placeholder name

out_path = f"{OUT_DIR}/pet_lifecycle_dataset.csv"
df.to_csv(out_path, index=False)

print(f"\nWrote {len(df):,} rows to {out_path}")
print(f"File size: {os.path.getsize(out_path) / 1024 / 1024:.1f} MB")
print(f"Time: {time.time() - t0:.1f}s")

# Summary
from collections import Counter
print(f"\nClass distribution:")
for evt, n in Counter(df["lifecycle_event"]).most_common():
    print(f"  {evt:20s} {n:8,}  ({n/len(df)*100:5.1f}%)")
