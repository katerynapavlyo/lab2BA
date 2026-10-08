import asyncio
import json
import csv
from playwright.async_api import async_playwright

async def scrape_spending():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("Завантаження сторінки трансакцій...")
        await page.goto("https://spending.gov.ua/new/transactions", wait_until="domcontentloaded", timeout=60000)

        print("Очікування відображення таблиці...")
        await page.wait_for_timeout(8000)

        rows = await page.query_selector_all("tr")
        data = []

        for row in rows:
            cols = await row.query_selector_all("td")
            if len(cols) >= 4:
                cols_text = [await col.inner_text() for col in cols]
                cols_clean = [c.strip().replace("\n", " ") for c in cols_text if c.strip()]

                if len(cols_clean) >= 4 and any("." in cols_clean[0] for _ in [0]):
                    item = {
                        "дата": cols_clean[0],
                        "платник": cols_clean[1],
                        "отримувач": cols_clean[2],
                        "сума": cols_clean[3],
                        "призначення": cols_clean[4] if len(cols_clean) > 4 else ""
                    }
                    data.append(item)

        if not data:
            blocks = await page.query_selector_all("div[class*='transaction'], div[class*='table-row'], div[class*='row-']")
            for block in blocks:
                text = await block.inner_text()
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                if len(lines) >= 5 and "ДАТА ОПЛАТИ" not in lines and "ПЛАТНИК" not in lines:
                    item = {
                        "дата": lines[0],
                        "платник": lines[1],
                        "отримувач": lines[2],
                        "сума": lines[3],
                        "призначення": " | ".join(lines[4:])
                    }
                    if item not in data:
                        data.append(item)

        if data:
            with open("transactions.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Успішно збережено {len(data)} трансакцій у transactions.json")

            with open("transactions.csv", "w", encoding="utf-8-sig", newline="") as f:
                fieldnames = ["дата", "платник", "отримувач", "сума", "призначення"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            print(f"Успішно збережено {len(data)} трансакцій у transactions.csv")
        else:
            print("Трансакції не знайдені. Перевірте відкрите вікно браузера.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_spending())