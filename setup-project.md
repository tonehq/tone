# Project Setup Guide

This guide walks you through setting up the database and seeding initial data for Tone.

## Prerequisites

- Python 3.10+ installed
- PostgreSQL running and accessible
- `.env` file configured with your database connection string (`DATABASE_URL`)
- Dependencies installed: `pip install -r requirements.txt`

## 1. Run Database Migrations

Apply all existing migrations to create the database schema:

```bash
alembic upgrade head
```

This will create all the required tables and indexes in your database.

## 2. Creating New Migrations (Optional)

If you make changes to SQLAlchemy models and need to generate a new migration:

```bash
alembic revision --autogenerate -m "describe your changes"
```

Review the generated migration file in `alembic/versions/` to ensure it accurately reflects your changes, then apply it:

```bash
alembic upgrade head
```

## 3. Seed Service Providers and Models

Populate the database with default service providers (LLM, STT, TTS) and their available models:

```bash
python dev/seed.py
```

This reads from `dev/dev-data.json` and creates the necessary ServiceProvider and Model records. Provider API keys are loaded from environment variables specified in each provider's config.

## 4. Start the Server

```bash
python main.py
```

The server will start on port 8000. You can verify it's running by visiting `http://localhost:8000/docs` for the API documentation.
