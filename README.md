# AI Website Link Analysis API

An AI-powered Python backend built with FastAPI designed to accept a website URL, extract website content, analyze it using an LLM (Google Gemini), and generate structured business, competitor, SEO, search query, service, and target audience insights.

> **Current Status — Phase 1 (Project Foundation):** Only the foundational project structure, environment configuration, dependency setup, and initial health/root endpoints are implemented. Website extraction, LLM analysis, and the `/link-analysis` endpoint will be added in upcoming phases.

---

## Planned Features

The following capabilities are planned for subsequent development phases (not yet implemented):

- Website URL validation and normalization
- Asynchronous website content fetching and HTML text extraction
- Content length enforcement and cleaning
- LLM-powered website analysis via Google Gemini (`google-genai`)
- Structured output covering business overview, competitors, SEO insights, search queries, services, and target audience
- Main `/link-analysis` API endpoint with validated Pydantic request/response schemas
- Automated unit and integration tests with Pytest

---

## Technology Stack

- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Data Validation:** Pydantic
- **HTTP Client:** HTTPX
- **HTML Parsing:** BeautifulSoup4
- **Environment Management:** python-dotenv
- **LLM SDK (planned):** Google GenAI SDK (`google-genai`)
- **Testing:** Pytest

---

## Project Structure

```text
ai-website-link-analysis/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   │
│   ├── services/
│   │   └── __init__.py
│   │
│   └── utils/
│       └── __init__.py
│
├── tests/
│   └── __init__.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Installation & Setup

### 1. Navigate to the project directory

```bash
cd ai-website-link-analysis
```

### 2. Create a Python virtual environment

```bash
python3.12 -m venv venv
```

*(Any compatible Python 3.10+ interpreter may be used.)*

### 3. Activate the virtual environment

- **macOS / Linux (`zsh` / `bash`):**
  ```bash
  source venv/bin/activate
  ```
- **Windows (PowerShell):**
  ```powershell
  venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```cmd
  venv\Scripts\activate.bat
  ```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Copy `.env.example` to `.env` if you do not already have a local `.env` file:

```bash
cp .env.example .env
```

Available environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `APP_NAME` | Application display name | `AI Website Link Analysis API` |
| `APP_VERSION` | Application version | `1.0.0` |
| `APP_DESCRIPTION` | API description shown in Swagger docs | *(Built-in description)* |
| `REQUEST_TIMEOUT` | HTTP request timeout in seconds | `15` |
| `MAX_CONTENT_LENGTH` | Maximum website content length in characters | `15000` |
| `LLM_PROVIDER` | Configured LLM provider | `gemini` |
| `LLM_MODEL` | LLM model identifier | *(empty)* |
| `GEMINI_API_KEY` | API key for Google Gemini (not required in Phase 1) | *(empty)* |

Never commit `.env` or hardcode API credentials in source files.

---

## Running the Server

Start the FastAPI development server with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

### Local URLs

- **Root Endpoint:** http://localhost:4000
- **Health Check:** http://localhost:4000/health
- **Swagger Documentation:** http://localhost:4000/docs

