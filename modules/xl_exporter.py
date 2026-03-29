import os
import openpyxl
import openpyxl.utils
from models.advert import Advert


def export(ad: Advert):
    path = os.path.expanduser("~/Desktop") + '/template.xlsx'
    book = openpyxl.load_workbook(path)  # открываем файлик
    sheet = book.active
    row = 1
    while sheet[f'A{row}'].value is not None:  # ищем первую пустую строку
        row += 1
    # и забиваем туда данные
    sheet[f'A{row}'] = ad.name
    sheet[f'B{row}'] = ad.id_
    sheet[f'C{row}'] = ad.link
    sheet[f'D{row}'] = ad.desc
    sheet[f'E{row}'] = ad.price
    sheet[f'F{row}'] = ad.published
    sheet[f'G{row}'] = ad.views
    sheet[f'H{row}'] = ad.status
    sheet[f'I{row}'] = ad.city

    # закрываем файл, чтобы потом снова открыть. объяв всё же много, оперативу надо экономить (дорогая нынче)
    book.save(path)
