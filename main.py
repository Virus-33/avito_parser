from datetime import datetime
import random
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException
from selenium_stealth import stealth
from models.advert import Advert
from modules.db_control import cache, startup
from modules.xl_exporter import export


def get_target(query: str, city: str = 'all'):
    return f'https://www.avito.ru/{city}/?q={query}'  # собираем поисковой запрос. Категорию оно благо само подбирает


def hide_driver():
    options = Options()
    options.page_load_strategy = 'eager'  # может начать бесконечно грузить страницу, поэтому не ждём
    driver = webdriver.Chrome(options=options)
    stealth(driver, platform='Win32')  # вообще тут любую чушь вместо платформы вставить можно чтобы скрыться
    return driver


# js-прокрутка с ожиданием, ничё интересного
def scroll(driver, long):
    for _ in range(long):
        driver.execute_script('window.scrollBy(0, 1000);')
        time.sleep(random.uniform(0.1, 0.3))


# поиск элемента через вебдрайвер с ожиданием во избежание казусов
def get_with_waiting(driver, tag: str, prop: str):
    return WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                              f'//{tag}[@{prop}]')))


# на случай если поиск через вебдрайвер улетел по таймауту или "потерял" элемент (а такое бывает)
def get_with_js_id(driver, id: str):
    return driver.execute_script(f"""
        let el = document.querySelector('#{id}');
        return el ? el.textContent : null;
    """)


# прошлый поиск был по id для одного кейса, но мне не нравилась жирная функция. Этот ищет по маркеру.
def get_with_js_marker(driver, tag, marker: str):
    return driver.execute_script(f"""
        let el = document.querySelector('{tag}[{marker}]');
        return el ? el.textContent : null;
    """)


def get_stuff(driver, url):
    driver.get(url)
    urls: list[str] = []
    for i in range(10):  # с 10 страниц поиска собираем ссылки из всех карточек до каких доберёмся
        holder = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                                    '//div[@data-marker="catalog-serp"]')))
        if holder is None:
            return []  # если не нашли обёртку карточек то поминки
        print('found cardholder')
        scroll(driver, 37)

        # собираем ссылку из карточки
        links = holder.find_elements(By.XPATH, './div[@data-marker="item"]//h2//a[@data-marker="item-title"]')
        for link in links:
            urls.append(link.get_attribute('href'))  # из элемента берём исключительно ссылку как строку

        # кликаем на страничку чтобы собрать больше
        WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                           '//div[@data-marker="pagination-button'
                                                                           '/nextPage"]'))).click()
    return urls


def fetch_address(driver):
    time.sleep(0.8)  # спим, некоторые вещи грузятся не сразу
    driver.execute_script("""
    let link = Array.from(document.querySelectorAll('a')).find(a => a.textContent.trim() === 'Узнать подробности');
    if (link) link.click();
    """)  # вот такие например
    time.sleep(2)
    WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH,
                                                                       '//div[@itemprop="address"]')))  # ждём ещё...

    address_props = driver.execute_script("""
        return Array.from(document.querySelectorAll('[itemprop="address"]'))
            .map(el => el.textContent.trim());
    """)  # пожинаем плоды ожидания в виде парочки span с инфой

    return address_props[0], address_props[1][address_props[1].rfind('\n') + 1:]  # иногда там есть мусор типа
                                                                                # станций метро и т.д., его обрезаем


def parse_advert(driver, url):
    driver.get(url)
    closed = driver.find_elements(By.XPATH, '//div[@data-marker="item-view/closed-warning"]')  # проверка на статус
    if len(closed) > 0:
        return

    ad = Advert()
    print('found active one')

    # получаем отдельно каждый кусочек объявы, если не можем - получаем через js, потому что он там 100% есть
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
        ad.price = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, 'bx_item-price-value'))).text \
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

    # получаем адрес объявителя
    city, address = fetch_address(driver)

    print('got address')
    ad.address = address
    ad.link = url
    ad.status = 'активно'
    ad.city = city
    ad.last_cache_update = datetime.now().timestamp()
    ad.ts_cached = datetime.now()

    return ad


def argument_handler():
    query = ""
    city = ""
    next_is_city = False

    for i in range(1, len(sys.argv)):
        if sys.argv[i].lower() == '-c':  # если нашли ключ, то след арг это город (если есть, иначе скип)
            if i < len(sys.argv) - 1:
                city = sys.argv[i + 1]
                next_is_city = True
        elif next_is_city:
            next_is_city = False
            continue
        else:
            query += sys.argv[i] + " "  # собираем всё пробельное в один запрос
    return city, query


def main():
    city, query = argument_handler()  # чекаем чё в аргументах запуска

    looking_for = get_target(query) if city == "" else get_target(query, city)  # тернарник не боимся, вызываем поиск

    driver = hide_driver()  # прячемся под браузером с надстройками чтобы авито не палил что это бот

    links = get_stuff(driver, looking_for)  # получаем все ссылки с первых десяти страниц поиска

    print('working with links')
    startup()  # прогреваем бд на всякий случай
    for link in links:
        ad = parse_advert(driver, link)  # собираем инфу об объяве
        ad.query = query
        cache(ad)  # кешируем
        export(ad)  # и выводим в ехель


main()
