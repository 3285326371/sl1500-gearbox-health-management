from pathlib import Path
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


OUT = Path("docs/system_screenshots")
OUT.mkdir(parents=True, exist_ok=True)


def click_nav(driver, target):
    driver.execute_script(
        """
        const item = document.querySelector(`[data-target="${arguments[0]}"]`);
        if (item) item.click();
        """,
        target,
    )
    sleep(1.6)


def shot(driver, name):
    driver.save_screenshot(str(OUT / f"{name}.png"))


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1100")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    try:
        driver.get("http://127.0.0.1:5000")
        wait.until(EC.presence_of_element_located((By.ID, "username")))
        driver.find_element(By.ID, "username").clear()
        driver.find_element(By.ID, "username").send_keys("admin")
        driver.find_element(By.ID, "password").clear()
        driver.find_element(By.ID, "password").send_keys("admin")
        driver.find_element(By.CSS_SELECTOR, "#login-form button[type='submit']").click()
        wait.until(EC.presence_of_element_located((By.ID, "main-app")))
        sleep(2.5)

        shot(driver, "01_windfarm_overview")

        click_nav(driver, "diagnosis")
        try:
            driver.find_element(By.ID, "run-diagnosis-btn").click()
            sleep(2.2)
        except Exception:
            pass
        shot(driver, "02_fault_diagnosis")

        click_nav(driver, "data")
        shot(driver, "03_fault_records")

        click_nav(driver, "reports")
        shot(driver, "04_health_report")

        click_nav(driver, "ai-qa")
        try:
            driver.find_element(By.ID, "qa-input").send_keys("齿轮箱油温过高如何排查？")
            driver.find_element(By.ID, "send-qa-btn").click()
            sleep(2.5)
        except Exception:
            pass
        shot(driver, "05_ai_qa")

        click_nav(driver, "settings")
        shot(driver, "06_settings")
    finally:
        driver.quit()

    for p in sorted(OUT.glob("*.png")):
        print(p)


if __name__ == "__main__":
    main()
