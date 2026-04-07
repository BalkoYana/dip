import pandas as pd
import os
COLUMN_HINTS = {
    'client_id': ['CUSTOMERNAME', 'CLIENT_ID', 'CONTACTLASTNAME', 'ID_CUSTOMER'],
    'sales_sum': ['SALES', 'TOTAL_AMOUNT', 'REVENUE', 'SUM', 'PRICEEACH'],
    'quantity': ['QUANTITYORDERED', 'QTY', 'COUNT', 'AMOUNT'],
    'date': ['ORDERDATE', 'DATE', 'TRANSACTION_DATE']
}
def get_column_mapping(df):
    selected_cols = {}
    for key, synonyms in COLUMN_HINTS.items():
        match = next((col for col in df.columns if col.upper() in [s.upper() for s in synonyms]), None)
        if match:
            confirm = input(f"Знайдено потенційну колонку для '{key}': [{match}]. Використати її? (y/n): ").lower()
            if confirm == 'y':
                selected_cols[key] = match
                continue
        print(f"\nОберіть колонку для '{key}':")
        for i, col in enumerate(df.columns):
            print(f"{i}: {col}")
        choice = int(input(f"Введіть номер: "))
        selected_cols[key] = df.columns[choice]
    return selected_cols
def get_cleaning_settings(df):
    temp_df = df.replace(r'^\s*$', pd.NA, regex=True)
    settings = {}
    cols_with_nans = temp_df.columns[temp_df.isnull().any()].tolist()
    if not cols_with_nans:
        print("\nПропусків у даних не виявлено.")
        return settings
    print("\nНалаштування обробки пропусків")
    print(f"Знайдено пропуски у {len(cols_with_nans)} колонках.\n")
    for col in cols_with_nans:
        nan_count = temp_df[col].isnull().sum()
        is_numeric = pd.api.types.is_numeric_dtype(temp_df[col])
        if is_numeric:
            suggestion = "0 або середнє значення"
            default = "0"
        else:
            suggestion = "'Unknown', 'None' або 'International'"
            default = "Unknown"

        print(f"Колонка: [{col}]")
        print(f"Кількість пропусків: {nan_count} ({round(nan_count / len(temp_df) * 100, 2)}%)")
        print(f"Тип даних: {'Числовий' if is_numeric else 'Текстовий/Об’єкт'}")
        user_val = input(
            f"   Введіть значення для заміни (пропозиція {suggestion}, за замовчуванням '{default}'): ").strip()
        if is_numeric and not user_val:
            settings[col] = 0
        elif not user_val:
            settings[col] = default
        else:
            if is_numeric:
                try:
                    settings[col] = float(user_val.replace(',', '.'))
                except ValueError:
                    settings[col] = user_val
            else:
                settings[col] = user_val
        print("-" * 30)

    return settings

def clean_base_data(df, selected_cols, cleaning_settings):
    new_df = df.copy()
    new_df = new_df.replace(r'^\s*$', pd.NA, regex=True)
    date_col = selected_cols['date']
    new_df[date_col] = pd.to_datetime(new_df[date_col], errors='coerce')
    critical = [selected_cols['client_id'], date_col]
    new_df.dropna(subset=critical, inplace=True)
    for col, value in cleaning_settings.items():
        if col in new_df.columns:
            new_df[col] = new_df[col].fillna(value)
    for col in new_df.columns:
        if col in [selected_cols['sales_sum'], selected_cols['quantity']]:
            continue
        if new_df[col].isnull().any():
            if pd.api.types.is_numeric_dtype(new_df[col]):
                new_df[col] = new_df[col].fillna(0)
            else:
                new_df[col] = new_df[col].fillna("Unknown")

    return new_df

def enrich_data(df, selected_cols):
    df = df.copy()
    s_col = selected_cols['sales_sum']
    q_col = selected_cols['quantity']
    d_col = selected_cols['date']
    df['REALPRICEEACH'] = df.apply(
        lambda x: x[s_col] / x[q_col] if x[q_col] > 0 else 0, axis=1
    )
    df['ORDER_MONTH'] = df[d_col].dt.month
    df['ORDER_YEAR'] = df[d_col].dt.year
    return df

def prepare_for_scoring(df, selected_cols):
    scoring_df = df.copy()
    for col in [selected_cols['sales_sum'], selected_cols['quantity']]:
        if scoring_df[col].dtype == 'object':
            scoring_df[col] = scoring_df[col].astype(str).str.replace(',', '.').astype(float)
        scoring_df[col] = scoring_df[col].fillna(0)
    return scoring_df

def prepare_for_stats(df, selected_cols):
    stats_df = df.copy()
    s_col = selected_cols['sales_sum']
    if stats_df[s_col].dtype == 'object':
        stats_df[s_col] = stats_df[s_col].astype(str).str.replace(',', '.').astype(float)
    stats_df.dropna(subset=[s_col], inplace=True)
    return stats_df

def run_preparation_pipeline(file_path):
    if file_path.endswith(('.xlsx', '.xls')):
        df_raw = pd.read_excel(file_path)
    else:
        df_raw = pd.read_csv(file_path, sep=None, engine='python')

    cols = get_column_mapping(df_raw)
    clean_settings = get_cleaning_settings(df_raw)
    df_base = clean_base_data(df_raw, cols, clean_settings)
    df_enriched = enrich_data(df_base, cols)
    df_rfm_ready = prepare_for_scoring(df_enriched, cols)
    df_stats_ready = prepare_for_stats(df_enriched, cols)
    output_folder = 'data'
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    rfm_path = os.path.join(output_folder, 'cleaned_rfm_data.xlsx')
    stats_path = os.path.join(output_folder, 'cleaned_stats_data.xlsx')
    df_rfm_ready.to_excel(rfm_path, index=False)
    df_stats_ready.to_excel(stats_path, index=False)
    print(f"Результати збережено у '{output_folder}'")
    return df_rfm_ready, df_stats_ready, cols
if __name__ == "__main__":
    rfm_data, stat_data, mapping = run_preparation_pipeline('Data.xlsx')