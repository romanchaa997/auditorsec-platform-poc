# 🚀 auditorsec-platform-poc

**PoC AI-SOC for Gov/Energy sectors** — Мультиагентна платформа для детекції, оркестрації й аналітики критичної інфраструктури.

Будується на базі [Audityzer](https://github.com/romanchaa997/Audityzer) (Web3 Security) та [StructuriZER](https://github.com/romanchaa997/StructuriZER) (AI Data Structuring).

---

## 📋 Структура проєкту

```
auditorsec-platform-poc/
├── .github/workflows/         # CI/CD pipeline (GitHub Actions)
├── analytics/                 # SQL schema + views + analytical scripts
├── soc/                       # AI-SOC service (Python + FastAPI)
├── bots/                      # Telegram/Threads/X бот-помічники
├── infra/                     # Terraform, k8s, DevOps configs
├── docker-compose.yml         # Локальний стек: postgres + soc + metabase
├── .env.example               # Шаблон конфігурації
└── README.md                  # Цей файл
```

---

## 🚀 Швидкий старт (5 хвилин)

### Вимоги
- Docker & Docker Compose
- Git
- ~2 GB RAM & 5 GB дискового простору

### Запуск

```bash
# 1. Клонуй репо
git clone https://github.com/romanchaa997/auditorsec-platform-poc
cd auditorsec-platform-poc

# 2. Налаштуй .env
cp .env.example .env
# Оновли DB_PASSWORD якщо потрібно

# 3. Запусти сервіси
docker-compose up -d

# 4. Чекай логи
docker-compose logs -f
```

### Доступи

| Сервіс | URL | Логін | Пароль |
|--------|-----|-------|--------|
| PostgreSQL | localhost:5432 | audit_user | changeme |
| SOC API | http://localhost:8000 | — | — |
| Metabase | http://localhost:3000 | admin | password |
| Metabase (SQL) | Postgres @ postgres:5432/auditorsec_poc | audit_user | changeme |

---

## 📊 Archictecture

### Шари системи

1. **Data Layer** (PostgreSQL)  
   - `content_events` — записи з LinkedIn/Threads/X/ботів
   - `funnel_events` — B2B воронка (lead → deal)
   - Views: `monthly_channel_metrics`, `monthly_funnel_metrics`

2. **SOC Service** (Python/FastAPI)  
   - Інжест логів → нормалізація → детекція → аналітика
   - API endpoints для запитів & моніторингу
   - Мультиагентна логіка (Ingest, Detection, Triage, Report)

3. **Analytics** (Metabase)  
   - Дашборди по каналах, темах, воронці
   - SQL views для швидкої аналітики
   - Експорт даних для BI

4. **Бот-помічники** (Bot DMs)  
   - Телеграм + Threads + X
   - Автоматична класифікація запитів
   - Інтеграція з CRM

---

## 🎯 Епіки (Roadmap)

### Горизонт 0–12 місяців
- ✅ PostgreSQL schema + docker-compose
- ✅ GitHub Actions CI
- 🔄 PoC AI-SOC (базові правила + ML)
- 🔄 PoC мультиагентна система
- 🔄 Socia bots (Telegram, Threads, X)
- 🔄 Metabase дашборди

### Горизонт 12–36 місяців
- [ ] AI-SOC як повна платформа (multi-sector)
- [ ] BCI/immersive PoC
- [ ] Superset + граф-аналітика
- [ ] Zero-trust + PQC інтеграція

### Горизонт 36+ місяців
- [ ] Індустріальний рівень (reference implementation)
- [ ] Digital twins + мультиагенти
- [ ] Міжнародні стандарти

---

## 🔧 Development

### Локальна розробка

```bash
# Зберегти логи
docker-compose logs soc > soc.log

# Перебудувати контейнер
docker-compose build soc
docker-compose up -d soc

# Запустити SQL запит
docker-compose exec postgres psql -U audit_user -d auditorsec_poc \
  -f /docker-entrypoint-initdb.d/schema.sql

# Зупинити все
docker-compose down
```

### Додати нову таблицю

1. Оновити `analytics/schema.sql`
2. Перезавантажити postgres: `docker-compose down && docker-compose up -d`

---

## 📈 Метрики Fidelity/Risk/Impact

Кожна нова ідея/модуль оцінюється по трьом осях:

- **Fidelity** (0–10): якість результатів  
- **Risk** (low/mid/high): рівень ризику/помилок  
- **Impact**: бізнес-ефект (ліди, скорочення часу, etc.)

---

## 🤝 Kontributing

1. Fork репо
2. Створ feature branch (`git checkout -b feature/awesome`)
3. Commit (`git commit -m 'feat: add awesome'`)
4. Push (`git push origin feature/awesome`)
5. Open PR

---

## 📝 Ліцензія

MIT

---

## 👤 Автор

**Ігор Романченко**  
[@romanchaa997](https://github.com/romanchaa997)  
[LinkedIn](https://linkedin.com/in/igor-romanenko) | [Twitter](https://twitter.com/romanchaa997)

---

## 🎯 Контакти

- **Issues**: [GitHub Issues](https://github.com/romanchaa997/auditorsec-platform-poc/issues)
- **Discussions**: [GitHub Discussions](https://github.com/romanchaa997/auditorsec-platform-poc/discussions)
- **Email**: [romanenko.dev@gmail.com](mailto:romanenko.dev@gmail.com)
