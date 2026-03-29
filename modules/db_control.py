import sqlite3

from models.advert import Advert

# запросы, в которые будет идти подстановка параметров
insertion_ad = f'''insert into adverts(id, name, desc, price, address, published, views, link, status, city, 
last_cache_update, ts_cached, query) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

update = f'''update adverts set {0} = {1} where id = {2}'''

get_ad = f'''select * from adverts where id = ?'''


# Получает кешированные данные из бд
def get_cache(id_: int):
    con = sqlite3.connect('./data/cache.db')
    cursor = con.cursor()
    ad = cursor.execute(str.format(get_ad, id_)).fetchone()
    return ad


# пишет в кеш да
def write_cache(ad: Advert):
    con = sqlite3.connect('./data/cache.db')
    cursor = con.cursor()
    cursor.execute(insertion_ad, (ad.id_, ad.name, ad.desc, ad.price, ad.address, ad.published, ad.views,
                               ad.link, ad.status, ad.city, ad.last_cache_update, ad.ts_cached, ad.query))
    con.commit()
    con.close()


# обновляем данные если надо. если не надо, не обновляем
def update_cache(ad: Advert, old: Advert):

    commands = []

    need_update = False

    if ad.status != old.status:
        commands.append(str.format(update, 'status', ad.status, ad.id_))
        need_update = True
    if ad.price != old.price:
        commands.append(str.format(update, 'price', ad.price, ad.id_))
        need_update = True
    if ad.name != old.name:
        commands.append(str.format(update, 'name', ad.price, ad.id_))
        need_update = True
    if ad.desc != old.desc:
        commands.append(str.format(update, 'desc', ad.desc, ad.id_))
        need_update = True

    if not need_update:
        return
    else:
        commands.append(str.format(update, 'last_cache_update', ad.last_cache_update, ad.id_))
    try:
        con = sqlite3.connect('./data/cache.db')
        cursor = con.cursor()
        cursor.execute('BEGIN')
        for command in commands:
            cursor.execute(command)  # транзакция, т.к. время обновления кеша связано с обновлением кеша (вау)
        cursor.execute('COMMIT')
    except:
        cursor.execute('ROLLBACK')
        print('хз, не получилось обновить данные в кеше.\nОткатил транзакцию')
    finally:
        con.close()


# фасад, управляющий логикой кеша
def cache(ad: Advert):
    check = get_cache(ad.id_)
    if check is None:
        write_cache(ad)
    else:
        update_cache(ad, check)


# если нет бд, то создаём
def startup():
    con = sqlite3.connect('./data/cache.db')
    cursor = con.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS adverts(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    desc TEXT NOT NULL,
    price TEXT real NOT NULL,
    address TEXT NOT NULL,
    published TEXT NOT NULL,
    views TEXT NOT NULL,
    link TEXT NOT NULL,
    status TEXT NOT NULL,
    city TEXT NOT NULL,
    last_cache_update INTEGER NOT NULL,
    ts_cached TEXT NOT NULL,
    query TEXT NOT NULL
    )
    ''')
    con.close()
