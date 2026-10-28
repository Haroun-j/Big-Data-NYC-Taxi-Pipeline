"""
Exploratory Data Analysis (EDA) for NYC Taxi fare prediction.

This script analyzes the data before training to understand:
- Data distribution
- Correlations between features and target
- Basic statistics
- Outlier detection
"""
import pandas as pd
import logging

from preprocessing import (load_data, validate_input_data,
                           minio_storage_options, validated_data_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def display_basic_info(df: pd.DataFrame) -> None:
    """
    Display basic information about the dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    """
    print("\n" + "=" * 60)
    print("1. INFORMATIONS GÉNÉRALES")
    print("=" * 60)
    print(f"Nombre de lignes    : {len(df):,}")
    print(f"Nombre de colonnes  : {len(df.columns)}")
    print(f"Mémoire utilisée    : {df.memory_usage().sum() / 1e9:.2f} GB")
    print("\nColonnes disponibles:")
    for col in df.columns:
        print(f"  - {col} ({df[col].dtype})")


def display_statistics(df: pd.DataFrame) -> None:
    """
    Display descriptive statistics for numeric columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    """
    print("\n" + "=" * 60)
    print("2. STATISTIQUES DESCRIPTIVES (colonnes numériques)")
    print("=" * 60)

    numeric_cols = ['total_amount', 'trip_distance', 'passenger_count',
                    'fare_amount', 'tip_amount']
    available_cols = [c for c in numeric_cols if c in df.columns]

    stats = df[available_cols].describe()
    print(stats.to_string())


def display_target_distribution(df: pd.DataFrame) -> None:
    """
    Display distribution of the target variable (total_amount).

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    """
    print("\n" + "=" * 60)
    print("3. DISTRIBUTION DE LA TARGET (total_amount)")
    print("=" * 60)

    target = df['total_amount']

    print(f"Minimum     : ${target.min():.2f}")
    print(f"Maximum     : ${target.max():.2f}")
    print(f"Moyenne     : ${target.mean():.2f}")
    print(f"Médiane     : ${target.median():.2f}")
    print(f"Écart-type  : ${target.std():.2f}")

    # Percentiles
    print("\nPercentiles:")
    for p in [25, 50, 75, 90, 95, 99]:
        print(f"  {p}% : ${target.quantile(p/100):.2f}")

    # Distribution par tranches
    print("\nDistribution par tranches de prix:")
    bins = [0, 10, 20, 30, 50, 100, 500]
    labels = ['0-10$', '10-20$', '20-30$', '30-50$', '50-100$', '100-500$']
    df['price_range'] = pd.cut(target, bins=bins, labels=labels)
    distribution = df['price_range'].value_counts().sort_index()
    total = len(df)
    for label, count in distribution.items():
        pct = count / total * 100
        print(f"  {label:10} : {count:>10,} ({pct:5.1f}%)")


def display_correlations(df: pd.DataFrame) -> None:
    """
    Display correlations between features and target.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    """
    print("\n" + "=" * 60)
    print("4. CORRÉLATIONS AVEC LA TARGET (total_amount)")
    print("=" * 60)

    numeric_cols = ['trip_distance', 'passenger_count', 'fare_amount',
                    'tip_amount', 'tolls_amount', 'extra', 'mta_tax']
    available_cols = [c for c in numeric_cols if c in df.columns]

    correlations = df[available_cols + ['total_amount']].corr()['total_amount']
    correlations = correlations.drop('total_amount').sort_values(ascending=False)

    print("\nCorrélation de Pearson avec total_amount:")
    for col, corr in correlations.items():
        bar = "█" * int(abs(corr) * 20)
        sign = "+" if corr > 0 else "-"
        print(f"  {col:25} : {sign}{abs(corr):.3f} {bar}")


def display_missing_values(df: pd.DataFrame) -> None:
    """
    Display missing values analysis.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    """
    print("\n" + "=" * 60)
    print("5. VALEURS MANQUANTES")
    print("=" * 60)

    missing = df.isnull().sum()
    total = len(df)

    if missing.sum() == 0:
        print("Aucune valeur manquante détectée.")
    else:
        for col, count in missing[missing > 0].items():
            pct = count / total * 100
            print(f"  {col:25} : {count:>10,} ({pct:.2f}%)")


def display_outliers(df: pd.DataFrame) -> None:
    """
    Display potential outliers in key columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    """
    print("\n" + "=" * 60)
    print("6. DÉTECTION D'OUTLIERS")
    print("=" * 60)

    # Outliers basés sur des règles métier
    outliers = {
        'total_amount <= 0': len(df[df['total_amount'] <= 0]),
        'total_amount > 500': len(df[df['total_amount'] > 500]),
        'trip_distance <= 0': len(df[df['trip_distance'] <= 0]),
        'trip_distance > 100': len(df[df['trip_distance'] > 100]),
        'passenger_count <= 0': len(df[df['passenger_count'] <= 0]),
        'passenger_count > 6': len(df[df['passenger_count'] > 6]),
    }

    total = len(df)
    for desc, count in outliers.items():
        pct = count / total * 100
        status = "warn" if pct > 1 else "ok"
        print(f"  {status} {desc:25} : {count:>10,} ({pct:.2f}%)")


def display_categorical_distribution(df: pd.DataFrame) -> None:
    """
    Display distribution of categorical features.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    """
    print("\n" + "=" * 60)
    print("7. DISTRIBUTION DES VARIABLES CATÉGORIELLES")
    print("=" * 60)

    # VendorID
    if 'VendorID' in df.columns:
        print("\nVendorID:")
        vendor_dist = df['VendorID'].value_counts()
        for vid, count in vendor_dist.items():
            pct = count / len(df) * 100
            print(f"  Vendor {vid}: {count:>10,} ({pct:.1f}%)")

    # Payment type
    if 'payment_type' in df.columns:
        print("\nPayment Type:")
        payment_names = {
            1: "Credit card",
            2: "Cash",
            3: "No charge",
            4: "Dispute",
            5: "Unknown",
            6: "Voided"
        }
        pay_dist = df['payment_type'].value_counts()
        for pid, count in pay_dist.items():
            name = payment_names.get(pid, f"Type {pid}")
            pct = count / len(df) * 100
            print(f"  {name:15}: {count:>10,} ({pct:.1f}%)")


def main():
    """
    Main EDA execution.
    """
    # Load data
    df = load_data(validated_data_path(), minio_storage_options())

    # Validate
    validate_input_data(df)

    # Run all EDA steps
    display_basic_info(df)
    display_statistics(df)
    display_target_distribution(df)
    display_correlations(df)
    display_missing_values(df)
    display_outliers(df)
    display_categorical_distribution(df)

    print("\n" + "=" * 60)
    print("EDA TERMINÉE - Prêt pour l'entraînement !")
    print("=" * 60)
    print("\nPour lancer l'entraînement : python train.py")


if __name__ == "__main__":
    main()
