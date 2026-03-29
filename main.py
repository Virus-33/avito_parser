import os
from datetime import datetime
import random
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium_stealth import stealth
from models.advert import Advert
from models.pic import Picture
from modules.image_handler import get_jpeg
from modules.db_control import cache, get_cache


def get_target(query: str, city: str = 'all'):
    return f'https://www.avito.ru/{city}/?q={query}'


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
    holder = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                                '//div[@data-marker="catalog-serp"]')))

    if holder is not None:
        print('found cardholder')

    links = holder.find_elements(By.XPATH, './div[@data-marker="item"]//h2//a[@data-marker="item-title"]')
    return links


def fetch_address(driver):
    reveal_btn = driver.find_element(By.LINK_TEXT, 'Узнать подробности')
    driver.execute_script('arguments[0].click();', reveal_btn)
    address_props = driver.find_elements(By.XPATH, '//div[@itemprop="address"]')
    return address_props[0], address_props[1]


def get_all_images(driver, ad_id):
    try:
        img_wrap = driver.find_element(By.XPATH, '//ul[@data-marker="image-frame/image-wrapper"]')
        images = driver.find_elements(By.XPATH, '//li[@data-marker="image-preview/item"]')
    except NoSuchElementException:
        return 0

    result: list[Picture] = []

    for i in range(len(images)):
        temp = Picture()
        url = img_wrap.get_attribute('data-url')
        temp.byte = get_jpeg(url)
        temp.advertisement = ad_id
        temp.order = i
        result.append(temp)
        if i < len(images) - 1:
            driver.execute_script('arguments[0].click();', i+1)
    return result


def compile_description(paragraphs: list[webdriver.remote.webelement.WebElement]):
    result = ""
    for p in paragraphs:
        result += p.text
    return result


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

    ad.id_ = ad_id.text.strip('№&nbsp;')
    ad.name = title.get_attribute('innerText')
    ad.desc = desc_paragraphs
    ad.price = price.replace('&nbsp;', ' ', 2)
    ad.address = address.text
    ad.published = pub_date.text.strip(' · ')
    ad.views = views.text.strip('&nbsp;просмотр')
    ad.link = url
    ad.status = 1
    ad.city = city
    ad.last_cache_update = datetime.now().timestamp()
    ad.ts_cached = datetime.now()
    ad.query = sys.argv[1]

    images = get_all_images(driver, ad.id_)
    return ad, images


def argument_handler():

    query = ""
    city = ""
    next_is_city = False

    for i in range(1, len(sys.argv)):
        if sys.argv[i].lower() == '-c':
            if i < len(sys.argv) - 1:
                city = sys.argv[i+1]
                next_is_city = True
        elif next_is_city:
            next_is_city = False
            continue
        else:
            query += sys.argv[i] + " "
    return city, query


def main():

    city, query = argument_handler()

    looking_for = get_target(query) if city == "" else get_target(query, city)

    driver = hide_driver()

    links = get_stuff(driver, looking_for)

    for link in links:
        ad, images = parse_advert(driver, link)
        cache(ad, images)


main()
