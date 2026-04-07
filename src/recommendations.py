import pandas as pd
import os


def generate_abc_xyz_recommendations(final_df, cat_col):
    print("ГЕНЕРАЦІЯ РЕКОМЕНДАЦІЙ (ABC-XYZ АНАЛІЗ)")
    recommendations = []

    for _, row in final_df.iterrows():
        category = row[cat_col]
        abc_2d = row['ABC_2D']
        xyz = row['XYZ_Class']
        priority = row['Priority']

        rec_text = f"Категорія [{category}]: "
        if abc_2d == 'AA':
            rec_text += "Найбільш прибуткова категорія (драйвер доходу). Рекомендується збільшити асортимент та забезпечити постійну наявність на складі. "
            if xyz == 'X':
                rec_text += "Стабільний попит дозволяє використовувати автоматизоване поповнення запасів."
            else:
                rec_text += "Через нестабільність попиту (Y/Z) потребує створення страхового запасу."
        elif priority == '2 група':
            if abc_2d == 'BA' or abc_2d == 'CA':
                rec_text += "Товар користується високим попитом за кількістю, але має нижчу маржу. Рекомендується змінити або урізноманітнити асортимент для підняття прибутку."
            else:
                rec_text += "Прибутковий товар, що продається рідко. Потребує індивідуального підходу до маркетингу."
        elif priority == '3 група':
            rec_text += "Середня рентабельність. Доцільно підтримувати асортимент без значних інвестицій у просування."
        elif abc_2d == 'CC':
            rec_text += "Найменш рентабельна категорія. Рекомендується скоротити увагу постачальника або застосувати стратегію 'Product Bundling' (продаж у наборі з товарами групи AA зі знижкою)."

        else:
            rec_text += "Категорія потребує додаткового моніторингу динаміки продажів."

        recommendations.append(rec_text)
    final_df['Analytical_Recommendation'] = recommendations
    return final_df


def generate_rfm_recommendations(rfm_df, segment_col):
    print("\n" + "=" * 50)
    print("ГЕНЕРАЦІЯ РЕКОМЕНДАЦІЙ (RFM СЕГМЕНТАЦІЯ)")

    rec_map = {
        'Champions': "Особливий підхід: надання персональних пропозицій, ексклюзивних умов, бонусів та подяк за високу лояльність.",
        'Loyal Customers': "Необхідно пропонувати участь у програмі лояльності або накопичувальні бонуси для підтримки стабільності покупок.",
        'Potential Loyalists': "Ціль — зробити постійними. Рекомендовано провести опитування та запропонувати мотиваційну знижку на наступну покупку.",
        'At Risk (Big Spenders)': "Критичний сегмент: витратили великі суми, але давно не поверталися. Потребують активації персональними акціями.",
        'Hibernating': "Малоцінна група: не потребує дорогих маркетингових інвестицій. Достатньо масової розсилки з опитувальником та вигідною пропозицією.",
        'About to Sleep/Others': "Потребують повернення: доцільно здійснити дзвінок або надіслати повідомлення з дуже вигідними умовами для наступного замовлення."
    }

    rfm_df['Marketing_Strategy'] = rfm_df[segment_col].map(rec_map)
    return rfm_df


if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')
    abc_input = 'data/final_abc_xyz_full_model.xlsx'
    if os.path.exists(abc_input):
        try:
            df_abc = pd.read_excel(abc_input)
            cat_col = df_abc.columns[0]
            df_abc_final = generate_abc_xyz_recommendations(df_abc, cat_col)

            output_abc_path = 'data/abc_xyz_with_recommendations.xlsx'
            df_abc_final.to_excel(output_abc_path, index=False, engine='openpyxl')
            print(f"Рекомендації ABC-XYZ збережено у: {output_abc_path}")
        except Exception as e:
            print(f"Помилка при обробці ABC-XYZ: {e}")

    rfm_input = 'data/rfm_final_report.xlsx'
    if os.path.exists(rfm_input):
        try:
            df_rfm = pd.read_excel(rfm_input, sheet_name='Повні_Дані_RFM')
            df_rfm = generate_rfm_recommendations(df_rfm, 'Segment_Jenks')
            client_col = df_rfm.columns[0]

            output_rfm_path = 'data/rfm_with_recommendations.xlsx'
            df_rfm.to_excel(output_rfm_path, index=False, engine='openpyxl')

            print("\nПРИКЛАДИ СТРАТЕГІЙ ДЛЯ КЛІЄНТІВ (Top 10):")
            print(df_rfm[[client_col, 'Segment_Jenks', 'Marketing_Strategy']].head(10))
            print(f"\nRFM рекомендації додано та збережено у: {output_rfm_path}")
        except Exception as e:
            print(f"Помилка при обробці RFM: {e}")
    else:
        print(f"Файл {rfm_input} не знайдено.")