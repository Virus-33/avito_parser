import random
import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium_stealth import stealth

# TODO: config existence check
with open('config.conf', 'r', encoding='utf-8') as config:
    line = config.readline()
    target = line[line.find('="') + 2: line.find('\n')]


def hide_driver():
    driver = webdriver.Chrome()
    stealth(driver, platform='Win32')
    return driver


def scroll(driver, long):
    for _ in range(long):
        driver.execute_script('window.scrollBy(0,500)')
        time.sleep(random.uniform(0.1, 0.3))


def get_stuff(driver, url):
    driver.get(url)
    scroll(driver, 4)
    holder = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, '//div[@data-marker="catalog-serp"]')))

    if holder is not None:
        print('found cardholder')

    links = holder.find_elements(By.XPATH, './div[@data-marker="item"]//h2//a[@data-marker="item-title"]')
    for link in links:
        print(link.get_attribute('href'))


looking_for = target+sys.argv[1]

driver = hide_driver()

get_stuff(driver, looking_for)


