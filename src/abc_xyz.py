import pandas as pd
import numpy as np
import os
from preprocessing import run_preparation_pipeline

def perform_enhanced_abc_xyz(df, mapping):
    print("ЗАПУСК ІНТЕГРОВАНОЇ МОДЕЛІ: ABC(2D) + XYZ + SCORE")
    user_filter = input("\nБажаєте відфільтрувати дані? (наприклад, Shipped) (y/n): ").lower()
    if user_filter == 'y':
        print("\nОберіть колонку для фільтрації:")
        for i, col in enumerate(df.columns): print(f"{i}: {col}")
        f_idx = int(input("Номер колонки: "))
        f_col = df.columns[f_idx]
        print(f"Унікальні значення: {df[f_col].unique()}")
        val = input(f"Значення для залишення: ")
        df = df[df[f_col].astype(str) == val].copy()
    print("\nОберіть колонку для аналізу (наприклад, PRODUCTLINE):")
    for i, col in enumerate(df.columns): print(f"{i}: {col}")
    cat_idx = int(input("Введіть номер: "))
    cat_col = df.columns[cat_idx]
    s_col = mapping['sales_sum']
    q_col = mapping['quantity']
    abc_data = df.groupby(cat_col).agg({s_col: 'sum', q_col: 'sum'}).reset_index()
    abc_data = abc_data.sort_values(by=s_col, ascending=False)
    abc_data['Дохід_%'] = abc_data[s_col] / abc_data[s_col].sum()
    abc_data['Кумулятивна_1'] = abc_data['Дохід_%'].cumsum()
    abc_data['Група_Sales'] = abc_data['Кумулятивна_1'].apply(
        lambda x: 'A' if x <= 0.8 else ('B' if x <= 0.95 else 'C'))

    abc_data['Кількість_%'] = abc_data[q_col] / abc_data[q_col].sum()
    abc_data['Кумулятивна_2'] = abc_data['Кількість_%'].cumsum()
    abc_data['Група_Qty'] = abc_data['Кумулятивна_2'].apply(lambda x: 'A' if x <= 0.8 else ('B' if x <= 0.95 else 'C'))
    abc_data['ABC_2D'] = abc_data['Група_Sales'] + abc_data['Група_Qty']
    monthly = df.groupby([cat_col, 'ORDER_YEAR', 'ORDER_MONTH'])[s_col].sum().reset_index()
    xyz_stats = monthly.groupby(cat_col)[s_col].agg(['std', 'mean']).reset_index()
    xyz_stats['CV'] = np.where(xyz_stats['mean'] == 0, 0, xyz_stats['std'] / xyz_stats['mean'])

    def get_xyz(cv):
        if cv <= 0.10: return 'X'
        if cv <= 0.25: return 'Y'
        return 'Z'
    xyz_stats['XYZ_Class'] = xyz_stats['CV'].apply(get_xyz)
    final_df = abc_data.merge(xyz_stats[[cat_col, 'CV', 'XYZ_Class']], on=cat_col)
    score_map = {'A': 3, 'B': 2, 'C': 1}
    xyz_map = {'X': 3, 'Y': 2, 'Z': 1}
    final_df['Integral_Score'] = (
            final_df['Група_Sales'].map(score_map) +
            final_df['Група_Qty'].map(score_map) +
            final_df['XYZ_Class'].map(xyz_map)
    )
    priority_map = {
        'AA': '1 група (Високий)', 'BA': '2 група', 'CA': '2 група',
        'AB': '2 група', 'AC': '2 група', 'BB': '3 група',
        'BC': '3 група', 'CB': '3 група', 'CC': '4 група'
    }
    final_df['Priority'] = final_df['ABC_2D'].map(priority_map)
    final_df['Final_Category'] = final_df['ABC_2D'] + final_df['XYZ_Class']

    group_aa = final_df[final_df['ABC_2D'] == 'AA']
    items_pct = (len(group_aa) / len(final_df)) * 100
    sales_pct = group_aa['Дохід_%'].sum() * 100

    print("\n" + "-" * 30)
    print(f"АНАЛІЗ ПАРЕТО: {items_pct:.1f}% товарів дають {sales_pct:.1f}% доходу.")
    print("-" * 30)
    print("МАТРИЦЯ РОЗПОДІЛУ КАТЕГОРІЙ (ABC 2D)")

    rows = ['A', 'B', 'C']
    cols = ['A', 'B', 'C']
    matrix_data = []

    total_cats = len(final_df)

    for r in rows:
        matrix_row = []
        for c in cols:
            cell_cats = final_df[(final_df['Група_Sales'] == r) & (final_df['Група_Qty'] == c)]
            names = ", ".join(cell_cats[cat_col].tolist())
            count = len(cell_cats)
            pct = (count / total_cats) * 100

            cell_text = f"{r}{c}: {pct:.0f}% ({names})" if count > 0 else f"{r}{c}: -"
            matrix_row.append(cell_text)
        matrix_data.append(matrix_row)

    matrix_df = pd.DataFrame(matrix_data, index=['A(дохід)', 'B(дохід)', 'C(дохід)'],
                             columns=['A(кількість)', 'B(кількість)', 'C(кількість)'])

    print(matrix_df)
    return final_df, cat_col,matrix_df


if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')

    rfm_ready, _, mapping = run_preparation_pipeline('Data.xlsx')
    result, cat_col, matrix = perform_enhanced_abc_xyz(rfm_ready, mapping)
    print("\nПІДСУМКОВИЙ РЕЙТИНГ МОДЕЛІ:")
    output_cols = [cat_col, 'Final_Category', 'Integral_Score', 'Priority', 'CV']
    sorted_res = result.sort_values('Integral_Score', ascending=False)
    print(sorted_res[output_cols])
    output_path = 'data/abc_xyz_full_report.xlsx'
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            sorted_res.to_excel(writer, sheet_name='Повний_аналіз', index=False)
            matrix.to_excel(writer, sheet_name='Матриця_ABC')
        print(f"\nЗвіт з матрицею збережено у '{output_path}' (див. вкладку 'Матриця_ABC')")
    except Exception as e:
        print(f"\nПомилка при збереженні '{output_path}': {e}")

 
    model_path = 'data/final_abc_xyz_full_model.xlsx'
    try:
        sorted_res.to_excel(model_path, index=False)
        print(f"Повний звіт збережено у '{model_path}'")
    except Exception as e:
        print(f"Помилка при збереженні '{model_path}': {e}")
