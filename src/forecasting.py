import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


def run_forecast_logic(df_filtered, target_col, d_col, train_years, n_months, label):
    if df_filtered.empty: return None
    df_ts = df_filtered.set_index(d_col).resample('ME')[target_col].sum().reset_index()
    mean_val = df_ts[target_col].mean()
    std_val = df_ts[target_col].std()
    cv = (std_val / mean_val) if mean_val > 0 else 0
    if cv <= 0.15:
        xyz_class = 'X (Стабільний)'
    elif cv <= 0.35:
        xyz_class = 'Y (Мінливий)'
    else:
        xyz_class = 'Z (Випадковий)'

    df_ts['Year'] = df_ts[d_col].dt.year
    df_ts['Month'] = df_ts[d_col].dt.month
    df_ts['Lag_1'] = df_ts[target_col].shift(1)
    df_ts = df_ts.dropna()

    train_data = df_ts[df_ts['Year'].isin(train_years)]
    test_data = df_ts[~df_ts['Year'].isin(train_years)].head(n_months)

    if test_data.empty or train_data.empty or len(train_data) < 3:
        return None

    X_train, y_train = train_data[['Lag_1', 'Month']], train_data[target_col]
    X_test, y_test = test_data[['Lag_1', 'Month']], test_data[target_col]

    model_rf = RandomForestRegressor(n_estimators=100, random_state=42)
    model_rf.fit(X_train, y_train)
    preds_rf = model_rf.predict(X_test)
    model_lr = LinearRegression()
    model_lr.fit(X_train, y_train)
    preds_lr = model_lr.predict(X_test)


    def safe_mape(true, pred):
        return np.mean(np.abs((true - pred) / (true + 1))) * 100

    mape_rf = safe_mape(y_test, preds_rf)
    mape_lr = safe_mape(y_test, preds_lr)

    monthly_details = []
    for i in range(len(test_data)):
        monthly_details.append({
            'Дата': test_data.iloc[i][d_col].strftime('%Y-%m'),
            'Об\'єкт': label,
            'Реальний Факт': round(y_test.values[i], 2),
            'Прогноз RF': round(preds_rf[i], 2),
            'Прогноз LR': round(preds_lr[i], 2),
            'Помилка RF (%)': round(abs(y_test.values[i] - preds_rf[i]) / (y_test.values[i] + 1) * 100, 2)
        })

    # Побудова графіка
    plt.figure(figsize=(10, 5))
    plt.plot(train_data[d_col], train_data[target_col], label='Історія', alpha=0.4)
    plt.plot(test_data[d_col], y_test, 'g-s', label='Факт (Тест)')
    plt.plot(test_data[d_col], preds_rf, 'r--x', label=f'Random Forest (MAPE: {mape_rf:.1f}%)')
    plt.plot(test_data[d_col], preds_lr, 'b--+', label=f'Linear Regression (MAPE: {mape_lr:.1f}%)')
    plt.title(f'Прогноз: {label} | Клас стійкості: {xyz_class}')
    plt.legend()
    plt.grid(True, alpha=0.3)

    folder = 'data/forecast_plots'
    if not os.path.exists(folder): os.makedirs(folder)
    plt.savefig(f"{folder}/{label.replace('/', '_')}.png")
    plt.close()

    # Визначаємо кращу модель
    best_model = "Random Forest" if mape_rf < mape_lr else "Linear Regression"

    summary_row = {
        'Об\'єкт': label,
        'XYZ Клас': xyz_class,
        'CV (Коеф. варіації)': round(cv, 3),
        'MAPE RF (%)': round(mape_rf, 2),
        'MAPE LR (%)': round(mape_lr, 2),
        'Точність Кращої Моделі (%)': round(max(0, 100 - min(mape_rf, mape_lr)), 2),
        'Краща модель': best_model,
        'Реальний Факт (період)': round(y_test.sum(), 2),
        'Прогноз (період)': round((preds_rf.sum() if best_model == "Random Forest" else preds_lr.sum()), 2)
    }

    return summary_row, monthly_details


def perform_flexible_forecast(df, mapping):
    print(" КОМПЛЕКСНЕ ПРОГНОЗУВАННЯ ТА АНАЛІЗ СТІЙКОСТІ")
    d_col = mapping['date']
    df[d_col] = pd.to_datetime(df[d_col])
    print("\nОберіть розріз аналізу (напр. PRODUCTLINE):")
    for i, col in enumerate(df.columns): print(f"{i}: {col}")
    filter_idx = int(input("Введіть номер (або -1 для загального): "))

    targets_to_analyze = []
    filter_col = None

    if filter_idx != -1:
        filter_col = df.columns[filter_idx]
        unique_vals = sorted(df[filter_col].unique().astype(str))
        print(f"\nДоступні значення: {unique_vals}")
        user_input = input("Значення через кому або 'ALL': ").strip()
        targets_to_analyze = unique_vals if user_input.upper() == 'ALL' else [v.strip() for v in user_input.split(',')]
    else:
        targets_to_analyze = ['Загальні продажі']

    # 2. ОБРАННЯ ПОКАЗНИКА
    print("\n Що прогнозуємо? (0: Sales, 1: Qty)")
    target_choice = int(input("Введіть 0 або 1: "))
    target_col = mapping['sales_sum'] if target_choice == 0 else mapping['quantity']

    # 3. НАЛАШТУВАННЯ ПЕРІОДІВ
    years = sorted(df[d_col].dt.year.unique())
    print(f"\n Доступні роки: {years}")
    train_years = [int(y.strip()) for y in input("Роки для НАВЧАННЯ (напр. 2003,2004): ").split(',')]
    n_months = int(input("Кількість місяців для ТЕСТУ (напр. 5): "))

    summaries = []
    detailed_forecasts = []

    for label in targets_to_analyze:
        df_sub = df.copy() if filter_idx == -1 else df[df[filter_col].astype(str) == label].copy()
        res = run_forecast_logic(df_sub, target_col, d_col, train_years, n_months, label)
        if res:
            summaries.append(res[0])
            detailed_forecasts.extend(res[1])

    if not summaries: return None, None

    final_report = pd.DataFrame(summaries)
    detailed_report = pd.DataFrame(detailed_forecasts)

    # Візуалізація порівняння точності по об'єктах
    if len(final_report) > 1:
        plt.figure(figsize=(12, 6))
        x = np.arange(len(final_report))
        width = 0.35
        plt.bar(x - width / 2, final_report['MAPE RF (%)'], width, label='MAPE Random Forest', color='salmon')
        plt.bar(x + width / 2, final_report['MAPE LR (%)'], width, label='MAPE Linear Regression', color='skyblue')
        plt.xticks(x, final_report['Об\'єкт'], rotation=45)
        plt.ylabel('Помилка MAPE (%)')
        plt.title('Порівняльний аналіз точності моделей')
        plt.legend()
        plt.tight_layout()
        plt.savefig('data/model_comparison_mape.png')
        plt.show()

    return final_report, detailed_report


if __name__ == "__main__":
    from preprocessing import run_preparation_pipeline

    if not os.path.exists('data'):
        os.makedirs('data')

    df_raw, _, mapping = run_preparation_pipeline('Data.xlsx')
    report, details = perform_flexible_forecast(df_raw, mapping)

    if report is not None:
        print("\nПОРІВНЯЛЬНА ТАБЛИЦЯ ТОЧНОСТІ МОДЕЛЕЙ ТА АНАЛІЗ СТІЙКОСТІ:")
        print(report[['Об\'єкт', 'XYZ Клас', 'MAPE RF (%)', 'MAPE LR (%)', 'Краща модель']])

        output_path = 'data/forecast_comparative_analysis.xlsx'

        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                report.to_excel(writer, sheet_name='Підсумковий_Аналіз', index=False)
                details.to_excel(writer, sheet_name='Прогноз_по_місяцях', index=False)

            print(f"\nРезультати успішно збережено: '{output_path}' (2 аркуші)")

        except Exception as e:
            print(f"\nПомилка при збереженні файлу прогнозу: {e}")
