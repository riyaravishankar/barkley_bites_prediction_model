"""
Barkley Bites Pet Lifecycle Dataset Builder (v2 with fixes)
FIX-IT-FIVE | DCP Phase 2 | Riya Ravishankar

Generates a labeled dataset for the Pet Lifecycle Detection Model.
v2 changes vs v1:
  + 4% label noise injected (defensibility)
  + orders_last_7d feature (helps TRAVEL_PAUSE)
  + had_resumption feature (helps TRAVEL_PAUSE)
"""

import csv
import os
import random
from datetime import datetime, timedelta
import numpy as np

random.seed(42)
np.random.seed(42)

OUT_DIR = "/home/claude/barkley_dcp/model/data"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- Reference data ----------
BREEDS = [
    ("French Bulldog",  0.10, "small",   18, 28),
    ("Labrador",        0.12, "large",   55, 80),
    ("Golden Retriever",0.09, "large",   55, 75),
    ("German Shepherd", 0.07, "large",   55, 90),
    ("Poodle",          0.07, "medium",  40, 70),
    ("Bulldog",         0.05, "medium",  40, 50),
    ("Beagle",          0.05, "small",   20, 30),
    ("Rottweiler",      0.04, "large",   80, 130),
    ("Dachshund",       0.05, "small",   16, 32),
    ("German Shorthaired Pointer", 0.04, "large", 45, 70),
    ("Pembroke Welsh Corgi", 0.04, "small", 22, 30),
    ("Australian Shepherd", 0.04, "medium", 40, 65),
    ("Yorkshire Terrier", 0.03, "small",  4, 7),
    ("Cavalier King Charles", 0.03, "small", 13, 18),
    ("Boxer",           0.03, "large",   50, 80),
    ("Shih Tzu",        0.03, "small",   9, 16),
    ("Mixed Breed",     0.12, "medium",  20, 70),
]
breed_names = [b[0] for b in BREEDS]
breed_weights = np.array([b[1] for b in BREEDS])
breed_weights = breed_weights / breed_weights.sum()
breed_size = {b[0]: b[2] for b in BREEDS}
breed_min_w = {b[0]: b[3] for b in BREEDS}
breed_max_w = {b[0]: b[4] for b in BREEDS}

DFW_ZIPS = [
    ("Dallas","75201"),("Dallas","75205"),("Dallas","75214"),
    ("Plano","75024"),("Plano","75093"),
    ("Frisco","75033"),("Frisco","75034"),
    ("Richardson","75080"),("Richardson","75082"),
    ("Irving","75038"),("Irving","75063"),("Addison","75001"),
    ("Fort Worth","76102"),("Fort Worth","76109"),
    ("Arlington","76012"),("Arlington","76016"),
    ("McKinney","75070"),("Allen","75013"),
    ("Coppell","75019"),("Carrollton","75007"),
]

FIRST_NAMES = ["Sarah","Michael","Emma","David","Jessica","James","Olivia","Daniel",
    "Ashley","Chris","Megan","Ryan","Lauren","Brandon","Rachel","Tyler",
    "Amanda","Jason","Stephanie","Justin","Nicole","Andrew","Brittany","Eric",
    "Priya","Rohit","Aisha","Carlos","Maria","Diego","Yuki","Wei",
    "Hannah","Connor","Madison","Ethan","Sophia","Logan","Ava","Noah"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Wilson","Anderson","Thomas",
    "Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson","White",
    "Patel","Kumar","Shah","Khan","Nguyen","Tran","Kim","Park","Chen","Wang"]
PET_NAMES = ["Bella","Max","Luna","Charlie","Daisy","Rocky","Milo","Zoe","Buddy","Ruby",
    "Cooper","Lucy","Bear","Lily","Tucker","Bailey","Stella","Duke","Maggie","Jack",
    "Sadie","Oliver","Penny","Riley","Sophie","Toby","Lola","Finn","Gus","Mochi",
    "Biscuit","Pickles","Waffles","Banjo","Scout","Pepper","Olive","Murphy","Roxy","Beans"]

products = [
    {"product_id":"P01","name":"Wild Salmon Bowl","protein":"salmon","life_stage":"all","kcal_per_oz":38,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":14.50},
    {"product_id":"P02","name":"Atlantic Whitefish Recipe","protein":"whitefish","life_stage":"all","kcal_per_oz":35,"allergen_chicken":0,"allergen_grain":1,"allergen_dairy":0,"price_per_lb":13.00},
    {"product_id":"P03","name":"Sustainable Cod & Sweet Potato","protein":"cod","life_stage":"all","kcal_per_oz":33,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":13.50},
    {"product_id":"P04","name":"Senior Tuna & Pumpkin","protein":"tuna","life_stage":"senior","kcal_per_oz":30,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":14.00},
    {"product_id":"P05","name":"Puppy Salmon Starter","protein":"salmon","life_stage":"puppy","kcal_per_oz":42,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":1,"price_per_lb":15.00},
    {"product_id":"P06","name":"Rescued Mahi & Rice","protein":"mahi","life_stage":"adult","kcal_per_oz":36,"allergen_chicken":0,"allergen_grain":1,"allergen_dairy":0,"price_per_lb":14.50},
    {"product_id":"P07","name":"Coastal Sardine Blend","protein":"sardine","life_stage":"adult","kcal_per_oz":40,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":13.50},
    {"product_id":"P08","name":"Pacific Halibut & Quinoa","protein":"halibut","life_stage":"all","kcal_per_oz":34,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":15.50},
    {"product_id":"P09","name":"Texas Catfish Stew","protein":"catfish","life_stage":"adult","kcal_per_oz":37,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":12.50},
    {"product_id":"P10","name":"Lean Trout & Veggie","protein":"trout","life_stage":"adult","kcal_per_oz":32,"allergen_chicken":0,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":13.00},
    {"product_id":"P11","name":"Heritage Chicken Bowl","protein":"chicken","life_stage":"adult","kcal_per_oz":39,"allergen_chicken":1,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":12.00},
    {"product_id":"P12","name":"Free-Range Turkey Recipe","protein":"turkey","life_stage":"all","kcal_per_oz":36,"allergen_chicken":1,"allergen_grain":0,"allergen_dairy":0,"price_per_lb":12.50},
]

TODAY = datetime(2026, 5, 4)
N_CUSTOMERS = 800

# ---------- Build customers ----------
customers = []
for cid in range(1, N_CUSTOMERS + 1):
    city, zip_code = random.choice(DFW_ZIPS)
    signup_days_ago = min(int(np.random.exponential(scale=180)), 540)
    signup_date = TODAY - timedelta(days=signup_days_ago)
    customers.append({
        "customer_id": f"C{cid:04d}",
        "first_name": random.choice(FIRST_NAMES),
        "last_name":  random.choice(LAST_NAMES),
        "email":      f"customer{cid}@example.com",
        "city":       city,
        "zip_code":   zip_code,
        "signup_date": signup_date.strftime("%Y-%m-%d"),
        "signup_source": np.random.choice(
            ["Instagram","Friend Referral","Google Search","Vet Referral","Pop-up Event","TikTok"],
            p=[0.30,0.25,0.15,0.12,0.10,0.08]),
        "has_used_free_trial": int(np.random.random() < 0.92),
    })

# ---------- Build pets ----------
pets = []
pet_counter = 1
for c in customers:
    n_pets = np.random.choice([1,2,3], p=[0.78,0.18,0.04])
    for _ in range(n_pets):
        breed = np.random.choice(breed_names, p=breed_weights)
        age_years = round(float(np.clip(np.random.gamma(2.5, 2.2), 0.2, 16)), 1)
        if age_years < 1: life_stage = "puppy"
        elif age_years < 7: life_stage = "adult"
        else: life_stage = "senior"
        weight = round(float(np.random.uniform(breed_min_w[breed], breed_max_w[breed])), 1)
        has_allergy = np.random.random() < 0.15
        allergy = ""
        if has_allergy:
            allergy = np.random.choice(["chicken","grain","dairy","beef"], p=[0.5,0.25,0.15,0.10])
        activity = np.random.choice(["low","medium","high"], p=[0.25,0.55,0.20])
        pets.append({
            "pet_id": f"PET{pet_counter:04d}",
            "customer_id": c["customer_id"],
            "pet_name": random.choice(PET_NAMES),
            "breed": breed, "size": breed_size[breed],
            "age_years": age_years, "life_stage": life_stage,
            "weight_lbs": weight, "allergy": allergy, "activity_level": activity,
            "birthday_month": int(np.random.randint(1,13)),
            "birthday_day": int(np.random.randint(1,28)),
        })
        pet_counter += 1

# ---------- Lifecycle scenarios ----------
SCENARIO_DIST = {
    "STABLE":            0.50, "RE_ENGAGE":         0.13,
    "NEW_PUPPY":         0.08, "BIRTHDAY":          0.10,
    "TRAVEL_PAUSE":      0.06, "SENIOR_TRANSITION": 0.06,
    "PET_LOSS":          0.04, "FIRST_TIME":        0.03,
}
scenarios = list(SCENARIO_DIST.keys())
probs = list(SCENARIO_DIST.values())

pet_scenarios = {}
for p in pets:
    s = np.random.choice(scenarios, p=probs)
    if s == "NEW_PUPPY":
        p["age_years"] = round(np.random.uniform(0.15, 0.95), 1)
        p["life_stage"] = "puppy"
    if s == "SENIOR_TRANSITION":
        p["age_years"] = round(np.random.uniform(6.5, 7.8), 1)
        p["life_stage"] = "adult" if p["age_years"] < 7 else "senior"
    pet_scenarios[p["pet_id"]] = s

# Inject 4% label noise (real-world data is never cleanly labeled)
noisy_pet_ids = list(pet_scenarios.keys())
random.shuffle(noisy_pet_ids)
n_noise = int(0.04 * len(noisy_pet_ids))
for pid in noisy_pet_ids[:n_noise]:
    current = pet_scenarios[pid]
    pet_scenarios[pid] = random.choice([s for s in scenarios if s != current])

# ---------- Build orders ----------
orders = []
order_counter = 1
for p in pets:
    cid = p["customer_id"]
    pet_id = p["pet_id"]
    scenario = pet_scenarios[pet_id]
    customer = next(c for c in customers if c["customer_id"] == cid)
    signup_date = datetime.strptime(customer["signup_date"], "%Y-%m-%d")

    # Pick recipe based on pet
    if p["life_stage"] == "puppy":
        cands = [pr for pr in products if pr["life_stage"] in ("puppy","all")]
    elif p["life_stage"] == "senior":
        cands = [pr for pr in products if pr["life_stage"] in ("senior","all","adult")]
    else:
        cands = [pr for pr in products if pr["life_stage"] in ("adult","all")]

    if p["allergy"] == "chicken": cands = [pr for pr in cands if pr["allergen_chicken"]==0]
    if p["allergy"] == "grain":   cands = [pr for pr in cands if pr["allergen_grain"]==0]
    if p["allergy"] == "dairy":   cands = [pr for pr in cands if pr["allergen_dairy"]==0]
    if not cands: cands = products
    primary = random.choice(cands)

    order_dates = []
    if scenario == "FIRST_TIME":
        order_dates = []
    elif scenario == "STABLE":
        d = signup_date + timedelta(days=int(np.random.randint(0,5)))
        while d < TODAY - timedelta(days=int(np.random.randint(2,8))):
            order_dates.append(d); d += timedelta(days=int(np.random.randint(7,15)))
    elif scenario == "RE_ENGAGE":
        gap = int(np.random.randint(14,60))
        last_d = TODAY - timedelta(days=gap)
        d = signup_date + timedelta(days=int(np.random.randint(0,7)))
        while d <= last_d:
            order_dates.append(d); d += timedelta(days=int(np.random.randint(7,14)))
    elif scenario == "NEW_PUPPY":
        order_dates = [TODAY - timedelta(days=int(np.random.randint(0,7)))]
    elif scenario == "BIRTHDAY":
        d = signup_date + timedelta(days=int(np.random.randint(0,5)))
        while d < TODAY - timedelta(days=int(np.random.randint(2,8))):
            order_dates.append(d); d += timedelta(days=int(np.random.randint(7,14)))
        bday_offset = int(np.random.randint(1,14))
        bday_date = TODAY + timedelta(days=bday_offset)
        p["birthday_month"] = bday_date.month
        p["birthday_day"] = bday_date.day
    elif scenario == "TRAVEL_PAUSE":
        # Regular orders, gap of 21-40 days, then RESUMED ordering in last 7-14 days
        # The resumption is the key signal that distinguishes from RE_ENGAGE
        d = signup_date + timedelta(days=int(np.random.randint(0,5)))
        gap_started = False
        gap_start_offset = int(np.random.randint(60,180)) if (TODAY - signup_date).days > 60 else 30
        gap_start_date = signup_date + timedelta(days=gap_start_offset)
        while d < TODAY - timedelta(days=int(np.random.randint(2,12))):
            if (not gap_started) and d > gap_start_date:
                d += timedelta(days=int(np.random.randint(21,40)))
                gap_started = True
                continue
            order_dates.append(d); d += timedelta(days=int(np.random.randint(7,14)))
    elif scenario == "SENIOR_TRANSITION":
        d = signup_date + timedelta(days=int(np.random.randint(0,5)))
        while d < TODAY - timedelta(days=int(np.random.randint(2,8))):
            order_dates.append(d); d += timedelta(days=int(np.random.randint(7,14)))
    elif scenario == "PET_LOSS":
        stopped_days_ago = int(np.random.randint(30,180))
        last_d = TODAY - timedelta(days=stopped_days_ago)
        if last_d < signup_date: last_d = signup_date + timedelta(days=14)
        d = signup_date + timedelta(days=int(np.random.randint(0,7)))
        while d <= last_d:
            order_dates.append(d); d += timedelta(days=int(np.random.randint(7,14)))

    for od in order_dates:
        chosen = primary if np.random.random() < 0.7 else random.choice(cands)
        qty_lbs = round(float(np.random.choice([2,3,4,5,6,7], p=[0.05,0.15,0.25,0.25,0.20,0.10])), 1)
        unit_price = chosen["price_per_lb"]
        total = round(qty_lbs * unit_price, 2)
        rating = ""
        if np.random.random() < 0.35:
            rating = int(np.random.choice([3,4,5], p=[0.05,0.25,0.70]))
        orders.append({
            "order_id": f"BB{order_counter:06d}",
            "customer_id": cid, "pet_id": pet_id,
            "order_date": od.strftime("%Y-%m-%d"),
            "product_id": chosen["product_id"],
            "qty_lbs": qty_lbs, "unit_price": unit_price, "total_amount": total,
            "delivery_status": "Delivered" if od < TODAY - timedelta(days=2) else "Scheduled",
            "rating": rating,
            "channel": np.random.choice(["Web","Pickup","Re-order Email"], p=[0.7,0.15,0.15]),
        })
        order_counter += 1

# ---------- Build snapshot with new features ----------
snapshot = []
for p in pets:
    cid = p["customer_id"]
    pet_id = p["pet_id"]
    scenario = pet_scenarios[pet_id]
    customer = next(c for c in customers if c["customer_id"] == cid)

    pet_orders = [o for o in orders if o["pet_id"] == pet_id]
    n_orders = len(pet_orders)

    if n_orders > 0:
        order_dates = [datetime.strptime(o["order_date"], "%Y-%m-%d") for o in pet_orders]
        last_order = max(order_dates)
        first_order = min(order_dates)
        days_since_last_order = (TODAY - last_order).days
        days_active = max((last_order - first_order).days, 1)
        avg_interval_days = days_active / max(n_orders - 1, 1) if n_orders > 1 else 0
        total_spend = round(sum(o["total_amount"] for o in pet_orders), 2)
        avg_order_value = round(total_spend / n_orders, 2)
        ratings = [int(o["rating"]) for o in pet_orders if o["rating"] != ""]
        avg_rating = round(np.mean(ratings), 2) if ratings else 0
        if n_orders >= 3:
            sorted_dates = sorted(order_dates)
            intervals = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates)-1)]
            interval_stddev = round(float(np.std(intervals)), 2)
            max_interval = max(intervals)
            # NEW FEATURE: had_resumption - did orders resume after the longest gap?
            max_gap_idx = intervals.index(max_interval)
            had_resumption = 1 if max_gap_idx < len(intervals) - 1 else 0
        else:
            interval_stddev = 0
            max_interval = 0
            had_resumption = 0
        orders_last_7d = sum(1 for od in order_dates if (TODAY - od).days <= 7)
        orders_last_30d = sum(1 for od in order_dates if (TODAY - od).days <= 30)
        orders_last_90d = sum(1 for od in order_dates if (TODAY - od).days <= 90)
    else:
        days_since_last_order = -1
        avg_interval_days = 0; total_spend = 0; avg_order_value = 0
        avg_rating = 0; interval_stddev = 0; max_interval = 0
        had_resumption = 0
        orders_last_7d = 0; orders_last_30d = 0; orders_last_90d = 0

    bday_this_year = datetime(TODAY.year, p["birthday_month"], p["birthday_day"])
    if bday_this_year < TODAY:
        bday_this_year = datetime(TODAY.year + 1, p["birthday_month"], p["birthday_day"])
    days_to_birthday = (bday_this_year - TODAY).days
    days_since_signup = (TODAY - datetime.strptime(customer["signup_date"], "%Y-%m-%d")).days

    snapshot.append({
        "snapshot_date": TODAY.strftime("%Y-%m-%d"),
        "customer_id": cid, "pet_id": pet_id, "pet_name": p["pet_name"],
        "breed": p["breed"], "size": p["size"],
        "pet_age_years": p["age_years"], "life_stage": p["life_stage"],
        "weight_lbs": p["weight_lbs"], "allergy": p["allergy"],
        "activity_level": p["activity_level"],
        "city": customer["city"], "signup_source": customer["signup_source"],
        "days_since_signup": days_since_signup,
        "n_orders": n_orders, "days_since_last_order": days_since_last_order,
        "avg_interval_days": round(float(avg_interval_days), 2),
        "interval_stddev": interval_stddev, "max_interval_days": max_interval,
        "had_resumption": had_resumption,           # NEW
        "orders_last_7d": orders_last_7d,           # NEW
        "orders_last_30d": orders_last_30d,
        "orders_last_90d": orders_last_90d,
        "total_spend": total_spend, "avg_order_value": avg_order_value,
        "avg_rating": avg_rating, "days_to_birthday": days_to_birthday,
        "lifecycle_event": scenario,
    })

def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

write_csv(f"{OUT_DIR}/customers.csv", customers, list(customers[0].keys()))
write_csv(f"{OUT_DIR}/pets.csv", pets, list(pets[0].keys()))
write_csv(f"{OUT_DIR}/products.csv", products, list(products[0].keys()))
write_csv(f"{OUT_DIR}/orders.csv", orders, list(orders[0].keys()))
write_csv(f"{OUT_DIR}/pet_lifecycle_dataset.csv", snapshot, list(snapshot[0].keys()))

from collections import Counter
print(f"Customers:     {len(customers)}")
print(f"Pets:          {len(pets)}")
print(f"Products:      {len(products)}")
print(f"Orders:        {len(orders)}")
print(f"Snapshots:     {len(snapshot)}")
print()
print("Class distribution:")
for evt, n in Counter(r["lifecycle_event"] for r in snapshot).most_common():
    print(f"  {evt:20s} {n:5d}  ({n/len(snapshot)*100:5.1f}%)")
