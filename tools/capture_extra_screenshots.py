from pathlib import Path
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


OUT = Path("docs/system_screenshots")
OUT.mkdir(parents=True, exist_ok=True)


def login(driver):
    wait = WebDriverWait(driver, 20)
    driver.get("http://127.0.0.1:5000")
    wait.until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys("admin")
    driver.find_element(By.ID, "password").send_keys("admin")
    driver.find_element(By.CSS_SELECTOR, "#login-form button[type='submit']").click()
    wait.until(EC.presence_of_element_located((By.ID, "main-app")))
    sleep(2)


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1100")
    options.add_argument("--disable-gpu")
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    driver = webdriver.Chrome(options=options)
    try:
        login(driver)
        driver.execute_script("""
            const card = document.querySelector('.windfarm-card, .unit-card, [data-unit-id], .turbine-card');
            if (card) card.click();
            else document.querySelector('[data-target="turbine-detail"]')?.click();
        """)
        sleep(2.5)
        driver.save_screenshot(str(OUT / "07_turbine_detail.png"))

        driver.get("http://127.0.0.1:5000/hmi.html?unit=WTG-001&mode=login")
        sleep(2.5)
        driver.save_screenshot(str(OUT / "08_hmi_page.png"))
    finally:
        driver.quit()
    for p in sorted(OUT.glob("0[78]_*.png")):
        print(p)


if __name__ == "__main__":
    main()
