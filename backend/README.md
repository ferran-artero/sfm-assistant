# Backend — SFM Assistant

FastAPI backend for SFM Assistant, a conversational demo application for checking train and metro schedules in Mallorca.

The backend is responsible for interpreting user messages, maintaining conversational context, validating stations and known places, searching local schedule data and generating safe Catalan responses.

Gemini is used only as a language layer. It does not directly search schedules or decide transport data. The backend owns all schedule lookup, validation and safety checks.

> This backend is part of a local educational demo. It is not affiliated with Serveis Ferroviaris de Mallorca (SFM), and it does not use official real-time data.

---

## Table of Contents

* [Overview](#overview)
* [Main Responsibilities](#main-responsibilities)
* [Tech Stack](#tech-stack)
* [Backend Structure](#backend-structure)
* [Architecture](#architecture)
* [Request Flow](#request-flow)
* [Services](#services)
* [Local Data](#local-data)
* [Prompts](#prompts)
* [Supported Query Types](#supported-query-types)
* [Date and Time Handling](#date-and-time-handling)
* [Conversation Memory](#conversation-memory)
* [Safety and Fallbacks](#safety-and-fallbacks)
* [API Endpoints](#api-endpoints)
* [Installation](#installation)
* [Environment Variables](#environment-variables)
* [Running the Backend](#running-the-backend)
* [Testing the API](#testing-the-api)
* [Debugging](#debugging)
* [Known Limitations](#known-limitations)
* [Future Improvements](#future-improvements)
* [Security Notes](#security-notes)

---

## Overview

SFM Assistant backend receives natural language messages such as:

```text
Vull anar de Manacor a Palma
```

```text
Quins trens hi ha d'Inca a Palma dematí?
```

```text
Vull arribar a Palma abans de les 9 des d'Inca
```

```text
Vull anar a Vilafranca
```

It then converts the message into a structured query, validates the locations, resolves dates and time windows, searches local schedule data and returns a final answer in Catalan.

The system is designed so that the language model never becomes the source of truth for schedule data. Gemini may help interpret and verbalize information, but all transport data is verified by backend services.

---

## Main Responsibilities

The backend handles:

* Chat orchestration.
* Natural language intent detection.
* Rule-based fallback when Gemini fails.
* Conversation memory through `conversation_id`.
* Pending query completion.
* Follow-up queries such as:

  * `A Palma`
  * `Des de Manacor`
  * `I demà dematí?`
  * `I un més tard?`
* Station validation.
* Detection of known places without train or metro service.
* Local schedule search.
* Date and service calendar resolution.
* Time-window resolution.
* Response generation in Catalan.
* Gemini hallucination protection.
* Development debug endpoints.

---

## Tech Stack

* Python
* FastAPI
* Uvicorn
* Pydantic
* Pydantic Settings
* Google Gemini API
* Local JSON data
* `zoneinfo`
* `tzdata`

---

## Backend Structure

```text
backend/

├── app/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   │
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── conversation_service.py
│   │   ├── hallucination_guard.py
│   │   ├── intent_service.py
│   │   ├── llm_service.py
│   │   ├── response_service.py
│   │   ├── station_service.py
│   │   └── train_service.py
│   │
│   ├── data/
│   │   ├── stations.json
│   │   ├── places_without_train.json
│   │   └── schedules_sample.json
│   │
│   └── prompts/
│       ├── intent_prompt.txt
│       └── response_prompt.txt
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## Architecture

The backend follows a service-oriented structure.

```text
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
ChatResponse
```

Each service has a clearly separated responsibility:

* `ChatService` orchestrates the full chat flow.
* `IntentService` converts natural language into structured intent data.
* `ConversationService` manages temporary conversation memory.
* `StationService` validates stations and known places.
* `TrainService` searches local schedule data.
* `ResponseService` generates the final user-facing answer.
* `HallucinationGuard` validates Gemini-generated responses.
* `LLMService` communicates with Gemini.

---

## Request Flow

### 1. User sends a message

The frontend sends:

```json
{
  "message": "Vull anar de Manacor a Palma",
  "conversation_id": null
}
```

If no `conversation_id` is provided, the backend creates a new one.

---

### 2. Intent detection

`IntentService` tries to interpret the message using Gemini.

If Gemini is unavailable or returns invalid data, the backend falls back to deterministic rules.

The intent layer can detect:

* `greeting`
* `thanks`
* `goodbye`
* `train_query`
* `out_of_domain`
* `empty`

For train queries, it extracts:

* query type
* origin
* destination
* date
* time
* time window
* departure-after condition
* arrival-before condition
* known places without train service

---

### 3. Contextual follow-up handling

`ChatService` checks whether the message should be interpreted using conversation context.

Examples:

```text
User: Vull anar a Palma
Bot: Des de quina estació vols sortir per anar a Palma Estació Intermodal?
User: Des de Manacor
```

The second message completes the pending query.

Another example:

```text
User: Vull anar de Manacor a Inca
Bot: Here are the next options.
User: I demà dematí?
```

The backend reuses the previous route and only updates the date and time window.

---

### 4. Known places without train service

The backend uses deterministic rules to detect places that are not train or metro stops in the loaded demo data.

For example:

```text
Des de Vilafranca
```

If Vilafranca appears in `places_without_train.json`, the assistant explains that it does not currently appear as a train or metro stop in the demo network.

This guard is important because known business rules should not depend exclusively on Gemini.

---

### 5. Query completion

`ConversationService` combines the new structured query with any pending query.

It checks which required fields are missing depending on the query type.

For example:

```json
{
  "query_type": "next_departure",
  "origin_stop_id": null,
  "destination_stop_id": "palma"
}
```

This query is incomplete because the origin is missing.

The backend returns a clarification message instead of searching schedules.

---

### 6. Schedule search

Once the query is complete, `TrainService` searches `schedules_sample.json`.

The backend can search:

* next departures
* trains within a time window
* departures after a specific time
* arrivals before a specific time
* departures from a station
* arrivals to a station
* relative later or earlier options

Lists are limited to a small number of results, currently 3 options, to keep responses concise.

---

### 7. Response generation

`ResponseService` generates the final response.

For controlled cases, templates are used directly:

* greetings
* thanks
* goodbyes
* out-of-domain messages
* incomplete queries
* known places without train service
* no results

For train results, Gemini can be used to convert verified JSON into readable Catalan text.

Gemini is instructed not to summarize incorrectly, invent data, remove results or add information outside the backend-provided JSON.

---

### 8. Hallucination validation

`HallucinationGuard` extracts times from the Gemini-generated response and compares them with the verified times returned by `TrainService`.

If Gemini mentions a time that does not appear in the verified result set, the response is rejected and the backend falls back to a safe template.

---

## Services

## `ChatService`

File:

```text
app/services/chat_service.py
```

Main orchestrator of the chatbot.

Responsibilities:

* Receive the user message.
* Create or retrieve the conversation context.
* Store user and assistant messages.
* Call `IntentService`.
* Apply deterministic guards.
* Resolve contextual follow-ups.
* Complete pending queries.
* Search schedules.
* Generate the final response.
* Return `ChatResponse`.

Important logic handled here:

* `DEFAULT_LIMIT = 3`
* current time resolution
* service calendar resolution
* weekday vs weekend handling
* train vs metro mode guessing
* time-window normalization
* relative queries such as `later` and `earlier`
* known places without train guard
* contextual follow-up handling

---

## `IntentService`

File:

```text
app/services/intent_service.py
```

Converts natural language into structured intent data.

It uses two strategies:

1. Gemini-based interpretation.
2. Rule-based fallback.

It detects:

* intent
* query type
* origin text
* destination text
* date
* time
* time window
* departure-after time
* arrival-before time
* detected locations
* known places without train service

Example input:

```text
Vull anar demà dematí d'Inca a Palma
```

Example internal output:

```json
{
  "intent": "train_query",
  "confidence": 0.9,
  "query": {
    "query_type": "list_trains",
    "origin_stop_id": "inca",
    "destination_stop_id": "palma",
    "date": "tomorrow",
    "time": null,
    "time_window": "morning",
    "departure_after": null,
    "arrival_before": null,
    "service_id": null
  }
}
```

---

## `ConversationService`

File:

```text
app/services/conversation_service.py
```

Maintains temporary conversation memory in RAM.

Stored context:

```json
{
  "conversation_id": "uuid",
  "created_at": "iso-date",
  "updated_at": "iso-date",
  "messages": [],
  "last_query": null,
  "last_results": null,
  "pending_query": null
}
```

It supports:

* pending query completion
* last query reuse
* last result reuse
* missing field detection
* clarification messages
* default date handling
* default current-time handling for next departures

Default behavior:

* If no date is provided, the backend assumes `today`.
* If the query is `next_departure` and no time is provided, the backend assumes `now`.

---

## `StationService`

File:

```text
app/services/station_service.py
```

Validates stations and known places.

Responsibilities:

* Load `stations.json`.
* Load `places_without_train.json`.
* Normalize text.
* Match station names.
* Match aliases.
* Match common typos.
* Detect ambiguous locations.
* Detect known places without train service.

Examples:

```text
Palma
```

Valid station.

```text
Plama
```

Possible typo suggestion.

```text
Vilafranca
```

Known place without train or metro stop in the loaded demo network.

---

## `TrainService`

File:

```text
app/services/train_service.py
```

Searches local structured schedule data.

It does not generate text. It only returns structured results.

Main methods:

* `search_next_departure()`
* `search_trains_in_window()`
* `search_arrival_before()`
* `search_departure_after()`
* `search_departures_from_station()`
* `search_arrivals_to_station()`

Example internal result:

```json
{
  "trip_id": "T3_WEEKDAY_MANACOR_PALMA_1825",
  "route_id": "T3",
  "route_name": "T3 Palma - Manacor",
  "service_id": "train_weekday",
  "headsign": "Palma",
  "origin": {
    "stop_id": "manacor",
    "sequence": 1,
    "time": "18:25"
  },
  "destination": {
    "stop_id": "palma",
    "sequence": 20,
    "time": "19:34"
  },
  "duration_minutes": 69
}
```

---

## `ResponseService`

File:

```text
app/services/response_service.py
```

Generates the final response shown to the user.

Response sources:

* `template`
* `gemini`
* `template_fallback`

Templates are used for controlled cases.

Gemini is used only when there are verified train results. It receives:

* normalized query JSON
* verified result JSON
* context JSON

It must return:

```json
{
  "response": "Final response in Catalan"
}
```

If Gemini fails, returns invalid JSON or invents times, the service falls back to a template response.

---

## `HallucinationGuard`

File:

```text
app/services/hallucination_guard.py
```

Protects the system from Gemini-generated schedule hallucinations.

It works by:

1. Extracting all times from the generated response.
2. Extracting all valid times from the verified train results.
3. Comparing both sets.
4. Rejecting the response if it contains invented times.

Example:

Verified times:

```text
08:05, 08:43
```

Gemini response:

```text
El tren surt a les 08:10.
```

Result:

```text
08:10
```

does not exist in the verified result set, so the response is rejected.

---

## `LLMService`

File:

```text
app/services/llm_service.py
```

Generic Gemini client wrapper.

Responsibilities:

* Configure Gemini client.
* Check whether the API key is available.
* Send prompts.
* Request JSON output.
* Parse Gemini responses.
* Raise clear errors when Gemini is unavailable or returns invalid JSON.

---

## Local Data

## `stations.json`

Contains train and metro stops available in the demo.

Typical fields:

* `stop_id`
* `display_name`
* `official_name`
* `aliases`
* `common_typos`
* `modes`
* `routes`
* `valid_rail_stop`
* `valid_train_station`

Used by `StationService`.

---

## `places_without_train.json`

Contains known places in Mallorca that do not appear as railway or metro stops in the loaded demo data.

Examples may include:

* Vilafranca de Bonany
* Alcúdia
* Llucmajor
* Campos
* Santanyí
* Artà

Used to avoid incorrect route searches and hallucinated train destinations.

---

## `schedules_sample.json`

Contains local structured schedule data.

Main sections:

```json
{
  "metadata": {},
  "routes": [],
  "service_calendars": [],
  "trips": []
}
```

Each trip includes:

* `trip_id`
* `route_id`
* `service_id`
* `direction_id`
* `headsign`
* `stop_times`

The backend stores full trips with ordered stop times. This allows it to search route segments between intermediate stops.

---

## Prompts

## `intent_prompt.txt`

Used by Gemini to convert a user message into structured JSON.

The prompt enforces:

* JSON-only output.
* Allowed intents.
* Allowed query types.
* Allowed date values.
* Allowed time-window values.
* No final user-facing response.
* No schedule invention.

---

## `response_prompt.txt`

Used by Gemini to convert verified backend data into readable Catalan text.

The prompt enforces:

* Catalan-only responses.
* No invented times.
* No invented stations.
* No invented routes.
* No real-time claims.
* No information outside `results_json`.
* Mentioning all received results when results are available.
* Returning JSON with only a `response` field.

---

## Supported Query Types

## `next_departure`

Searches next available departures.

Example:

```text
Vull anar d'Inca a Palma
```

If no time is provided, the backend uses the current local time.

---

## `list_trains`

Searches several trains within a time window.

Example:

```text
Quins trens hi ha d'Inca a Palma dematí?
```

The current result limit is 3 options.

---

## `departure_after`

Searches trains departing after a specific time.

Example:

```text
Vull sortir d'Inca després de les 17 cap a Palma
```

---

## `arrival_before`

Searches trains arriving before a specific time.

Example:

```text
Vull arribar a Palma abans de les 9 des d'Inca
```

---

## `departures_from_station`

Searches departures from a station within a time window.

Example:

```text
Quins trens surten d'Inca demà dematí?
```

---

## `arrivals_to_station`

Searches arrivals to a station within a time window.

Example:

```text
Quins trens arriben a Palma dematí?
```

---

## `later`

Relative follow-up query.

Example:

```text
I un més tard?
```

Uses the previous query and last results.

---

## `earlier`

Relative follow-up query.

Example:

```text
I un abans?
```

Uses the previous query and last results.

---

## Date and Time Handling

## Dates

Supported internal date values:

* `today`
* `tomorrow`
* `monday`
* `tuesday`
* `wednesday`
* `thursday`
* `friday`
* `saturday`
* `sunday`
* `weekend`

If no date is provided, the backend defaults to:

```text
today
```

This allows the system to choose the correct weekday or weekend service calendar.

---

## Current Time

For `next_departure`, if no time is provided, the backend uses:

```text
now
```

`now` is resolved using:

```text
Europe/Madrid
```

This prevents the assistant from returning morning departures when the user is asking for the next available train at the current time.

---

## Time Windows

Natural language expressions are mapped to internal time windows.

| Internal value | User expressions            | Time range    |
| -------------- | --------------------------- | ------------- |
| `morning`      | dematí, matí                | 06:00 - 12:00 |
| `midday`       | migdia                      | 12:00 - 15:00 |
| `afternoon`    | tarda, horabaixa, capvespre | 15:00 - 20:00 |
| `evening`      | vespre, nit                 | 20:00 - 23:59 |

Time-window queries are normalized to `list_trains` because users usually expect multiple options within that range.

---

## Service Calendars

The backend resolves the correct `service_id` according to date and transport mode.

Examples:

| Service ID              | Meaning                                            |
| ----------------------- | -------------------------------------------------- |
| `train_weekday`         | Train service on weekdays                          |
| `train_weekend_holiday` | Train service on weekends or holidays              |
| `metro_weekday`         | Metro service on weekdays                          |
| `metro_saturday`        | Metro service on Saturdays                         |
| `metro_no_service`      | No metro service available in the loaded demo data |

Public holiday handling is simplified in the current demo.

---

## Conversation Memory

The backend stores conversation context in RAM.

This enables:

### Pending query completion

```text
User: Vull anar a Palma
Bot: Des de quina estació vols sortir per anar a Palma Estació Intermodal?
User: Des de Manacor
Bot: Returns Manacor → Palma options.
```

### Short station follow-ups

```text
User: Vull sortir d'Inca
Bot: Cap a quina estació vols anar des d'Inca?
User: A Palma
```

### Temporal follow-ups

```text
User: Vull anar de Manacor a Inca
Bot: Returns current options.
User: I demà dematí?
Bot: Returns Manacor → Inca options for tomorrow morning.
```

### Relative result follow-ups

```text
User: Vull anar d'Inca a Palma
Bot: Returns options.
User: I un més tard?
```

The memory is not persistent. It is lost when the backend process restarts.

---

## Safety and Fallbacks

## Gemini as helper, not source of truth

Gemini may help with:

* interpreting natural language
* converting verified JSON into readable Catalan

Gemini must not:

* invent schedules
* invent stations
* invent routes
* decide whether a train exists
* claim real-time data access

---

## Intent fallback

If Gemini fails during intent detection:

```text
intent_source = rules_fallback
```

The backend uses deterministic rules.

---

## Response fallback

If Gemini fails during response generation:

```text
response_source = template_fallback
```

The backend returns a safe template response.

---

## Direct templates

Templates are used for:

* greetings
* thanks
* goodbyes
* empty messages
* out-of-domain queries
* clarifications
* known places without train service
* no results

---

## Hallucination guard

If Gemini mentions a time that is not present in the verified backend results, the response is discarded and replaced with a template fallback.

---

## API Endpoints

## `POST /chat`

Main chatbot endpoint.

### Request

```json
{
  "message": "Vull anar d'Inca a Palma",
  "conversation_id": null
}
```

### Response

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

## `GET /health`

Health check endpoint.

Example:

```bash
curl http://127.0.0.1:8000/health
```

---

## Debug Endpoints

The backend includes debug endpoints for local development.

Examples:

```text
GET /debug/llm
GET /debug/intent?message=Vull anar d'Inca a Palma
GET /debug/station/{query}
GET /debug/trains/next
GET /debug/trains/window
GET /debug/trains/arrival-before
GET /debug/trains/departure-after
GET /debug/conversation/{conversation_id}
DELETE /debug/conversation/{conversation_id}
GET /debug/hallucination/log
DELETE /debug/hallucination/log
```

These endpoints are useful while developing, but they should not be considered a public production API.

---

## Installation

## 1. Enter the backend folder

```bash
cd backend
```

---

## 2. Create a virtual environment

```bash
python -m venv .venv
```

---

## 3. Activate the virtual environment

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

---

## 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file from `.env.example`.

Windows PowerShell:

```bash
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

Example `.env`:

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

Important:

* Never commit `.env`.
* Keep only placeholders in `.env.example`.
* Restart the backend after changing environment variables.

---

## Running the Backend

From `backend/`:

```bash
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

## Testing the API

### Health check

```bash
curl http://127.0.0.1:8000/health
```

---

### Basic chat request

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Vull anar d'Inca a Palma\",\"conversation_id\":null}"
```

---

### Incomplete query test

```json
{
  "message": "Vull anar a Palma",
  "conversation_id": null
}
```

Expected behavior:

```text
Des de quina estació vols sortir per anar a Palma Estació Intermodal?
```

Then send the returned `conversation_id` with:

```json
{
  "message": "Des de Manacor",
  "conversation_id": "same-conversation-id"
}
```

---

### Known place without train test

```json
{
  "message": "Vull anar a Vilafranca",
  "conversation_id": null
}
```

Expected behavior:

The assistant should explain that Vilafranca de Bonany does not currently appear as a train or metro stop in the loaded demo data.

---

### Temporal follow-up test

First:

```json
{
  "message": "Vull anar de Manacor a Inca",
  "conversation_id": null
}
```

Then:

```json
{
  "message": "I demà dematí?",
  "conversation_id": "same-conversation-id"
}
```

Expected behavior:

The assistant should reuse Manacor → Inca and change only the date and time window.

---

## Debugging

Useful values in `/chat` responses:

### `intent_source`

Indicates how the user message was interpreted.

Possible values include:

* `gemini`
* `rules`
* `rules_fallback`
* `pending_context`
* `last_query_context`
* `rules_place_guard`

### `response_source`

Indicates how the final response was generated.

Possible values include:

* `gemini`
* `template`
* `template_fallback`

### `debug`

May include:

* detected intent
* confidence
* structured query
* pending query
* missing fields
* number of results
* Gemini error
* response source

---

## Common Issues

## `ZoneInfoNotFoundError`

Error:

```text
ZoneInfoNotFoundError: No time zone found with key Europe/Madrid
```

Solution:

```bash
pip install tzdata
```

Also make sure `tzdata` is listed in `requirements.txt`.

---

## Gemini is unavailable

Check:

```text
http://127.0.0.1:8000/debug/llm
```

Possible causes:

* missing `GEMINI_API_KEY`
* placeholder API key
* invalid model name
* quota exceeded
* temporary Gemini API issue

---

## Gemini quota exceeded

If you receive a `429 RESOURCE_EXHAUSTED` error:

* wait for quota reset
* switch to a lighter model
* reduce Gemini calls
* rely more on rule-based fallback
* consider separate models for intent and response generation in the future

---

## Invalid Gemini JSON

Gemini is requested to return JSON only. If it returns malformed JSON, the backend falls back to rules or templates depending on where the failure happens.

---

## Frontend cannot connect

Check that the backend is running:

```text
http://127.0.0.1:8000/health
```

Also check that CORS allows the frontend origin.

---

## Known Limitations

This backend is a demo, not a production system.

Current limitations:

* Uses local schedule data, not official real-time data.
* Schedule data may be incomplete or outdated.
* Conversation memory is stored in RAM.
* Memory is lost when the backend restarts.
* Public holiday handling is simplified.
* Transfers are limited.
* No persistent database.
* No authentication.
* Debug endpoints are exposed in development.
* Gemini may fail because of quota, latency or invalid responses.
* No automated test suite yet.

---

## Future Improvements

Possible improvements:

* Import official GTFS data.
* Add real public holiday calendars.
* Add full transfer support.
* Add SQLite or PostgreSQL persistence.
* Add automated tests.
* Add Docker support.
* Add structured logging.
* Add production mode with debug endpoints disabled.
* Add rate limiting.
* Add authentication if the API is exposed publicly.
* Separate Gemini model configuration for intent parsing and response writing.
* Add a no-LLM mode using only rules and templates.

---

## Security Notes

Never commit secrets.

Do not upload:

```text
.env
```

Only commit:

```text
.env.example
```

If an API key is accidentally committed:

1. Revoke the exposed key.
2. Generate a new one.
3. Update the local `.env`.
4. Remove the exposed key from the repository.
5. Commit and push the cleanup.

---

## Relationship with the Frontend

The backend is consumed by the React frontend through:

```text
POST /chat
```

The frontend is responsible only for:

* displaying the chat interface
* sending messages
* storing the `conversation_id`
* showing loading state
* resetting the conversation

All transport logic belongs to the backend.

---

## Disclaimer

This backend is part of an independent educational demo. It is not affiliated with, endorsed by or officially connected to Serveis Ferroviaris de Mallorca.

The information returned by the assistant depends on local demo data and may not match the current official service. For official and up-to-date transport information, users should always consult the official transport provider.
