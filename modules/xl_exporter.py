import openpyxl
import openpyxl.utils
from models.advert import Advert
from models.pic import Picture
from openpyxl.drawing.image import Image as XLImage


def export(ad: Advert, pics: list[Picture]):
    book = openpyxl.load_workbook('../data/template.xlsx')
    sheet = book.active
    row = 1
    while sheet[f'A{row}'].value is not None:
        row += 1
    sheet[f'A{row}'] = ad.name
    sheet[f'B{row}'] = ad.id_
    sheet[f'C{row}'] = ad.link
    sheet[f'D{row}'] = ad.desc
    sheet[f'E{row}'] = ad.price
    sheet[f'F{row}'] = ad.published
    sheet[f'G{row}'] = ad.views
    sheet[f'H{row}'] = ad.status
    sheet[f'I{row}'] = ad.city

    for pic in pics:
        letter = openpyxl.utils.get_column_letter(10+pic.order)
        wrap = XLImage(pic.byte)

        if wrap.width > 300 or wrap.height > 300:
            max_size = 300
            ratio = wrap.height / wrap.width
            wrap.width = max_size
            wrap.height = int(max_size * ratio)
        sheet.column_dimensions[letter].width = wrap.width / 7
        sheet.row_dimensions[row].height = wrap.height * 0.75

        sheet.add_image(wrap, f'{letter}{row}')
    book.save()
