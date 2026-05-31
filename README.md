# SFM Assistant

Conversational assistant demo for checking train and metro schedules in Mallorca.

SFM Assistant is a full-stack web application that combines a React frontend, a FastAPI backend, local structured schedule data and Gemini-based natural language processing. The system allows users to ask train and metro schedule questions in natural Catalan and receive concise, human-readable answers.

> This is an educational and local demo project. It is not affiliated with Serveis Ferroviaris de Mallorca (SFM), and it does not use official real-time data.

---

## Overview

SFM Assistant is designed as a conversational interface for public transport schedule queries in Mallorca.

Users can ask questions such as:

* `Vull anar de Manacor a Palma`
* `Quins trens hi ha d'Inca a Palma dematí?`
* `Vull arribar a Palma abans de les 9 des d'Inca`
* `Vull anar a Vilafranca`
* `I demà dematí?`
* `I un més tard?`

The assistant interprets the message, extracts structured information, validates stations, handles conversational context, searches local schedule data and returns a response in Catalan.

The language model does not search schedules directly. Schedule lookup is handled by the backend. Gemini is only used to interpret natural language and to convert verified backend data into a readable response.

---

## Main Features

* Conversational train and metro schedule assistant.
* Catalan-only user responses.
* Natural language understanding with Gemini.
* Rule-based fallback when Gemini is unavailable.
* Local JSON schedule search.
* Station and stop validation.
* Detection of known places without train or metro service.
* Support for incomplete queries and follow-up answers.
* Context memory through `conversation_id`.
* Support for relative follow-ups such as:

  * `I demà dematí?`
  * `I un més tard?`
  * `I des de Manacor?`
* Date handling for today, tomorrow, weekdays and weekends.
* Time-window handling for morning, midday, afternoon and evening.
* Result lists limited to a small number of relevant options.
* Hallucination guard to prevent Gemini from inventing times.
* Clean local demo frontend with official-looking visual style and non-official demo notice.

---

## Tech Stack

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* Pydantic Settings
* Google Gemini API
* Local JSON data
* `zoneinfo` / `tzdata`

### Frontend

* React
* Vite
* JavaScript
* CSS
* Fetch API
* LocalStorage

---

## Project Structure

```text
sfm-assistant/

├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   │
│   │   ├── services/
│   │   │   ├── chat_service.py
│   │   │   ├── conversation_service.py
│   │   │   ├── hallucination_guard.py
│   │   │   ├── intent_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── response_service.py
│   │   │   ├── station_service.py
│   │   │   └── train_service.py
│   │   │
│   │   ├── data/
│   │   │   ├── stations.json
│   │   │   ├── places_without_train.json
│   │   │   └── schedules_sample.json
│   │   │
│   │   └── prompts/
│   │       ├── intent_prompt.txt
│   │       └── response_prompt.txt
│   │
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── public/
│   │   └── SFM_Color.svg
│   │
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
│
├── .gitignore
├── README.md
└── TODO.md
```

---

## How It Works

The application follows a backend-controlled architecture.

```text
User
↓
React frontend
↓
POST /chat
↓
ChatService
↓
IntentService
↓
ConversationService
↓
StationService
↓
TrainService
↓
ResponseService
↓
HallucinationGuard
↓
Final response
```

### 1. The user sends a message

The frontend sends the user message and the current `conversation_id` to the backend.

### 2. The backend interprets the intent

`IntentService` uses Gemini to extract structured information from the message. If Gemini fails, a rule-based parser is used as fallback.

The system can detect:

* greetings
* thanks
* goodbyes
* train queries
* out-of-domain messages
* origin station
* destination station
* date
* time
* time window
* query type
* known places without train service

### 3. The conversation context is completed

`ConversationService` keeps temporary memory in RAM.

It stores:

* previous messages
* pending query
* last complete query
* last results

This allows conversations such as:

```text
User: Vull anar a Palma
Bot: Des de quina estació vols sortir per anar a Palma Estació Intermodal?
User: Des de Manacor
Bot: Here are the next options from Manacor to Palma.
```

It also supports temporal follow-ups:

```text
User: Vull anar de Manacor a Inca
Bot: Here are the next options.
User: I demà dematí?
Bot: Here are the options from Manacor to Inca tomorrow morning.
```

### 4. Stations and places are validated

`StationService` validates whether a location is a valid train or metro stop.

It can also detect known places without railway service, such as Vilafranca de Bonany or Alcúdia, so the assistant does not try to invent a train route.

### 5. Local schedules are searched

`TrainService` searches local structured schedule data stored in JSON.

Supported query types include:

* next departures
* trains within a time window
* departures after a specific time
* arrivals before a specific time
* departures from a station
* arrivals to a station
* later or earlier relative options

### 6. A final response is generated

`ResponseService` generates the final response in Catalan.

If Gemini is available, it receives only verified backend data and converts it into readable text.

If Gemini fails or returns unsafe information, the backend uses a safe template response.

### 7. The hallucination guard validates the answer

`HallucinationGuard` checks that Gemini has not introduced times that do not exist in the verified schedule results.

If Gemini invents a time, the generated response is discarded and a template fallback is used.

---

## Example Queries

### Direct route query

```text
Vull anar de Manacor a Palma
```

Expected behavior:

* Detect origin: Manacor.
* Detect destination: Palma.
* Use today as default date.
* Use current time as default time.
* Return the next available options.

---

### Time-window query

```text
Quins trens hi ha d'Inca a Palma dematí?
```

Expected behavior:

* Detect origin: Inca.
* Detect destination: Palma.
* Detect time window: morning.
* Search trains within the morning range.
* Return up to 3 options.

---

### Arrival-before query

```text
Vull arribar a Palma abans de les 9 des d'Inca
```

Expected behavior:

* Detect origin: Inca.
* Detect destination: Palma.
* Detect arrival limit: 09:00.
* Return trains that arrive before that time.

---

### Incomplete query

```text
Vull anar a Palma
```

Expected behavior:

```text
Des de quina estació vols sortir per anar a Palma Estació Intermodal?
```

Then:

```text
Des de Manacor
```

The assistant completes the pending query and searches Manacor → Palma.

---

### Known place without train service

```text
Vull anar a Vilafranca
```

Expected behavior:

The assistant explains that Vilafranca de Bonany does not currently appear as a train or metro stop in the loaded demo data.

---

### Contextual follow-up

```text
I demà dematí?
```

Expected behavior:

The assistant reuses the previous route and changes only the date and time window.

---

## Time Windows

The assistant maps natural language expressions to internal time windows.

| Internal value | Meaning                       | Time range    |
| -------------- | ----------------------------- | ------------- |
| `morning`      | dematí / matí                 | 06:00 - 12:00 |
| `midday`       | migdia                        | 12:00 - 15:00 |
| `afternoon`    | tarda / horabaixa / capvespre | 15:00 - 20:00 |
| `evening`      | vespre / nit                  | 20:00 - 23:59 |

---

## Local Data

The project currently uses local JSON files as demo data.

### `stations.json`

Contains valid train and metro stops, including:

* stop ID
* display name
* official name
* aliases
* common typos
* transport modes
* related routes

### `places_without_train.json`

Contains known places in Mallorca that do not appear as train or metro stops in the loaded demo network.

This is used to avoid incorrect route searches or hallucinated station names.

### `schedules_sample.json`

Contains local structured schedule data.

It includes:

* routes
* service calendars
* trips
* stop times

Each trip stores a full ordered list of stops, which allows the backend to search intermediate route segments.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/ferran-artero/sfm-assistant.git
cd sfm-assistant
```

---

## Backend Setup

### 1. Enter the backend folder

```bash
cd backend
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Create the environment file

Windows PowerShell:

```bash
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

### 6. Configure Gemini

Edit `backend/.env`:

```env
APP_NAME=SFM Assistant
ENVIRONMENT=development

LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite

RESPONSE_LANGUAGE=ca
USE_SAMPLE_DATA=true
DEBUG=true
```

### 7. Run the backend

```bash
uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

## Frontend Setup

Open a new terminal from the project root.

### 1. Enter the frontend folder

```bash
cd frontend
```

### 2. Install dependencies

```bash
npm install
```

### 3. Run the development server

```bash
npm run dev
```

The frontend will usually be available at:

```text
http://localhost:5173
```

---

## API

### `POST /chat`

Main chatbot endpoint.

Example request:

```json
{
  "message": "Vull anar d'Inca a Palma",
  "conversation_id": null
}
```

Example response:

```json
{
  "conversation_id": "uuid",
  "response": "Aquí tens les properes sortides d'Inca cap a Palma Estació Intermodal...",
  "intent_source": "gemini",
  "response_source": "gemini",
  "debug": {
    "intent": "train_query",
    "intent_confidence": 0.9,
    "query": {
      "query_type": "next_departure",
      "origin_stop_id": "inca",
      "destination_stop_id": "palma",
      "date": "today",
      "time": "now",
      "time_window": null,
      "departure_after": null,
      "arrival_before": null,
      "service_id": null
    },
    "results_count": 3,
    "response_source": "gemini",
    "llm_error": null
  }
}
```

---

## Debug Endpoints

The backend includes several debug endpoints for development.

Examples:

```text
GET /health
GET /debug/llm
GET /debug/intent?message=Vull anar d'Inca a Palma
GET /debug/station/{query}
GET /debug/trains/next
GET /debug/trains/window
GET /debug/trains/arrival-before
GET /debug/trains/departure-after
GET /debug/conversation/{conversation_id}
GET /debug/hallucination/log
```

These endpoints are useful during local development but are not intended as a public production API.

---

## Frontend Notes

The frontend provides a clean chat interface with:

* SFM-inspired visual identity.
* User and assistant message bubbles.
* Loading indicator.
* Conversation reset button.
* Persistent `conversation_id` in `localStorage`.
* Non-official local demo notice.

The frontend intentionally hides development debug metadata from the user-facing interface.

---

## Safety and Reliability

The project includes several safeguards:

### Backend-owned data lookup

Gemini does not directly decide schedules. It only works with structured data provided by the backend.

### Rule-based fallback

If Gemini fails, the assistant can still interpret common train queries using deterministic rules.

### Template fallback

If Gemini fails while generating a response, the backend returns a safe template response.

### Hallucination guard

If Gemini mentions a time that does not exist in the verified backend results, the response is discarded.

### Known places without train service

The assistant can detect known places that are not part of the loaded train or metro network and respond accordingly.

---

## Limitations

This project is currently a local demo.

Known limitations:

* It does not use an official real-time SFM API.
* Schedule data is local and may not be up to date.
* Conversation memory is stored in RAM and is lost when the backend restarts.
* Public holidays are simplified.
* Transfers are limited.
* There is no persistent database.
* There is no authentication.
* Debug endpoints are available during development.
* Gemini may fail because of quota limits, latency or malformed responses.

---

## Future Improvements

Potential improvements include:

* Import official GTFS data.
* Add full transfer support.
* Model real public holidays.
* Add SQLite or PostgreSQL persistence.
* Add automated backend and frontend tests.
* Add Docker support.
* Add structured logging.
* Add production mode with debug endpoints disabled.
* Add a frontend environment variable for the backend API URL.
* Add a result-card UI for schedule options.
* Add deployment documentation.

---

## Documentation

More detailed documentation is available in:

```text
backend/README.md
frontend/README.md
```

The root README gives a general overview of the project. The backend and frontend READMEs explain each part in more technical detail.

---

## Security

Never commit `.env` files or API keys.

Use `.env.example` for placeholders only.

If an API key is accidentally pushed to GitHub:

1. Revoke the key.
2. Generate a new one.
3. Update the local `.env` file.
4. Remove the exposed key from the repository.
5. Commit and push the cleanup.

---

## Author

Developed by Ferran Artero as a full-stack AI assistant demo for train and metro schedule queries in Mallorca.

---

## Disclaimer

This project is an independent educational demo. It is not affiliated with, endorsed by or officially connected to Serveis Ferroviaris de Mallorca.

The information returned by the assistant depends on locally loaded demo data and may not match the current official service. For official and up-to-date transport information, users should always consult the official transport provider.
