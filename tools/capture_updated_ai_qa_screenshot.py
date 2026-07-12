from pathlib import Path
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


OUT = Path("docs/system_screenshots_updated")
OUT.mkdir(parents=True, exist_ok=True)


def login(driver, password):
    wait = WebDriverWait(driver, 10)
    driver.get("http://127.0.0.1:5000")
    wait.until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys("admin")
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "#login-form button[type='submit']").click()
    sleep(1.0)
    try:
        alert = driver.switch_to.alert
        alert.accept()
        return False
    except Exception:
        return True


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    try:
        if not login(driver, "admin"):
            login(driver, "123456")
        wait.until(EC.presence_of_element_located((By.ID, "main-app")))
        driver.execute_script('document.querySelector("[data-target=\\"ai-qa\\"]").click()')
        sleep(1.5)
        q = driver.find_element(By.ID, "qa-input")
        q.clear()
        q.send_keys("结合当前机组数据，判断是否需要停机并给出处置步骤。")
        driver.find_element(By.ID, "send-qa-btn").click()
        sleep(4.0)
        path = OUT / "09_ai_qa_assistant_updated.png"
        driver.save_screenshot(str(path))
        print(path)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
