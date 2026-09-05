"""
Dataset Loader for ML Studio Feature Selection Research Track (SRS §9).

Loads and caches the 4 benchmark datasets:
1. California Housing (Regression) - scikit-learn / 1990 US Census
2. Bike Sharing Demand (Regression) - UCI Machine Learning Repository #275
3. Breast Cancer Wisconsin Diagnostic (Classification) - scikit-learn / UCI #17
4. Adult Census Income (Classification) - UCI Machine Learning Repository #2

Citations and Dataset Provenance:
- California Housing:
    Pace, R. Kelley and Ronald Barry, "Sparse Spatial Autoregressions,"
    Statistics and Probability Letters, 33 (1997) 291-297.
    Source: sklearn.datasets.fetch_california_housing (derived from 1990 US Census).
- Bike Sharing:
    Fanaee-T, Hadi, and Gama, Joao, "Event labeling combining ensemble detectors and background knowledge",
    Progress in Artificial Intelligence (2013): pp. 1-15, Springer Berlin Heidelberg,
    DOI: 10.1007/s13748-013-0040-3.
    Source URL: https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip
- Breast Cancer Wisconsin (Diagnostic):
    Wolberg, W.H., Street, W.N., & Mangasarian, O.L. (1995).
    Breast Cancer Wisconsin (Diagnostic) Data Set. UCI Machine Learning Repository.
    Source: sklearn.datasets.load_breast_cancer.
- Adult Census Income:
    Kohavi, Ronny and Becker, Barry. (1996). Adult. UCI Machine Learning Repository.
    Source URL: https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data
"""

import io
import os
import urllib.request
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.datasets import fetch_california_housing, load_breast_cancer

DEFAULT_CACHE_DIR = Path(__file__).parent / "data"


def load_california_housing(
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
) -> tuple[pd.DataFrame, pd.Series, str]:
    """
    Loads California Housing regression dataset.
    
    Returns:
        X (pd.DataFrame): 8 continuous spatial and demographic features.
        y (pd.Series): Median house value in $100,000s.
        task_type (str): "REGRESSION"
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    csv_file = cache_path / "california_housing.csv"

    if csv_file.exists():
        df = pd.read_csv(csv_file)
    else:
        raw = fetch_california_housing(as_frame=True)
        df = raw.frame
        df.to_csv(csv_file, index=False)

    target_col = "MedHouseVal"
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return X, y, "REGRESSION"


def load_bike_sharing(
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    frequency: str = "hour",
) -> tuple[pd.DataFrame, pd.Series, str]:
    """
    Loads UCI Bike Sharing Demand regression dataset.
    Removes leakage columns ('casual', 'registered' which sum to target 'cnt')
    and record identifiers ('instant', 'dteday').

    Returns:
        X (pd.DataFrame): 12 weather and temporal features.
        y (pd.Series): Total count of rental bikes ('cnt').
        task_type (str): "REGRESSION"
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    csv_filename = f"bike_sharing_{frequency}.csv"
    csv_file = cache_path / csv_filename

    if not csv_file.exists():
        url = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            z = zipfile.ZipFile(io.BytesIO(resp.read()))
            inner_file = f"{frequency}.csv"
            df_raw = pd.read_csv(z.open(inner_file))
            df_raw.to_csv(csv_file, index=False)
    else:
        df_raw = pd.read_csv(csv_file)

    leakage_and_id_cols = ["instant", "dteday", "casual", "registered"]
    target_col = "cnt"

    cols_to_drop = [c for c in leakage_and_id_cols + [target_col] if c in df_raw.columns]
    X = df_raw.drop(columns=cols_to_drop)
    y = df_raw[target_col].astype(float)
    return X, y, "REGRESSION"


def load_breast_cancer(
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
) -> tuple[pd.DataFrame, pd.Series, str]:
    """
    Loads Breast Cancer Wisconsin (Diagnostic) classification dataset.

    Returns:
        X (pd.DataFrame): 30 morphological cell nucleus features.
        y (pd.Series): Binary target (1 = benign, 0 = malignant).
        task_type (str): "CLASSIFICATION"
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    csv_file = cache_path / "breast_cancer.csv"

    if csv_file.exists():
        df = pd.read_csv(csv_file)
    else:
        raw = load_breast_cancer(as_frame=True)
        df = raw.frame
        df.to_csv(csv_file, index=False)

    target_col = "target"
    X = df.drop(columns=[target_col])
    y = df[target_col].astype(int)
    return X, y, "CLASSIFICATION"


def load_adult_income(
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
) -> tuple[pd.DataFrame, pd.Series, str]:
    """
    Loads UCI Adult Census Income classification dataset.
    Categorical attributes are one-hot encoded to yield a clean numerical
    design matrix for feature selection and downstream models.

    Returns:
        X (pd.DataFrame): Numerical design matrix.
        y (pd.Series): Binary target (1 for income > 50K, 0 for <= 50K).
        task_type (str): "CLASSIFICATION"
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    csv_file = cache_path / "adult_income.csv"

    if not csv_file.exists():
        url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            cols = [
                "age", "workclass", "fnlwgt", "education", "education_num",
                "marital_status", "occupation", "relationship", "race", "sex",
                "capital_gain", "capital_loss", "hours_per_week", "native_country",
                "income"
            ]
            df_raw = pd.read_csv(
                io.BytesIO(resp.read()),
                header=None,
                names=cols,
                skipinitialspace=True
            )
            df_raw.to_csv(csv_file, index=False)
    else:
        df_raw = pd.read_csv(csv_file, skipinitialspace=True)

    # Clean whitespace strings
    for col in df_raw.columns:
        if df_raw[col].dtype == object or isinstance(df_raw[col].dtype, pd.StringDtype):
            df_raw[col] = df_raw[col].astype(str).str.strip()

    # Target: 1 if >50K else 0
    y = (df_raw["income"].str.contains(">50K", regex=False)).astype(int)
    y.name = "income_above_50k"

    # Preprocess features: One-hot encode categorical variables
    X_raw = df_raw.drop(columns=["income"])
    X = pd.get_dummies(X_raw, drop_first=True, dtype=float)
    return X, y, "CLASSIFICATION"


DATASET_LOADERS = {
    "california_housing": load_california_housing,
    "bike_sharing": load_bike_sharing,
    "breast_cancer": load_breast_cancer,
    "adult_income": load_adult_income,
}


def load_dataset(
    name: str, cache_dir: str | Path = DEFAULT_CACHE_DIR
) -> tuple[pd.DataFrame, pd.Series, str]:
    """
    Unified dataset dispatcher by name.
    """
    norm_name = name.lower().replace("-", "_").replace(" ", "_")
    if norm_name not in DATASET_LOADERS:
        valid = list(DATASET_LOADERS.keys())
        raise ValueError(f"Unknown dataset '{name}'. Available datasets: {valid}")
    return DATASET_LOADERS[norm_name](cache_dir=cache_dir)
