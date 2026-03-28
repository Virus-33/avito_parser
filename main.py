from datetime import datetime
import random
import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium_stealth import stealth
from modules.advert import Advert

# TODO: config existence check
with open('config.conf', 'r', encoding='utf-8') as config:
    line = config.readline()
    target = line[line.find('="') + 2: line.find('\n')]


def hide_driver():
    options = Options()
    options.page_load_strategy = 'eager'
    driver = webdriver.Chrome(options=options)
    stealth(driver, platform='Win32')
    return driver


def scroll(driver, long):
    for _ in range(long):
        driver.execute_script('window.scrollBy(0,500);')
        time.sleep(random.uniform(0.1, 0.3))


def get_stuff(driver, url):
    driver.get(url)
    scroll(driver, 30)
    holder = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, '//div[@data-marker="catalog-serp"]')))

    if holder is not None:
        print('found cardholder')

    links = holder.find_elements(By.XPATH, './div[@data-marker="item"]//h2//a[@data-marker="item-title"]')
    return links


def fetch_address(driver):
    reveal_btn = driver.find_element(By.LINK_TEXT, 'Узнать подробности')
    driver.execute_script('arguments[0].click();', reveal_btn)
    address_props = driver.find_elements(By.XPATH, '//div[@itemprop="address"]')
    return address_props[0], address_props[1]


def fetch_phone(driver):
    phone_btn = driver.find_element(By.XPATH, '//button[@data-marker="item-phone-button/card"]')
    


def parse_advert(driver, url):
    driver.get(url)
    closed = driver.find_elements(By.XPATH, '//div[@data-marker="item-view/closed-warning"]')
    if len(closed) > 0:
        return

    ad = Advert()
    title = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, '//h1[@itemprop="name"]')))
    desc_packed = driver.find_element(By.XPATH, '//div[@itemprop="description"]')
    desc_paragraphs = desc_packed.find_elements(By.TAG_NAME, 'p')
    desc_paragraphs = compile_description(desc_paragraphs)
    price_box = driver.find_element(By.ID, 'bx_item-price-value')
    price = price_box.text
    ad_id = driver.find_element(By.XPATH, '//span[@data-marker="item-view/item-id"]')
    pub_date = driver.find_element(By.XPATH, '//span[@data-marker="item-view/item-date"]')
    views = driver.find_element(By.XPATH, '//span[@data-marker="item-view/total-views"]')
    city, address = fetch_address(driver)



    ad._id = ad_id.text.strip('№&nbsp;')
    ad.name = title.get_attribute('innerText')
    ad.desc = desc_paragraphs
    ad.price = price.replace('&nbsp;', ' ', 2)
    ad.address = address.text
    ad.published = pub_date.text.strip(' · ')
    ad.views = views.text.strip('&nbsp;просмотр')
    ad.link = url
    ad.status = 1
    ad.phone
    ad.city = city
    ad.images
    ad.last_cache_update = datetime.now().timestamp()
    ad.ts_cached = datetime.now()
    ad.query = sys.argv[1]


def compile_description(paragraphs: list[webdriver.remote.webelement.WebElement]):
    result = ""
    for p in paragraphs:
        result += p.text
    return result




def main():
    looking_for = target+sys.argv[1]

    driver = hide_driver()

    get_stuff(driver, looking_for)


