# seed_data.py — демо-данные + уникальные пароли сотрудников
from models import db, User, Car, Promo, Client, Lead
from app import create_app

# Пароли сотрудников (только для заказчика) — не коммитить в публичный git
STAFF_PASSWORDS = {
    'admin':     'Weng#Adm2026!Kx9',
    'manager':   'Mgr$Sale7nQ2p',
    'warehouse': 'Skl@Vin88mRt',
    'service':   'Srv#To12bLp',
    'marketing': 'Mkt!Lead5cVw',
}
# Стандартный пользователь (демо-клиент / простой доступ)
STANDARD_USER = ('demo', 'demo123')

def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        if User.query.filter_by(username='admin').first():
            print('Данные уже загружены')
            return

        admin = User(username='admin', email='admin@wengauto.ru', full_name='Администратор Системы', role='admin')
        admin.set_password(STAFF_PASSWORDS['admin'])
        manager = User(username='manager', email='manager@wengauto.ru', full_name='Иван Петров', role='manager')
        manager.set_password(STAFF_PASSWORDS['manager'])
        warehouse = User(username='warehouse', email='sklad@wengauto.ru', full_name='Сергей Складской', role='warehouse')
        warehouse.set_password(STAFF_PASSWORDS['warehouse'])
        service = User(username='service', email='service@wengauto.ru', full_name='Анна Сервисная', role='service')
        service.set_password(STAFF_PASSWORDS['service'])
        marketing = User(username='marketing', email='marketing@wengauto.ru', full_name='Мария Маркетолог', role='marketing')
        marketing.set_password(STAFF_PASSWORDS['marketing'])
        demo = User(username=STANDARD_USER[0], email='demo@wengauto.ru', full_name='Демо Пользователь', role='manager')
        demo.set_password(STANDARD_USER[1])
        db.session.add_all([admin, manager, warehouse, service, marketing, demo])

        # Реалистичные фото (Unsplash, стабильные URL)
        cars_data = [
            dict(vin='XW8ZZZ61ZJG000001', brand='Toyota', model='Camry', year=2024, price=3250000,
                 body_type='седан', transmission='АКПП', drive='передний', engine='2.5', power_hp=200,
                 color_body='Белый', color_interior='Чёрный', is_new=True, status='in_stock',
                 description='Новый Toyota Camry 2024. Комфорт, надёжность и богатая комплектация.',
                 image_url='/static/img/camry.jpg'),
            dict(vin='XW8ZZZ61ZJG000002', brand='BMW', model='X5', year=2023, price=7890000,
                 body_type='кроссовер', transmission='АКПП', drive='полный', engine='3.0', power_hp=340,
                 color_body='Чёрный', color_interior='Бежевый', is_new=True, status='in_stock',
                 description='BMW X5 xDrive40i. Премиальный кроссовер с полным приводом.',
                 image_url='/static/img/bmw.jpg'),
            dict(vin='XW8ZZZ61ZJG000003', brand='Hyundai', model='Tucson', year=2024, price=2890000,
                 body_type='кроссовер', transmission='АКПП', drive='полный', engine='2.0', power_hp=150,
                 color_body='Серый', color_interior='Чёрный', is_new=True, status='in_stock',
                 description='Hyundai Tucson 2024. Стильный дизайн и экономичный расход.',
                 image_url='/static/img/tucson.jpg'),
            dict(vin='XW8ZZZ61ZJG000004', brand='Kia', model='Sportage', year=2023, price=2650000,
                 body_type='кроссовер', transmission='АКПП', drive='передний', engine='2.0', power_hp=150,
                 color_body='Красный', color_interior='Чёрный', is_new=True, status='in_stock',
                 description='Kia Sportage. Яркий дизайн и богатая комплектация.',
                 image_url='/static/img/sportage.jpg'),
            dict(vin='XW8ZZZ61ZJG000005', brand='Mercedes-Benz', model='E-Class', year=2022, price=6200000,
                 body_type='седан', transmission='АКПП', drive='задний', engine='2.0', power_hp=197,
                 color_body='Серебристый', color_interior='Бежевый', is_new=False, mileage=15000, status='in_stock',
                 description='Mercedes-Benz E 200. С пробегом, в отличном состоянии.',
                 image_url='/static/img/mercedes.jpg'),
            dict(vin='XW8ZZZ61ZJG000006', brand='Volkswagen', model='Tiguan', year=2024, price=3450000,
                 body_type='кроссовер', transmission='АКПП', drive='полный', engine='2.0 TSI', power_hp=190,
                 color_body='Синий', color_interior='Чёрный', is_new=True, status='in_stock',
                 description='Volkswagen Tiguan. Немецкий кроссовер для города и трассы.',
                 image_url='/static/img/tiguan.jpg'),
            dict(vin='XW8ZZZ61ZJG000007', brand='Lada', model='Vesta', year=2024, price=1450000,
                 body_type='седан', transmission='МКПП', drive='передний', engine='1.6', power_hp=106,
                 color_body='Белый', color_interior='Серый', is_new=True, status='in_stock',
                 description='Lada Vesta. Доступный и практичный седан.',
                 image_url='/static/img/vesta.jpg'),
            dict(vin='XW8ZZZ61ZJG000008', brand='Audi', model='Q7', year=2023, price=9100000,
                 body_type='кроссовер', transmission='АКПП', drive='полный', engine='3.0 TFSI', power_hp=340,
                 color_body='Чёрный', color_interior='Коричневый', is_new=True, status='in_transit',
                 description='Audi Q7. В пути от дистрибьютора.',
                 image_url='/static/img/audi.jpg'),
            dict(vin='XW8ZZZ61ZJG000009', brand='Porsche', model='Cayenne', year=2023, price=12500000,
                 body_type='кроссовер', transmission='АКПП', drive='полный', engine='3.0', power_hp=340,
                 color_body='Белый', color_interior='Чёрный', is_new=True, status='in_stock',
                 description='Porsche Cayenne. Спорт и комфорт в одном кузове.',
                 image_url='/static/img/cayenne.jpg'),
            dict(vin='XW8ZZZ61ZJG000010', brand='Tesla', model='Model 3', year=2024, price=4500000,
                 body_type='седан', transmission='АКПП', drive='задний', engine='Electro', power_hp=283,
                 color_body='Красный', color_interior='Белый', is_new=True, status='in_stock',
                 description='Tesla Model 3. Электромобиль с автопилотом.',
                 image_url='/static/img/tesla.jpg'),
            dict(vin='XW8ZZZ61ZJG000011', brand='Lexus', model='RX', year=2023, price=7200000,
                 body_type='кроссовер', transmission='АКПП', drive='полный', engine='2.4 Hybrid', power_hp=250,
                 color_body='Синий', color_interior='Бежевый', is_new=True, status='in_stock',
                 description='Lexus RX. Премиальный гибридный кроссовер.',
                 image_url='/static/img/lexus.jpg'),
            dict(vin='XW8ZZZ61ZJG000012', brand='Skoda', model='Octavia', year=2024, price=2450000,
                 body_type='лифтбек', transmission='АКПП', drive='передний', engine='1.4 TSI', power_hp=150,
                 color_body='Серый', color_interior='Чёрный', is_new=True, status='in_stock',
                 description='Skoda Octavia. Вместительный и экономичный лифтбек.',
                 image_url='/static/img/octavia.jpg'),
        ]
        for c in cars_data:
            db.session.add(Car(**c))

        db.session.add(Promo(title='Весенняя скидка 5%', description='Скидка 5% на все новые автомобили Hyundai и Kia до конца месяца.', discount_percent=5, active=True))
        db.session.add(Promo(title='Trade-in бонус 50 000 ₽', description='Дополнительная выгода при обмене вашего автомобиля.', discount_percent=0, active=True))
        db.session.add(Promo(title='Кредит от 0,1%', description='Специальные условия кредитования на новые автомобили.', discount_percent=0, active=True))
        db.session.add(Promo(title='Зимние шины в подарок', description='При покупке кроссовера — комплект зимней резины.', discount_percent=0, active=True))

        db.session.commit()
        print('Демо-данные загружены.')
        print('Стандартный пользователь: demo / demo123')
        print('Пароли сотрудников — только у владельца (см. сообщение ассистента).')

if __name__ == '__main__':
    seed()
