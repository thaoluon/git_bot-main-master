from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os
from dotenv import load_dotenv

load_dotenv()
CHROME_PROFILE_PATH = os.getenv("CHROME_PROFILE_PATH")

def send_email(to_email, subject, body):
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    driver = webdriver.Chrome(options=options)

    driver.get("https://mail.google.com/mail/u/0/#inbox?compose=new")
    time.sleep(5)

    driver.find_element(By.NAME, "to").send_keys(to_email)
    driver.find_element(By.NAME, "subjectbox").send_keys(subject)
    driver.find_element(By.CSS_SELECTOR, "div[aria-label='Message Body']").send_keys(body)
    driver.find_element(By.XPATH, "//div[text()='Send']").click()

    time.sleep(3)
    driver.quit()
