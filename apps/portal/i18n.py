"""
Простий двомовний словник для публічного порталу (UA/EN).
Не використовуємо gettext щоб не потребувати системних бінарників на Windows.
"""

TRANSLATIONS = {
    'uk': {
        # Навігація
        'nav_home': 'Головна',
        'nav_search': 'Пошук рейсу',
        'nav_login': 'Вхід',
        'nav_register': 'Реєстрація',
        'nav_logout': 'Вихід',
        'nav_account': 'Мій кабінет',
        'nav_loyalty': 'Бонусна програма',

        # Hero
        'hero_title': 'Подорожуй Європою',
        'hero_title_2': 'зручно та надійно',
        'hero_subtitle': 'Регулярні автобусні рейси з України до Польщі, Чехії, Словаччини та інших країн ЄС. Купуй квиток онлайн за хвилину.',

        # Промо-банер
        'promo_text': 'Літня знижка 15% на всі рейси до 31 травня. Промокод',
        'promo_close': 'Закрити',

        # Форма пошуку
        'search_from': 'Звідки',
        'search_to': 'Куди',
        'search_date': 'Дата',
        'search_btn': 'Знайти',
        'search_from_ph': 'Місто відправлення',
        'search_to_ph': 'Місто призначення',

        # Секції
        'section_upcoming': 'Найближчі рейси',
        'section_upcoming_sub': 'Рейси, що відправляються найближчим часом',
        'section_popular': 'Популярні напрями',
        'section_popular_sub': 'Куди подорожують найчастіше',
        'section_fleet': 'Сучасний автопарк',
        'section_why': 'Чому ми',
        'section_why_sub': 'Кілька причин подорожувати з нами',
        'section_testimonials': 'Що кажуть наші пасажири',
        'section_testimonials_sub': 'Тисячі задоволених клієнтів щомісяця',
        'section_faq': 'Часті запитання',
        'section_faq_sub': 'Якщо маєш сумніви, напевно знайдеш відповідь нижче',

        # Чому ми
        'feature_safe': 'Надійно',
        'feature_safe_text': 'Сучасний автопарк, технічний контроль, регулярні рейси за розкладом.',
        'feature_comfort': 'Комфортно',
        'feature_comfort_text': "Wi-Fi, USB-розетки, кондиціонер, м'які крісла з відкидною спинкою.",
        'feature_price': 'Доступно',
        'feature_price_text': 'Прозорі ціни, без прихованих платежів, знижки для дітей та студентів.',
        'feature_online': 'Онлайн',
        'feature_online_text': 'Купівля квитка за хвилину, миттєве підтвердження, електронний квиток.',

        # Картки рейсів
        'card_buy': 'Купити квиток',
        'card_buy_short': 'Купити',
        'card_from': 'від',
        'card_price': 'Ціна',
        'card_free_seats': 'вільних',
        'card_hours': 'год',
        'card_km': 'км',
        'card_no_trips': 'Найближчих рейсів зараз немає.',

        # Бронювання
        'booking_title': 'Оформлення бронювання',
        'booking_passengers': 'Кількість пасажирів',
        'booking_route': 'Маршрут поїздки',
        'booking_boarding': 'Місце посадки',
        'booking_alighting': 'Місце висадки',
        'booking_contact': 'Контактні дані замовника',
        'booking_passenger': 'Пасажир',
        'booking_lastname': 'Прізвище',
        'booking_firstname': "Ім'я",
        'booking_phone': 'Телефон',
        'booking_email': 'Email (для квитка)',
        'booking_doc_type': 'Документ',
        'booking_doc_number': 'Номер документа',
        'booking_ticket_type': 'Тип квитка',
        'booking_choose': '— Оберіть —',
        'booking_promo': 'Промокод (за наявності)',
        'booking_total': 'Разом',
        'booking_submit': 'Оформити замовлення',
        'booking_terms': 'Натискаючи кнопку, ви погоджуєтесь з умовами перевезення.',
        'booking_summary': 'До сплати',
        'booking_loyalty': 'Бонусні бали',
        'booking_loyalty_avail': 'Доступно',
        'booking_loyalty_help': '1 бал = 1 EUR знижки (макс. 50% суми).',
        'booking_loyalty_use': 'Скільки балів використати',

        # Підтвердження
        'done_title': 'Замовлення оформлене',
        'done_subtitle': 'Ми надіслали підтвердження на ваш email. Збережіть цю сторінку.',
        'done_order': 'Номер замовлення',
        'done_status': 'Статус',
        'done_route': 'Маршрут',
        'done_departure': 'Дата і час відправлення',
        'done_transport': 'Транспорт',
        'done_contact': 'Контакт',
        'done_tickets': 'Квитки',
        'done_total': 'Разом до сплати',
        'done_back': 'На головну',
        'done_my_bookings': 'Мої бронювання',
        'done_register_cta': 'Зареєструватись для відстеження',
        'done_pdf': 'PDF',

        # Кабінет
        'account_upcoming': 'Майбутні поїздки',
        'account_history': 'Історія поїздок',
        'account_no_upcoming': 'У вас немає майбутніх поїздок',
        'account_find': 'Знайти рейс',
        'account_details': 'Деталі',
        'account_amount': 'Сума',
        'account_tickets_short': 'квитків',

        # Логін / реєстрація
        'login_title': 'Вхід у кабінет',
        'login_sub': 'Введіть ваш email і пароль',
        'login_email': 'Email',
        'login_password': 'Пароль',
        'login_submit': 'Увійти',
        'login_no_account': 'Ще не маєте акаунту?',
        'login_register_link': 'Зареєструватись',
        'login_error': 'Невірний email або пароль.',

        'register_title': 'Створення акаунту',
        'register_sub': 'Це швидко: ~30 секунд',
        'register_pass1': 'Пароль',
        'register_pass2': 'Повторіть пароль',
        'register_submit': 'Зареєструватись',
        'register_have_account': 'Вже маєте акаунт?',
        'register_login_link': 'Увійти',

        # Footer
        'footer_about': 'Сучасні міжнародні автобусні перевезення з України до Європи. Регулярні рейси, комфортний сервіс, прозорі ціни.',
        'footer_service': 'Сервіс',
        'footer_contacts': 'Контакти',
        'footer_newsletter': 'Розсилка новин',
        'footer_newsletter_text': 'Підпишіться, щоб першими дізнаватись про нові маршрути та акції.',
        'footer_subscribe_ok': 'Дякуємо за підписку!',
        'footer_privacy': 'Політика конфіденційності',
        'footer_terms': 'Умови перевезення',
        'footer_rights': 'Усі права захищені.',

        # Cookies
        'cookie_title': 'Cookies та конфіденційність',
        'cookie_text': 'Ми використовуємо файли cookie, щоб зробити сайт зручнішим для вас. Натискаючи «Прийняти», ви погоджуєтесь з нашою політикою.',
        'cookie_accept': 'Прийняти',
        'cookie_reject': 'Тільки необхідні',

        # FAQ
        'faq_q1': 'Як купити квиток онлайн?',
        'faq_a1': 'Виберіть місто відправлення та призначення, дату поїздки, оберіть бажаний рейс і заповніть дані пасажирів. Усе займає 2-3 хвилини. PDF-квиток приходить миттєво.',
        'faq_q2': 'Що потрібно мати при посадці?',
        'faq_a2': 'Документ, що посвідчує особу (закордонний паспорт або ID-картка для країн ЄС) та електронний або роздрукований квиток.',
        'faq_q3': 'Чи можу я повернути квиток?',
        'faq_a3': 'Так. Повернення можливе не пізніше ніж за 24 години до відправлення з утриманням 10% від суми.',
        'faq_q4': 'Які знижки доступні?',
        'faq_a4': 'Дитячий тариф (до 14 років) знижка 50%. Студентський (за наявності картки ISIC) 15%. Пенсійний 10%. Знижки сумуються із сезонними промокодами.',
        'faq_q5': 'Скільки багажу можна взяти?',
        'faq_a5': 'Безкоштовно: 1 місце багажу до 25 кг + ручна поклажа до 5 кг. Додатковий багаж від 5 € за місце, оплата при посадці.',

        # Стати на лендінгу
        'stat_passengers': 'Пасажирів за рік',
        'stat_trips_month': 'Рейсів на місяць',
        'stat_routes': 'Регулярних маршрутів',
        'stat_cities': 'Міст у Європі',

        # Опис автопарку (друга секція)
        'fleet_text': 'Туристичні автобуси Mercedes Tourismo, Setra та Neoplan з кондиціонером, Wi-Fi, м\'якими кріслами з відкидною спинкою та USB-зарядкою на кожному місці. Усі ТЗ проходять регулярний технічний огляд.',
        'fleet_wifi': 'Wi-Fi у дорозі',
        'fleet_climate': 'Клімат-контроль',
        'fleet_usb': 'USB на кожному місці',
        'fleet_tv': 'Мультимедіа',

        # Картки популярних міст
        'city_prague': 'Прага',
        'city_warsaw': 'Варшава',
        'city_berlin': 'Берлін',
        'city_budapest': 'Будапешт',
        'city_vienna': 'Відень',
        'city_krakow': 'Краків',
        'city_kyiv': 'Київ',
        'city_lviv': 'Львів',
        'city_uzhhorod': 'Ужгород',
        'country_cz': 'Чехія',
        'country_pl': 'Польща',
        'country_de': 'Німеччина',
        'country_hu': 'Угорщина',
        'country_at': 'Австрія',
        'badge_tourist': 'Туристичний',
        'badge_new': 'Новинка',
        'badge_economy': 'Економ',

        # Відгуки
        'testimonial_1': 'Дуже зручний автобус, вчасне відправлення. Купив квиток за 5 хвилин на сайті. Wi-Fi працював всю дорогу.',
        'testimonial_2': 'Користуюся регулярно для поїздок до родичів у Прагу. Завжди чисто, водії ввічливі, ніколи не запізнювались.',
        'testimonial_3': 'Електронний квиток у телефоні, зручний кабінет, бачу історію всіх своїх поїздок. Студентська знижка приємний бонус.',
        'testimonial_route': 'Маршрут',

        # Footer-адреса
        'footer_address': 'вулиця Заньковецької, 89, Ужгород, Закарпатська область, Україна, 88000',

        # Формат відносної дати у date-picker (на головній)
        'date_today': 'Сьогодні',
        'date_tomorrow': 'Завтра',
        'date_yesterday': 'Вчора',
        'months_short': 'січ,лют,бер,квіт,трав,черв,лип,серп,вер,жовт,лист,груд',
        'days_short': 'нд,пн,вт,ср,чт,пт,сб',

        # Сторінка деталей рейсу
        'trip_back_to_list': 'До списку рейсів',
        'trip_free_seats': 'вільних',
        'trip_duration': 'Час у дорозі',
        'trip_distance': 'Відстань',
        'trip_stops_count': 'Зупинок у дорозі',
        'trip_transport': 'Транспорт',
        'trip_stops_list': 'Зупинки на маршруті',
        'trip_arrival_short': 'приб.',
        'trip_reviews_word': 'відгук',
        'trip_default_client': 'Клієнт',
        'trip_fleet_section': 'Транспорт та зручності',
        'trip_model': 'Модель',
        'trip_year': 'Рік випуску',
        'trip_seats_total': 'Місць',
        'trip_amenities': 'Зручності у автобусі',
        'trip_amenity_wifi': 'Wi-Fi',
        'trip_amenity_climate': 'Клімат',
        'trip_amenity_wc': 'Туалет',
        'trip_amenity_tv': 'Мультимедіа',
        'trip_amenity_usb': 'USB',
        'trip_countdown_label': 'До відправлення',
        'trip_countdown_inroute': 'У дорозі',
        'trip_countdown_done': 'Завершено',
        'trip_gps_label': 'Стеження GPS',
        'trip_gps_title': 'Дивитись на карті',
        'trip_gps_hint': 'Позицію автобуса в реальному часі',
        'trip_gps_hint_live': 'ЖИВЕ СТЕЖЕННЯ, натисніть для перегляду',
        'trip_gps_hint_past': 'Подивитись пройдений маршрут',
        'trip_weather_dest': 'Погода у пункті призначення',
        'trip_price_per_ticket': 'Ціна за один квиток',
        'trip_departure_label': 'Відправлення',
        'trip_duration_label': 'Тривалість',
        'trip_free_seats_label': 'Вільних місць',
        'trip_buy_ticket': 'Купити квиток',
        'trip_no_seats': 'Місць немає',
        'trip_safe_payment': 'Безпечне оплачення',
        'trip_hours_short': 'год',
        'trip_km_short': 'км',
        'gps_bus_here': 'Автобус зараз тут',
        'gps_speed': 'Швидкість',
        'gps_speed_unit': 'км/год',
        'gps_progress': 'Пройдено',
        'gps_detail_track': 'Детальне стеження',

        # Загальне
        'lang_label': 'Мова',
    },

    'en': {
        # Navigation
        'nav_home': 'Home',
        'nav_search': 'Find a trip',
        'nav_login': 'Sign in',
        'nav_register': 'Sign up',
        'nav_logout': 'Sign out',
        'nav_account': 'My account',
        'nav_loyalty': 'Loyalty program',

        # Hero
        'hero_title': 'Travel Europe',
        'hero_title_2': 'comfortably and safely',
        'hero_subtitle': 'Regular bus services from Ukraine to Poland, Czech Republic, Slovakia and other EU countries. Buy your ticket online in a minute.',

        # Promo banner
        'promo_text': 'Summer 15% off all trips till May 31. Promo code',
        'promo_close': 'Close',

        # Search form
        'search_from': 'From',
        'search_to': 'To',
        'search_date': 'Date',
        'search_btn': 'Search',
        'search_from_ph': 'Departure city',
        'search_to_ph': 'Destination city',

        # Sections
        'section_upcoming': 'Upcoming trips',
        'section_upcoming_sub': 'Trips departing in the near future',
        'section_popular': 'Popular destinations',
        'section_popular_sub': 'Where our passengers travel most',
        'section_fleet': 'Modern fleet',
        'section_why': 'Why us',
        'section_why_sub': 'A few reasons to travel with us',
        'section_testimonials': 'What our passengers say',
        'section_testimonials_sub': 'Thousands of happy customers each month',
        'section_faq': 'Frequently asked questions',
        'section_faq_sub': 'If you have any doubts, you will probably find the answer below',

        # Why us
        'feature_safe': 'Reliable',
        'feature_safe_text': 'Modern fleet, technical control, regular on-time trips.',
        'feature_comfort': 'Comfortable',
        'feature_comfort_text': 'Wi-Fi, USB sockets, air conditioning, soft reclining seats.',
        'feature_price': 'Affordable',
        'feature_price_text': 'Transparent pricing, no hidden fees, discounts for kids and students.',
        'feature_online': 'Online',
        'feature_online_text': 'Buy a ticket in a minute, instant confirmation, e-ticket.',

        # Trip cards
        'card_buy': 'Buy ticket',
        'card_buy_short': 'Buy',
        'card_from': 'from',
        'card_price': 'Price',
        'card_free_seats': 'free seats',
        'card_hours': 'h',
        'card_km': 'km',
        'card_no_trips': 'No trips at the moment.',

        # Booking
        'booking_title': 'Place your booking',
        'booking_passengers': 'Number of passengers',
        'booking_route': 'Trip route',
        'booking_boarding': 'Boarding stop',
        'booking_alighting': 'Drop-off stop',
        'booking_contact': 'Booking contact details',
        'booking_passenger': 'Passenger',
        'booking_lastname': 'Last name',
        'booking_firstname': 'First name',
        'booking_phone': 'Phone',
        'booking_email': 'Email (for the ticket)',
        'booking_doc_type': 'Document',
        'booking_doc_number': 'Document number',
        'booking_ticket_type': 'Ticket type',
        'booking_choose': '— Choose —',
        'booking_promo': 'Promo code (if any)',
        'booking_total': 'Total',
        'booking_submit': 'Place booking',
        'booking_terms': 'By clicking the button you accept the carriage terms.',
        'booking_summary': 'To pay',
        'booking_loyalty': 'Loyalty points',
        'booking_loyalty_avail': 'Available',
        'booking_loyalty_help': '1 point = 1 EUR discount (max 50% of total).',
        'booking_loyalty_use': 'How many points to use',

        # Confirmation
        'done_title': 'Booking confirmed',
        'done_subtitle': 'We have sent the confirmation to your email. Save this page.',
        'done_order': 'Order number',
        'done_status': 'Status',
        'done_route': 'Route',
        'done_departure': 'Departure date and time',
        'done_transport': 'Vehicle',
        'done_contact': 'Contact',
        'done_tickets': 'Tickets',
        'done_total': 'Total to pay',
        'done_back': 'Home',
        'done_my_bookings': 'My bookings',
        'done_register_cta': 'Sign up to track your trips',
        'done_pdf': 'PDF',

        # Account
        'account_upcoming': 'Upcoming trips',
        'account_history': 'Trip history',
        'account_no_upcoming': 'You have no upcoming trips',
        'account_find': 'Find a trip',
        'account_details': 'Details',
        'account_amount': 'Amount',
        'account_tickets_short': 'tickets',

        # Login / register
        'login_title': 'Sign in',
        'login_sub': 'Enter your email and password',
        'login_email': 'Email',
        'login_password': 'Password',
        'login_submit': 'Sign in',
        'login_no_account': "Don't have an account?",
        'login_register_link': 'Sign up',
        'login_error': 'Invalid email or password.',

        'register_title': 'Create your account',
        'register_sub': 'It takes about 30 seconds',
        'register_pass1': 'Password',
        'register_pass2': 'Repeat password',
        'register_submit': 'Sign up',
        'register_have_account': 'Already have an account?',
        'register_login_link': 'Sign in',

        # Footer
        'footer_about': 'Modern international bus services from Ukraine to Europe. Regular trips, comfortable service, transparent pricing.',
        'footer_service': 'Service',
        'footer_contacts': 'Contacts',
        'footer_newsletter': 'Newsletter',
        'footer_newsletter_text': 'Subscribe to be the first to learn about new routes and offers.',
        'footer_subscribe_ok': 'Thanks for subscribing!',
        'footer_privacy': 'Privacy policy',
        'footer_terms': 'Carriage terms',
        'footer_rights': 'All rights reserved.',

        # Cookies
        'cookie_title': 'Cookies and privacy',
        'cookie_text': 'We use cookies to make the site more convenient for you. By clicking «Accept», you agree to our policy.',
        'cookie_accept': 'Accept',
        'cookie_reject': 'Necessary only',

        # FAQ
        'faq_q1': 'How to buy a ticket online?',
        'faq_a1': 'Pick the departure and destination city, the trip date, choose a trip and fill in the passengers. It takes 2-3 minutes. The PDF ticket arrives instantly.',
        'faq_q2': 'What do I need at boarding?',
        'faq_a2': 'A document confirming your identity (international passport or EU ID card) and an electronic or printed ticket.',
        'faq_q3': 'Can I refund the ticket?',
        'faq_a3': 'Yes. Refund is possible no later than 24 hours before departure with a 10% fee.',
        'faq_q4': 'Which discounts are available?',
        'faq_a4': 'Children up to 14 — 50% off. Student (with ISIC) 15%. Senior 10%. Discounts stack with seasonal promo codes.',
        'faq_q5': 'How much luggage can I take?',
        'faq_a5': 'Free: 1 luggage piece up to 25 kg + carry-on up to 5 kg. Extra luggage from 5 € per piece, paid at boarding.',

        # Stats on landing
        'stat_passengers': 'Passengers per year',
        'stat_trips_month': 'Trips per month',
        'stat_routes': 'Regular routes',
        'stat_cities': 'European cities',

        # Fleet description
        'fleet_text': 'Touring coaches Mercedes Tourismo, Setra and Neoplan with air conditioning, Wi-Fi, soft reclining seats and USB charging at every seat. All vehicles pass regular technical inspections.',
        'fleet_wifi': 'Wi-Fi on board',
        'fleet_climate': 'Climate control',
        'fleet_usb': 'USB at every seat',
        'fleet_tv': 'Entertainment',

        # Popular city cards
        'city_prague': 'Prague',
        'city_warsaw': 'Warsaw',
        'city_berlin': 'Berlin',
        'city_budapest': 'Budapest',
        'city_vienna': 'Vienna',
        'city_krakow': 'Krakow',
        'city_kyiv': 'Kyiv',
        'city_lviv': 'Lviv',
        'city_uzhhorod': 'Uzhhorod',
        'country_cz': 'Czechia',
        'country_pl': 'Poland',
        'country_de': 'Germany',
        'country_hu': 'Hungary',
        'country_at': 'Austria',
        'badge_tourist': 'Touristic',
        'badge_new': 'New',
        'badge_economy': 'Economy',

        # Testimonials
        'testimonial_1': 'Very comfortable bus, departed on time. Bought the ticket in 5 minutes online. Wi-Fi worked the whole way.',
        'testimonial_2': 'I use it regularly to visit relatives in Prague. Always clean, drivers are polite, never had a delay.',
        'testimonial_3': 'E-ticket on the phone, convenient cabinet, I see all my trip history. The student discount is a nice bonus.',
        'testimonial_route': 'Route',

        # Footer address
        'footer_address': 'Zankovetska st., 89, Uzhhorod, Zakarpattia oblast, Ukraine, 88000',

        # Relative date format in date-picker (home page)
        'date_today': 'Today',
        'date_tomorrow': 'Tomorrow',
        'date_yesterday': 'Yesterday',
        'months_short': 'Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec',
        'days_short': 'Sun,Mon,Tue,Wed,Thu,Fri,Sat',

        # Trip detail page
        'trip_back_to_list': 'Back to trips',
        'trip_free_seats': 'free',
        'trip_duration': 'Travel time',
        'trip_distance': 'Distance',
        'trip_stops_count': 'Stops along the way',
        'trip_transport': 'Vehicle',
        'trip_stops_list': 'Stops on the route',
        'trip_arrival_short': 'arr.',
        'trip_reviews_word': 'review',
        'trip_default_client': 'Customer',
        'trip_fleet_section': 'Vehicle and amenities',
        'trip_model': 'Model',
        'trip_year': 'Year',
        'trip_seats_total': 'Seats',
        'trip_amenities': 'On-board amenities',
        'trip_amenity_wifi': 'Wi-Fi',
        'trip_amenity_climate': 'Climate',
        'trip_amenity_wc': 'WC',
        'trip_amenity_tv': 'Entertainment',
        'trip_amenity_usb': 'USB',
        'trip_countdown_label': 'Until departure',
        'trip_countdown_inroute': 'In transit',
        'trip_countdown_done': 'Completed',
        'trip_gps_label': 'GPS tracking',
        'trip_gps_title': 'View on map',
        'trip_gps_hint': 'Bus position in real time',
        'trip_gps_hint_live': 'LIVE TRACKING, click to view',
        'trip_gps_hint_past': 'View the route taken',
        'trip_weather_dest': 'Weather at destination',
        'trip_price_per_ticket': 'Price per ticket',
        'trip_departure_label': 'Departure',
        'trip_duration_label': 'Duration',
        'trip_free_seats_label': 'Free seats',
        'trip_buy_ticket': 'Buy ticket',
        'trip_no_seats': 'No seats available',
        'trip_safe_payment': 'Secure payment',
        'trip_hours_short': 'h',
        'trip_km_short': 'km',
        'gps_bus_here': 'Bus is here now',
        'gps_speed': 'Speed',
        'gps_speed_unit': 'km/h',
        'gps_progress': 'Progress',
        'gps_detail_track': 'Detailed tracking',

        # Common
        'lang_label': 'Language',
    },
}


def get_translations(lang_code):
    """Повертає словник перекладів. Якщо мови немає, повертає українську."""
    return TRANSLATIONS.get(lang_code, TRANSLATIONS['uk'])


SUPPORTED_LANGUAGES = [
    ('uk', 'Українська'),
    ('en', 'English'),
]
