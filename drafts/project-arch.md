FINALYZ/
├── manage.py
├── requirements.txt
├── .env / .env.example
├── config/
│   ├── settings.py          ← configured (apps, crispy, auth redirects, static, dotenv)
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── accounts/                ← Auth only
│   ├── forms.py             ← RegisterForm (username + email + password)
│   ├── views.py             ← Login / Logout / Register (auto-login after register)
│   ├── urls.py
│   └── templates/accounts/
│       ├── login.html
│       └── register.html
├── analysis/                ← Core domain (placeholder for now)
│   ├── views.py             ← home view (login required)
│   ├── urls.py
│   ├── services/            ← ready for pure business logic
│   └── templates/analysis/
│       └── home.html        ← choose Excel / Manual
├── templates/
│   └── base.html            ← Bootstrap 5 + navbar + messages
└── static/
    ├── css/style.css
    └── js/app.js