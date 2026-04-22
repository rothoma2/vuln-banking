# Northstar Bank

Northstar Bank is a compact banking demo application with a Flask backend, PostgreSQL storage, and a browser-based dashboard for accounts, transfers, cards, bills, and AI-assisted support.

## Features

- User authentication and profile management
- Balance checks and transfers
- Loan requests
- Profile picture uploads
- Transaction history and analytics
- Virtual cards and bill payments
- AI customer support chat

## Setup

### Docker

```bash
docker-compose up --build
```

The application will be available at `http://localhost:5000`.

### Local Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Use PostgreSQL locally or via Docker, and set the environment variables in `.env` as needed.

## Environment Variables

```bash
DB_NAME=bank_app
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

## Endpoints

- Main app: `http://localhost:5000`
- API docs: `http://localhost:5000/api/docs`
- GraphQL analytics: `http://localhost:5000/graphql`

## Notes

- The database schema is created automatically on first run.
- Uploaded files are stored under `static/uploads/`.

