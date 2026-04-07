import pandas as pd
import numpy as np
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import jenkspy

def get_representative_samples(rfm_df, segment_col, r_col, f_col, m_col, client_id_col, n=2):
    indices = rfm_df.groupby(segment_col).head(n).index
    return rfm_df.loc[indices, [client_id_col, r_col, f_col, m_col, segment_col]]


def perform_advanced_rfm(df, mapping):
    print("\n" + "=" * 50)
    print("МОДУЛЬ СЕГМЕНТАЦІЇ: JENKS  VS K-MEANS")
    d_col = mapping['date']
    id_col = mapping['client_id']
    s_col = mapping['sales_sum']

    latest_date = df[d_col].max()

    rfm = df.groupby(id_col).agg({
        d_col: lambda x: (latest_date - x.max()).days,
        id_col: 'count',
        s_col: 'sum'
    }).rename(columns={d_col: 'Recency', id_col: 'Frequency', s_col: 'Monetary'}).reset_index()
    ALL_STATUSES = [
        'Champions', 'Loyal Customers', 'Potential Loyalists',
        'At Risk (Big Spenders)', 'Hibernating', 'About to Sleep/Others'
    ]

    print("Розрахунок балів за методом Дженкса та Розмаху")
    r_min, r_max = rfm['Recency'].min(), rfm['Recency'].max()
    step = (r_max - r_min) / 5

    def get_jenks_score(series):
        breaks = jenkspy.jenks_breaks(series, n_classes=5)
        breaks = sorted(list(set(breaks)))
        def assign(val):
            for i in range(1, len(breaks)):
                if val <= breaks[i]: return i
            return len(breaks) - 1
        return series.apply(assign)

    rfm['R_Jenks'] = rfm['Recency'].apply(
        lambda x: 5 if x <= step else (4 if x <= step * 2 else (3 if x <= step * 3 else (2 if x <= step * 4 else 1))))
    rfm['F_Jenks'] = get_jenks_score(rfm['Frequency'])
    rfm['M_Jenks'] = get_jenks_score(rfm['Monetary'])

    def assign_segment(row):
        r, f, m = row['R_Jenks'], row['F_Jenks'], row['M_Jenks']
        if r >= 4 and f >= 4 and m >= 4: return 'Champions'
        if f >= 3 and m >= 3: return 'Loyal Customers'
        if r >= 4 and f <= 2: return 'Potential Loyalists'
        if r <= 2 and m >= 4: return 'At Risk (Big Spenders)'
        if r <= 2 and f <= 2 and m <= 2: return 'Hibernating'
        return 'About to Sleep/Others'

    rfm['Segment_Jenks'] = rfm.apply(assign_segment, axis=1)
    print("Кластеризація алгоритмом K-Means")
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(rfm[['Recency', 'Frequency', 'Monetary']])
    kmeans = KMeans(n_clusters=6, init='k-means++', random_state=42, n_init=10)
    rfm['Cluster'] = kmeans.fit_predict(x_scaled)
    cluster_order = rfm.groupby('Cluster')['Monetary'].mean().sort_values().index
    cluster_names = {
        cluster_order[5]: 'Champions',
        cluster_order[4]: 'Loyal Customers',
        cluster_order[3]: 'At Risk (Big Spenders)',
        cluster_order[2]: 'Potential Loyalists',
        cluster_order[1]: 'About to Sleep/Others',
        cluster_order[0]: 'Hibernating'
    }
    rfm['Segment_KMeans'] = rfm['Cluster'].map(cluster_names)
    rfm['Segment_Jenks'] = pd.Categorical(rfm['Segment_Jenks'], categories=ALL_STATUSES)
    rfm['Segment_KMeans'] = pd.Categorical(rfm['Segment_KMeans'], categories=ALL_STATUSES)

    accuracy = (rfm['Segment_Jenks'].astype(str) == rfm['Segment_KMeans'].astype(str)).mean() * 100
    comparison_matrix = pd.crosstab(rfm['Segment_Jenks'], rfm['Segment_KMeans'], dropna=False)

    print(f"Схожість методів складає {accuracy:.2f}%")
    return rfm, comparison_matrix, accuracy


if __name__ == "__main__":
    from preprocessing import run_preparation_pipeline
    if not os.path.exists('data'):
        os.makedirs('data')
    df_raw, _, mapping = run_preparation_pipeline('Data.xlsx')
    rfm_results, comp_matrix, acc_val = perform_advanced_rfm(df_raw, mapping)
    jenks_summary = rfm_results['Segment_Jenks'].value_counts().reindex(
        rfm_results['Segment_Jenks'].cat.categories).reset_index()
    jenks_summary.columns = ['Статус (Jenks)', 'Кількість']
    kmeans_summary = rfm_results['Segment_KMeans'].value_counts().reindex(
        rfm_results['Segment_KMeans'].cat.categories).reset_index()
    kmeans_summary.columns = ['Статус (K-Means)', 'Кількість']
    print("\nГенерація репрезентативних вибірок")
    sample_jenks = get_representative_samples(rfm_results, 'Segment_Jenks', 'R_Jenks', 'F_Jenks', 'M_Jenks',
                                              mapping['client_id'])
    sample_kmeans = get_representative_samples(rfm_results, 'Segment_KMeans', 'Recency', 'Frequency', 'Monetary',
                                               mapping['client_id'])
    output_path = 'data/rfm_final_report.xlsx'

    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            rfm_results.to_excel(writer, sheet_name='Повні_Дані_RFM', index=False)
            comp_matrix.to_excel(writer, sheet_name='Матриця_Порівняння')
            jenks_summary.to_excel(writer, sheet_name='Підсумки_Jenks', index=False)
            kmeans_summary.to_excel(writer, sheet_name='Підсумки_KMeans', index=False)
            sample_jenks.to_excel(writer, sheet_name='Вибірка_Jenks', index=False)
            sample_kmeans.to_excel(writer, sheet_name='Вибірка_KMeans', index=False)

            pd.DataFrame({
                'Параметр': ['Загальна кількість клієнтів', 'Схожість методів (%)', 'Кількість сегментів'],
                'Значення': [len(rfm_results), round(acc_val, 2), 6]
            }).to_excel(writer, sheet_name='Точність_Моделі', index=False)

        print(f"\nАНАЛІЗ ЗАВЕРШЕНО. Звіт збережено: {output_path}")
        print(f"Фінальна схожість методів: {acc_val:.1f}%")

    except Exception as e:
        print(f"\nПомилка при збереженні звіту RFM: {e}")
        print("Переконайтеся, що файл rfm_final_report.xlsx не відкритий в Excel!")