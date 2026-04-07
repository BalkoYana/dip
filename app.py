import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))


def main_menu():
    DATA_FILE = os.path.join(os.getcwd(), 'src', 'Data.xlsx')
    prepared_data = None
    data_mapping = None

    try:
        from preprocessing import run_preparation_pipeline
        from abc_xyz import perform_enhanced_abc_xyz
        from rfm import perform_advanced_rfm
        from forecasting import perform_flexible_forecast
    except ImportError as e:
        print(f"Помилка імпорту модулів: {e}. Перевірте наявність файлів у папці 'src'.")
        return

    while True:
        print("ІНФОРМАЦІЙНА СИСТЕМА АНАЛІЗУ ПРОДАЖІВ (B2B)")
        status = "ДАНІ ГОТОВІ" if prepared_data is not None else "ПОТРІБНА ПІДГОТОВКА"
        print(f"Статус системи: {status}")

        print("1. Підготовка та очищення даних (Крок 1)")
        print("2. ABC-XYZ аналіз категорій")
        print("3. RFM-сегментація клієнтів")
        print("4. Прогнозування продажів (RF vs LR)")
        print("5. Формування аналітичних рекомендацій")
        print("0. Вихід")
        choice = input("Оберіть дію (0-5): ")

        if choice == '1':
            prepared_data, _, data_mapping = run_preparation_pipeline(DATA_FILE)
            print(f"Очищені дані збережено у 'data/cleaned_rfm_data.xlsx'")

        elif choice in ['2', '3', '4']:
            if prepared_data is None:
                print("\nПОМИЛКА: Спочатку виконайте Крок 1!")
                continue

            if choice == '2':
                result, cat_col, matrix = perform_enhanced_abc_xyz(prepared_data, data_mapping)
                print("\n АНАЛІЗ ЗАВЕРШЕНО")
                print(f" Повний звіт збережено у 'data/final_abc_xyz_full_model.xlsx'")
                print(f" Матриця розподілу доступна у 'data/abc_xyz_full_report.xlsx'")

            elif choice == '3':
                rfm_results, comp_matrix, acc_val = perform_advanced_rfm(prepared_data, data_mapping)
                print(f"\n СЕГМЕНТАЦІЯ ЗАВЕРШЕНА (Схожість методів: {acc_val:.1f}%)")
                print(f" Повний звіт RFM збережено у 'data/rfm_final_report.xlsx'")

            elif choice == '4':
                report, details = perform_flexible_forecast(prepared_data, data_mapping)
                if report is not None:
                    print("\n ПРОГНОЗУВАННЯ ЗАВЕРШЕНО")
                    print(f" Результати збережено у 'data/forecast_comparative_analysis.xlsx' (2 аркуші)")

        elif choice == '5':
            print("\n Запуск генерації текстових рекомендацій...")
            rec_script = os.path.join(os.getcwd(), 'src', 'recommendations.py')
            if os.path.exists(rec_script):
                os.system(f'python "{rec_script}"')
                print(f"РЕКОМЕНДАЦІЇ СФОРМОВАНО")
                print(
                    f" Файли збережено: 'data/abc_xyz_with_recommendations.xlsx' та 'data/rfm_with_recommendations.xlsx'")
            else:
                print(" Скрипт recommendations.py не знайдено.")

        elif choice == '0':
            print(" Програму завершено.")
            break
        else:
            print("Невірний вибір. Спробуйте ще раз.")


if __name__ == "__main__":
    main_menu()