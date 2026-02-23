import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from utils.logger import logger


def load_data(csv_name):
    logger.debug("load_data: Starting load_data script")
    try:
        data = pd.read_csv(csv_name, thousands=",", quotechar='"')
        df = data.copy()
        if df.empty or len(df.columns) == 0:
            print(f"Warning: Worksheet '{csv_name}' is empty or has no data rows.")
            return None

        if "Date" not in df.columns:
            print(f"ERROR: 'Date' column not found in '{csv_name}'.")
            return None

        formats_to_try = [
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]
        parsed_date = False
        original_dates = df["Date"].copy()
        logger.debug("load_data: Starting load_data script")
        for fmt in formats_to_try:
            try:
                df["Date"] = pd.to_datetime(original_dates, format=fmt, errors="coerce")
                if not df["Date"].isnull().all():
                    parsed_date = True
                    break
            except Exception:
                continue

        if not parsed_date:
            df["Date"] = pd.to_datetime(original_dates, errors="coerce")

        df.dropna(subset=["Date"], inplace=True)

        if not df.empty:
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)
        else:
            return None
        required_col = "Close"
        if required_col not in df.columns:
            print(f"ERROR: Required column '{required_col}' not found.")
            return None
        df[required_col] = df[required_col].replace(["-", "", " ", "#N/A"], np.nan)
        df[required_col] = pd.to_numeric(df[required_col], errors="coerce")
        df.dropna(subset=[required_col], inplace=True)
        for col in ["Open", "High", "Low", "Volume"]:
            if col in df.columns:
                df[col] = df[col].replace(["-", "", " ", "#N/A"], np.nan)
                df[col] = pd.to_numeric(df[col], errors="coerce").ffill()

        if df.empty:
            print(
                f"Warning: DataFrame for '{csv_name}' became empty after preprocessing."
            )
            return None

        print(f"Successfully loaded and preprocessed ({len(df)} rows).")
        return df

    except Exception as e:
        print(f"ERROR loading '{csv_name}': {str(e)}")
        return None


def plot_transition_matrix(matrix, labels):
    """Create a heatmap of the transition matrix"""
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        matrix,
        annot=True,
        cmap="YlGnBu",
        fmt=".2f",
        xticklabels=labels,
        yticklabels=labels,
        cbar=True,
        vmin=0,
        vmax=1,
    )
    plt.title("Transition Probability Matrix")
    plt.xlabel("Next State")
    plt.ylabel("Current State")
    plt.tight_layout()
    plt.show()
