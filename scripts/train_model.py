"""
Quick LightGBM + XGBoost comparison vs current Gradient Boosting champion.
Pick the best, save it as the final model.
"""
import os, json, joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
import lightgbm as lgb
import xgboost as xgb

DATA_PATH = "/home/claude/barkley_dcp/model/data/pet_lifecycle_dataset.csv"
OUT_DIR = "/home/claude/barkley_dcp/model/artifacts"
ORANGE = "#F26B1F"
BLACK = "#0E0E0E"

df = pd.read_csv(DATA_PATH)
drop_cols = ["snapshot_date","customer_id","pet_id","pet_name"]
target_col = "lifecycle_event"

X = df.drop(columns=drop_cols + [target_col]).copy()
y = df[target_col].copy()

categorical_cols = ["breed","size","life_stage","allergy","activity_level","city","signup_source"]
encoders = {}
for col in categorical_cols:
    X[col] = X[col].fillna("none")
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    encoders[col] = le

target_encoder = LabelEncoder()
y_enc = target_encoder.fit_transform(y)
class_names = list(target_encoder.classes_)
n_classes = len(class_names)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_enc, test_size=0.20, random_state=42, stratify=y_enc)

sample_weights = compute_sample_weight("balanced", y_train)

# ============================================================
# Model 1: Gradient Boosting (current champion)
# ============================================================
print("Training Gradient Boosting...")
gb = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42)
gb.fit(X_train, y_train, sample_weight=sample_weights)
gb_preds = gb.predict(X_test)
gb_acc = accuracy_score(y_test, gb_preds)
gb_f1 = f1_score(y_test, gb_preds, average="weighted", zero_division=0)
print(f"  GB:    acc={gb_acc:.4f}  weighted_F1={gb_f1:.4f}")

# ============================================================
# Model 2: LightGBM
# ============================================================
print("Training LightGBM...")
lgb_clf = lgb.LGBMClassifier(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    num_leaves=31, class_weight="balanced",
    random_state=42, verbose=-1, n_jobs=-1
)
lgb_clf.fit(X_train, y_train)
lgb_preds = lgb_clf.predict(X_test)
lgb_acc = accuracy_score(y_test, lgb_preds)
lgb_f1 = f1_score(y_test, lgb_preds, average="weighted", zero_division=0)
print(f"  LGB:   acc={lgb_acc:.4f}  weighted_F1={lgb_f1:.4f}")

# ============================================================
# Model 3: XGBoost
# ============================================================
print("Training XGBoost...")
xgb_clf = xgb.XGBClassifier(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    objective="multi:softprob", num_class=n_classes,
    random_state=42, n_jobs=-1, eval_metric="mlogloss",
    use_label_encoder=False, verbosity=0
)
xgb_clf.fit(X_train, y_train, sample_weight=sample_weights)
xgb_preds = xgb_clf.predict(X_test)
xgb_acc = accuracy_score(y_test, xgb_preds)
xgb_f1 = f1_score(y_test, xgb_preds, average="weighted", zero_division=0)
print(f"  XGB:   acc={xgb_acc:.4f}  weighted_F1={xgb_f1:.4f}")
print()

# ============================================================
# Pick winner
# ============================================================
results = [
    ("GradientBoosting", gb, gb_preds, gb_acc, gb_f1),
    ("LightGBM",         lgb_clf, lgb_preds, lgb_acc, lgb_f1),
    ("XGBoost",          xgb_clf, xgb_preds, xgb_acc, xgb_f1),
]
results.sort(key=lambda r: r[4], reverse=True)
champ_name, champ_model, champ_preds, champ_acc, champ_f1 = results[0]

print("=" * 60)
print(f"WINNER: {champ_name}")
print(f"  Accuracy: {champ_acc:.4f}")
print(f"  Weighted F1: {champ_f1:.4f}")
print("=" * 60)
print()

# ============================================================
# Cross-validation on winner
# ============================================================
print("5-fold CV on winner...")
if champ_name == "GradientBoosting":
    cv_model = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42)
elif champ_name == "LightGBM":
    cv_model = lgb.LGBMClassifier(n_estimators=300, max_depth=6, learning_rate=0.05,
        num_leaves=31, class_weight="balanced", random_state=42, verbose=-1, n_jobs=-1)
else:
    cv_model = xgb.XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05,
        objective="multi:softprob", num_class=n_classes, random_state=42, n_jobs=-1,
        eval_metric="mlogloss", verbosity=0)

cv_scores = cross_val_score(cv_model, X, y_enc,
    cv=StratifiedKFold(5, shuffle=True, random_state=42),
    scoring="f1_weighted", n_jobs=-1)
print(f"5-fold CV weighted F1: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
print()

# ============================================================
# Final report
# ============================================================
print("FINAL CLASSIFICATION REPORT:")
report = classification_report(y_test, champ_preds, target_names=class_names, digits=3, zero_division=0)
print(report)

# Per-class F1
per_class_f1 = {cls: f1_score(y_test == i, champ_preds == i, zero_division=0)
                for i, cls in enumerate(class_names)}
per_class_acc = {}
for i, cls in enumerate(class_names):
    mask = (y_test == i)
    if mask.sum() > 0:
        per_class_acc[cls] = (champ_preds[mask] == i).mean()

print("Per-class F1 (sorted):")
for cls, val in sorted(per_class_f1.items(), key=lambda x: -x[1]):
    print(f"  {cls:20s} {val:.3f}")
print()

# ============================================================
# Save artifacts (overwrite previous champion)
# ============================================================
joblib.dump(champ_model, f"{OUT_DIR}/lifecycle_model.pkl")
joblib.dump(encoders, f"{OUT_DIR}/feature_encoders.pkl")
joblib.dump(target_encoder, f"{OUT_DIR}/target_encoder.pkl")

with open(f"{OUT_DIR}/classification_report.txt", "w") as f:
    f.write(f"Model: {champ_name}\n\n")
    f.write(report)

# Update confusion matrix
cm = confusion_matrix(y_test, champ_preds)
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt="d",
            cmap=sns.light_palette(ORANGE, as_cmap=True),
            xticklabels=class_names, yticklabels=class_names,
            cbar_kws={"label": "Count"}, ax=ax,
            annot_kws={"size": 13, "weight": "bold"},
            linewidths=1, linecolor="white")
ax.set_xlabel("Predicted", fontsize=13, fontweight="bold", color=BLACK)
ax.set_ylabel("Actual", fontsize=13, fontweight="bold", color=BLACK)
ax.set_title(f"Confusion Matrix - {champ_name}", fontsize=16, fontweight="bold", color=BLACK, pad=15)
plt.xticks(rotation=30, ha="right", fontsize=11)
plt.yticks(fontsize=11)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/confusion_matrix.png", dpi=120, bbox_inches="tight", facecolor="white")
plt.close()

# Update feature importance
if hasattr(champ_model, "feature_importances_"):
    fi = pd.DataFrame({
        "feature": X.columns,
        "importance": champ_model.feature_importances_,
    }).sort_values("importance", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(fi["feature"], fi["importance"], color=ORANGE, edgecolor=BLACK, linewidth=0.8)
    ax.set_xlabel("Importance", fontsize=13, fontweight="bold", color=BLACK)
    ax.set_title(f"Feature Importance - {champ_name}", fontsize=16, fontweight="bold", color=BLACK, pad=15)
    plt.yticks(fontsize=11)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/feature_importance.png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close()
    top_features = fi.tail(10)[["feature","importance"]].to_dict("records")
else:
    top_features = []

# Final metrics
metrics = {
    "champion_model": champ_name,
    "test_accuracy": round(float(champ_acc), 4),
    "test_weighted_f1": round(float(champ_f1), 4),
    "cv_weighted_f1_mean": round(float(cv_scores.mean()), 4),
    "cv_weighted_f1_std": round(float(cv_scores.std()), 4),
    "all_models_compared": {
        "GradientBoosting": {"acc": round(float(gb_acc), 4), "f1": round(float(gb_f1), 4)},
        "LightGBM":         {"acc": round(float(lgb_acc), 4), "f1": round(float(lgb_f1), 4)},
        "XGBoost":          {"acc": round(float(xgb_acc), 4), "f1": round(float(xgb_f1), 4)},
    },
    "baselines": {
        "always_predict_majority_acc": 0.488,
        "always_predict_majority_f1": 0.320,
        "random_stratified_acc": 0.284,
    },
    "n_train": int(len(X_train)),
    "n_test": int(len(X_test)),
    "n_features": int(X.shape[1]),
    "n_classes": len(class_names),
    "class_names": class_names,
    "label_noise_pct": 4.0,
    "per_class_accuracy": {k: round(float(v), 4) for k, v in per_class_acc.items()},
    "per_class_f1": {k: round(float(v), 4) for k, v in per_class_f1.items()},
    "top_features": top_features,
}
with open(f"{OUT_DIR}/metrics.json", "w") as f:
    json.dump(metrics, f, indent=2, default=str)

# Save model config
joblib.dump({"feature_columns": list(X.columns),
             "model_name": champ_name,
             "class_names": class_names},
            f"{OUT_DIR}/model_config.pkl")

print(f"All artifacts saved to {OUT_DIR}")
print(f"Champion: {champ_name}")
