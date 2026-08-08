# BioPolymer AI Screening Platform - Technology Stack

This document outlines the core technologies used across the different components of the BioPolymer AI Screening Platform and their specific purposes.

## Backend (Python)

*   **Python**: The core programming language used for the backend services and machine learning scripts.
*   **FastAPI**: A modern, fast (high-performance) web framework for building the RESTful API, handling requests and routing.
*   **Uvicorn**: An ASGI web server implementation for Python, used to serve the FastAPI application.
*   **SQLAlchemy (asyncio)**: The SQL toolkit and Object-Relational Mapping (ORM) library used for interacting with the database asynchronously.
*   **asyncpg**: A fast, asynchronous PostgreSQL database driver library for Python.
*   **Alembic**: A lightweight database migration tool for use with SQLAlchemy, managing database schema changes.
*   **Pydantic**: Used for data validation and settings management using Python type annotations.
*   **python-jose**: Used for generating and verifying JSON Web Tokens (JWT) for authentication and security.
*   **Firebase Admin**: Server-side Firebase integration, likely used for authentication or push notifications.
*   **pandas**: A powerful data manipulation and analysis library, used for processing and structuring datasets.
*   **pytest & pytest-asyncio**: The testing framework used for writing and running unit and integration tests.
*   **testcontainers**: Used to spin up lightweight, throwaway instances of common databases (like PostgreSQL) for integration testing.
*   **ruff**: An extremely fast Python linter and code formatter.
*   **CatBoost**: A high-performance open-source gradient boosting on decision trees library, used for machine learning models (property imputation).

## Mobile Application (Android)

*   **Kotlin**: The primary programming language used for developing the Android application.
*   **Jetpack Compose**: Android's modern toolkit for building native UI in a declarative manner.
*   **Dagger Hilt**: A dependency injection library for Android that reduces the boilerplate of doing manual dependency injection.
*   **Room**: An abstraction layer over SQLite to allow for more robust database access while harnessing the full power of SQLite (local caching/storage).
*   **Retrofit & OkHttp**: A type-safe HTTP client for Android, used for making network requests to the backend API.
*   **Moshi & Kotlinx Serialization**: Used for parsing and serializing JSON data to and from Kotlin objects.
*   **DataStore (Preferences)**: A data storage solution that allows you to store key-value pairs, used for user preferences.
*   **WorkManager**: An API for scheduling deferrable, asynchronous tasks that are expected to run even if the app exits or the device restarts.
*   **Navigation Compose**: Used for routing and navigating between different Composable screens within the app.
*   **Firebase (Auth, Analytics, BOM)**: Used for user authentication and tracking application usage analytics.
*   **TensorFlow Lite**: A lightweight machine learning framework for mobile devices, used for on-device polysaccharide classification and inference.
*   **MPAndroidChart**: A powerful Android chart view / graph view library used for data visualization.
*   **JUnit, Espresso, MockK**: Testing frameworks used for unit testing, UI testing, and mocking dependencies.
