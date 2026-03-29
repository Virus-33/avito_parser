from datetime import datetime
import random
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
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
        driver.execute_script('window.scrollBy(0, 1000);')
        time.sleep(random.uniform(0.1, 0.3))


def get_with_waiting(driver, tag: str, prop: str):
    return WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                              f'//{tag}[@{prop}]')))


def get_with_js_id(driver, id: str):
    return driver.execute_script(f"""
        let el = document.querySelector('#{id}');
        return el ? el.textContent : null;
    """)


def get_with_js_marker(driver, tag, marker: str):
    return driver.execute_script(f"""
        let el = document.querySelector('{tag}[{marker}]');
        return el ? el.textContent : null;
    """)


def get_stuff(driver, url):
    driver.get(url)
    urls: list[str] = []
    for i in range(10):
        holder = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                                    '//div[@data-marker="catalog-serp"]')))
        if holder is None:
            return []
        print('found cardholder')
        scroll(driver, 37)

        links = holder.find_elements(By.XPATH, './div[@data-marker="item"]//h2//a[@data-marker="item-title"]')
        for link in links:
            urls.append(link.get_attribute('href'))

        next = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                                  '//div[@data-marker="pagination-button'
                                                                                  '/nextPage"]'))).click()
    return urls


def fetch_address(driver):
    time.sleep(0.8)
    driver.execute_script("""
    let link = Array.from(document.querySelectorAll('a')).find(a => a.textContent.trim() === 'Узнать подробности');
    if (link) link.click();
    """)
    WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                       '//div[@itemprop="address"]')))
    time.sleep(2)

    address_props = driver.execute_script("""
        return Array.from(document.querySelectorAll('[itemprop="address"]'))
            .map(el => el.textContent.trim());
    """)

    return address_props[0], address_props[1][address_props[1].rfind('\n') + 1:]


def get_all_images(driver, ad_id):
    img_wrap = get_with_js_marker(driver, 'ul', 'data-marker="image-frame/image-wrapper"')
    print('got img wrapper')
    images = driver.find_elements(By.XPATH, './li[@data-marker="image-preview/item"]')
    print('got image list')
    if img_wrap is None:
        print('found nothing')
        return []

    result: list[Picture] = []

    for i in range(len(images)):
        temp = Picture()
        url = img_wrap.get_attribute('data-url')
        temp.byte = get_jpeg(url)
        temp.advertisement = ad_id
        temp.order = i
        result.append(temp)
        if i < len(images) - 1:
            driver.execute_script('arguments[0].click();', i + 1)
    return result


def parse_advert(driver, url):
    driver.get(url)
    closed = driver.find_elements(By.XPATH, '//div[@data-marker="item-view/closed-warning"]')
    if len(closed) > 0:
        return

    ad = Advert()
    print('found active one')
    try:
        ad.name = get_with_waiting(driver, 'h1', 'itemprop="name"').get_attribute('innerText')
    except StaleElementReferenceException:
        ad.name = get_with_js_marker(driver, 'h1', 'itemprop="name"')
    print('got name')
    try:
        ad.desc = get_with_waiting(driver, 'div', 'itemprop="description"').text
    except StaleElementReferenceException:
        ad.desc = get_with_js_marker(driver, 'div', 'itemprop="description"')
    print('got desc')
    try:
        ad.price = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, 'bx_item-price-value'))).text\
            .replace('&nbsp;', ' ', 2)
    except StaleElementReferenceException:
        ad.price = get_with_js_id(driver, 'bx_item-price-value').replace('&nbsp;', ' ', 2)
    print('got price')
    try:
        ad.id_ = get_with_waiting(driver, 'span', 'data-marker="item-view/item-id"').text.strip('№&nbsp;')
    except StaleElementReferenceException:
        ad.id_ = get_with_js_marker(driver, 'span', 'data-marker="item-view/item-id"').strip('№&nbsp;')
    print('got number')
    try:
        ad.published = get_with_waiting(driver, 'span', 'data-marker="item-view/item-date"').text.strip(' · ')
    except StaleElementReferenceException:
        ad.published = get_with_js_marker(driver, 'span', 'data-marker="item-view/item-date"').text.strip(' · ')
    print('got date')
    try:
        ad.views = get_with_waiting(driver, 'span', 'data-marker="item-view/total-views"').text.strip('&nbsp;просмотр')
    except StaleElementReferenceException:
        ad.views = get_with_js_marker(driver, 'span', 'data-marker="item-view/total-views"').strip('&nbsp;просмотр')
    print('got views')

    city, address = fetch_address(driver)

    print('got address')
    ad.address = address
    ad.link = url
    ad.status = 1
    ad.city = city
    ad.last_cache_update = datetime.now().timestamp()
    ad.ts_cached = datetime.now()
    ad.query = sys.argv[1]

    '''
    print('getting images')
    images = get_all_images(driver, ad.id_)
    print(f'gathered {len(images)} pictures')
    '''
    return ad  # , images


def argument_handler():
    query = ""
    city = ""
    next_is_city = False

    for i in range(1, len(sys.argv)):
        if sys.argv[i].lower() == '-c':
            if i < len(sys.argv) - 1:
                city = sys.argv[i + 1]
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

    print('working with links')
    for link in links:
        ad = parse_advert(driver, link)
        cache(ad)


main()
