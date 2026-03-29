import sqlite3
from models.advert import Advert
from models.pic import Picture

insertion_ad = f'''insert into adverts(id, name, desc, price, address, published, views, link, status, city, 
last_cache_update, ts_cached, query) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

insertion_img = f'''insert into pics(order, advertisement, byte) values(?, ?, ?)'''

get_ad = f'''select * from adverts where id = ?'''
get_pics = f'''select order, byte from pics where advertisement = ?'''


def cache(ad: Advert, imgs: list[Picture]):
    con = sqlite3.connect('../data/cache.db')
    con.execute(insertion_ad, (ad.id_, ad.name, ad.desc, ad.price, ad.address, ad.published, ad.views,
                               ad.link, ad.status, ad.city, ad.last_cache_update, ad.ts_cached, ad.query))
    for img in imgs:
        con.execute(insertion_img, (img.order, img.advertisement, img.byte))
    con.close()


def get_cache(id_: int):
    con = sqlite3.connect('../data/cache.db')
    ad = con.execute(str.format(get_ad, id_)).fetchone()
    pics = con.execute(str.format(get_pics, id_)).fetchall()
    return ad, pics
