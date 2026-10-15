# Запустите один раз: python fix_photos.py
# Обновит URL картинок в базе на локальные
import os
os.environ.setdefault('SQLITE_PATH', os.path.join(os.path.dirname(__file__), 'wengauto.db'))
from app import create_app
from models import db, Car

BRAND_IMG = {
    'Toyota': '/static/img/camry.jpg',
    'BMW': '/static/img/bmw.jpg',
    'Hyundai': '/static/img/tucson.jpg',
    'Kia': '/static/img/sportage.jpg',
    'Mercedes-Benz': '/static/img/mercedes.jpg',
    'Volkswagen': '/static/img/tiguan.jpg',
    'Lada': '/static/img/vesta.jpg',
    'Audi': '/static/img/audi.jpg',
    'Porsche': '/static/img/cayenne.jpg',
    'Tesla': '/static/img/tesla.jpg',
    'Lexus': '/static/img/lexus.jpg',
    'Skoda': '/static/img/octavia.jpg',
}

app = create_app()
with app.app_context():
    n = 0
    for car in Car.query.all():
        car.image_url = BRAND_IMG.get(car.brand, '/static/img/car-placeholder.jpg')
        n += 1
    db.session.commit()
    print(f'Обновлено машин: {n}')
    print('Готово. Обновите страницу в браузере (Ctrl+F5).')
