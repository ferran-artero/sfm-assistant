# SFM Assistant

Assistent intel·ligent de demostració per consultar horaris de tren i metro de Mallorca a partir de dades locals estructurades.

El projecte combina un backend amb FastAPI, una interfície web amb React + Vite, una petita base de dades en JSON i integració amb Gemini per interpretar missatges i redactar respostes naturals en català.

---

## Resum general

SFM Assistant és una demo d’un chatbot capaç d’entendre consultes senzilles sobre trens i metro de Mallorca.

L’usuari pot escriure preguntes com:

`Vull anar d'Inca a Palma`

`Quins trens hi ha d'Inca a Palma dematí?`

`Vull arribar a Palma abans de les 9 des d'Inca`

`Vull anar a Vilafranca`

El sistema interpreta el missatge, valida les estacions, consulta horaris locals i genera una resposta en català.

La IA no consulta directament els horaris. El backend és qui valida i cerca les dades. Gemini només ajuda a entendre el llenguatge natural i, quan és segur, a redactar la resposta final.

---

## Objectius del projecte

Els objectius principals són:

* Crear una demo visual d’un assistent de trens i metro.
* Respondre sempre en català.
* Entendre consultes naturals de l’usuari.
* Detectar origen, destinació, data, hora i franja horària.
* Detectar pobles o llocs sense aturada ferroviària.
* Mantenir context de conversa amb `conversation_id`.
* Consultar horaris locals estructurats.
* Evitar que Gemini inventi hores, estacions o trajectes.
* Tenir fallback per regles i plantilles quan Gemini falla.

---

## Funcionalitats principals

Actualment el projecte permet:

* Consultar pròximes sortides.
* Consultar trens dins una franja horària.
* Cercar trens que arriben abans d’una hora.
* Cercar trens que surten després d’una hora.
* Detectar consultes incompletes i demanar aclariments.
* Respondre a aclariments curts com `A Palma`, `Manacor` o `dematí`.
* Detectar llocs coneguts sense tren, com Vilafranca o Alcúdia.
* Mostrar informació de debug durant el desenvolupament.
* Guardar el `conversation_id` al navegador.

---

## Arquitectura general

El flux principal és:

Usuari
↓
Frontend React
↓
POST /chat
↓
Chat Service
↓
Intent Service

* Gemini interpreta el missatge.
* Fallback amb regles si Gemini falla.
  ↓
  Conversation Service
* Manté el context.
* Completa consultes pendents.
  ↓
  Station Service
* Valida estacions.
* Detecta pobles sense tren.
* Corregeix typos simples.
  ↓
  Train Service
* Consulta horaris locals en JSON.
  ↓
  Response Service
* Gemini redacta quan és segur.
* Template si fa falta.
  ↓
  Hallucination Guard
* Bloqueja hores inventades.
  ↓
  Resposta final al frontend

---

## Estructura del projecte

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

---

## Tecnologies utilitzades

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* Pydantic Settings
* Google Gemini API
* JSON com a base de dades local
* `zoneinfo` / `tzdata` per gestionar la zona horària

### Frontend

* React
* Vite
* JavaScript
* CSS
* LocalStorage

---

## Instal·lació ràpida

### 1. Clonar el repositori

`git clone https://github.com/ferran-artero/sfm-assistant.git`

`cd sfm-assistant`

---

## Executar el backend

Entra dins el backend:

`cd backend`

Crea un entorn virtual:

`python -m venv .venv`

Activa l’entorn virtual.

A Windows PowerShell:

`.\.venv\Scripts\Activate.ps1`

A macOS/Linux:

`source .venv/bin/activate`

Instal·la dependències:

`pip install -r requirements.txt`

Crea el fitxer `.env` a partir de `.env.example`:

`cp .env.example .env`

A Windows PowerShell:

`Copy-Item .env.example .env`

Edita `backend/.env` i afegeix la teva clau de Gemini:

APP_NAME=SFM Assistant
ENVIRONMENT=development

LLM_PROVIDER=gemini
GEMINI_API_KEY=posa_aqui_la_teva_clau
GEMINI_MODEL=gemini-3.1-flash-lite

RESPONSE_LANGUAGE=ca
USE_SAMPLE_DATA=true
DEBUG=true

Executa el backend:

`uvicorn app.main:app --reload`

El backend quedarà disponible a:

`http://127.0.0.1:8000`

Documentació automàtica:

`http://127.0.0.1:8000/docs`

---

## Executar el frontend

Obre una altra terminal i entra dins el frontend:

`cd frontend`

Instal·la dependències:

`npm install`

Executa el servidor de desenvolupament:

`npm run dev`

El frontend quedarà disponible normalment a:

`http://localhost:5173`

---

## Ús bàsic

Amb el backend i el frontend en marxa, obre:

`http://localhost:5173`

Exemples de consultes:

`Hola`

`Vull anar d'Inca a Palma`

`Quins trens hi ha d'Inca a Palma dematí?`

`Vull arribar a Palma abans de les 9 des d'Inca`

`Vull sortir d'Inca`

Després:

`A Palma`

`Vull anar a Vilafranca`

---

## API principal

### `POST /chat`

Endpoint principal del chatbot.

Request:

{
"message": "Vull anar d'Inca a Palma",
"conversation_id": null
}

Response:

{
"conversation_id": "uuid-de-la-conversa",
"response": "Resposta final en català",
"intent_source": "gemini",
"response_source": "gemini",
"debug": {
"intent": "train_query",
"intent_confidence": 0.9,
"query": {
"query_type": "next_departure",
"origin_stop_id": "inca",
"destination_stop_id": "palma",
"date": null,
"time": "now",
"time_window": null,
"departure_after": null,
"arrival_before": null,
"service_id": null
},
"results_count": 5,
"response_source": "gemini",
"llm_error": null
}
}

---

## Camps principals de resposta

`conversation_id`
Identificador de la conversa. El frontend el guarda al navegador.

`response`
Resposta final que veu l’usuari.

`intent_source`
Indica com s’ha interpretat el missatge.

Possibles valors:

* `gemini`
* `rules`
* `rules_fallback`
* `pending_context`

`response_source`
Indica com s’ha generat la resposta final.

Possibles valors:

* `gemini`
* `template`
* `template_fallback`

`debug`
Informació útil durant el desenvolupament.

---

## Endpoints útils de desenvolupament

El backend inclou endpoints de debug per provar cada part del sistema.

`GET /health`

`GET /debug/llm`

`GET /debug/intent?message=Vull anar d'Inca a Palma`

`GET /debug/station/{query}`

`GET /debug/trains/next`

`GET /debug/trains/window`

`GET /debug/trains/arrival-before`

`GET /debug/trains/departure-after`

`GET /debug/conversation/{conversation_id}`

`GET /debug/hallucination/log`

Aquests endpoints són útils durant el desenvolupament, però no estan pensats com a API pública final.

---

## Serveis principals del backend

### `ChatService`

Orquestra el flux complet del chatbot.

Coordina:

* Intent Service
* Conversation Service
* Station Service
* Train Service
* Response Service
* Hallucination Guard

### `IntentService`

Interpreta el missatge de l’usuari.

Pot usar Gemini i, si Gemini falla, torna a un sistema de regles simples.

Detecta:

* salutacions
* agraïments
* comiats
* consultes de tren
* origen i destinació
* dates relatives
* hores
* franges horàries
* llocs sense tren

### `ConversationService`

Manté context temporal de conversa en memòria RAM.

Guarda:

* missatges
* consulta pendent
* darrera consulta
* darrers resultats

Serveix per resoldre converses com:

Usuari: Vull sortir d'Inca
Bot: Cap a quina estació vols anar?
Usuari: A Palma
Bot: Cerca trens d'Inca a Palma

### `StationService`

Valida estacions i llocs.

Permet detectar:

* estacions vàlides
* àlies
* errors simples d’escriptura
* pobles coneguts sense tren

### `TrainService`

Consulta els horaris locals guardats en JSON.

Sempre retorna resultats estructurats, no text final.

### `ResponseService`

Genera la resposta final.

Pot usar Gemini per redactar respostes més naturals, però només a partir de dades verificades pel backend.

Si Gemini falla o la resposta no és segura, usa una plantilla.

### `HallucinationGuard`

Valida que Gemini no inventi hores.

Si Gemini menciona una hora que no apareix en els resultats verificats, la resposta es descarta i es torna a una plantilla segura.

---

## Dades locals

El projecte usa tres fitxers principals:

`stations.json`
Aturades vàlides, àlies, typos, línies i modes.

`places_without_train.json`
Pobles o llocs coneguts sense aturada ferroviària.

`schedules_sample.json`
Horaris locals estructurats per línies, calendaris i viatges.

El format d’horaris és semblant a un GTFS simplificat:

`routes`
Línies disponibles.

`service_calendars`
Tipus de servei: laborable, cap de setmana, metro dissabte, etc.

`trips`
Viatges complets amb `stop_times`.

Cada viatge guarda totes les aturades, no només origen i destinació. Això permet consultar trams intermedis.

---

## Prompts

El backend usa dos prompts:

`intent_prompt.txt`
Converteix el missatge de l’usuari en JSON estructurat.

`response_prompt.txt`
Redacta una resposta natural en català a partir de resultats verificats.

Gemini no ha d’inventar horaris. Només pot treballar amb informació que ja li passa el backend.

---

## Frontend

El frontend és una interfície de xat simple.

Inclou:

* pantalla de conversa
* missatges d’usuari i bot
* botons d’exemple
* estat de càrrega
* botó per reiniciar conversa
* guardat del `conversation_id` a `localStorage`
* visualització de debug durant el desenvolupament

Els colors principals estan inspirats en la identitat de SFM:

`--sfm-blue: #002e6d;`

`--sfm-green: #61a60e;`

---

## Fallbacks

El sistema no depèn completament de Gemini.

### Fallback d’intenció

Si Gemini falla interpretant el missatge:

`intent_source = rules_fallback`

El sistema intenta interpretar-lo amb regles simples.

### Fallback de resposta

Si Gemini falla redactant o inventa dades:

`response_source = template_fallback`

El sistema genera una resposta segura amb plantilla.

### Template directe

S’usa en casos controlats com:

* salutacions
* gràcies
* adeu
* fora de domini
* aclariments
* llocs sense tren
* consultes sense resultats

---

## Limitacions actuals

Aquesta aplicació és una demo i no un sistema de producció.

Limitacions conegudes:

* Les dades són locals i no provenen d’una API en temps real.
* La memòria de conversa és temporal i es perd en reiniciar el servidor.
* No hi ha base de dades persistent.
* No hi ha autenticació.
* La gestió de festius és simplificada.
* Els transbords encara són limitats.
* Gemini pot fallar per quota, latència o resposta incorrecta.
* El debug encara és visible al frontend.

---

## Errors freqüents

### Error de zona horària a Windows

Si apareix:

`ZoneInfoNotFoundError: No time zone found with key Europe/Madrid`

Instal·la `tzdata`:

`pip install tzdata`

També hauria d’estar inclòs dins `requirements.txt`.

### Gemini retorna quota excedida

Pot passar si s’esgota el límit gratuït del model configurat.

Canvia el model dins `.env`, per exemple:

GEMINI_MODEL=gemini-3.1-flash-lite

Després reinicia el backend:

`uvicorn app.main:app --reload`

### El frontend no connecta amb el backend

Comprova que el backend està actiu:

`http://127.0.0.1:8000/health`

I que el frontend apunta a:

`http://127.0.0.1:8000/chat`

---

## Roadmap

Possibles millores futures:

* Afegir SQLite.
* Importar horaris GTFS.
* Millorar suport de transbords.
* Afegir festius reals.
* Separar model Gemini per intents i per resposta.
* Afegir mode només-regles per no consumir quota.
* Afegir tests automatitzats.
* Afegir Docker.
* Afegir logs estructurats.
* Amagar el debug en mode producció.
* Millorar les respostes curtes en context.
* Afegir una vista de totes les opcions trobades.
* Afegir panell d’administració per actualitzar horaris.

---

## Seguretat

No s’ha de pujar mai el fitxer `.env` al repositori.

El fitxer `.env.example` sí que es pot mantenir perquè només és una plantilla.

Si una clau API s’ha pujat accidentalment a GitHub:

1. Revoca la clau.
2. Genera’n una de nova.
3. Actualitza `backend/.env`.
4. Elimina la clau del codi.
5. Fes commit dels canvis.

---

## Documentació específica

Aquest README dona una visió general del projecte.

Per a més detall:

`backend/README.md`
Arquitectura interna del backend, serveis, endpoints i dades.

`frontend/README.md`
Estructura del frontend, components, estils i funcionament de la interfície.

---

## Autor

Projecte desenvolupat per Ferran Artero com a demo d’un assistent intel·ligent per consultar horaris de tren i metro de Mallorca.

---

## Nota

Aquesta aplicació és una demo educativa i de desenvolupament. Les dades d’horaris carregades localment poden no correspondre sempre amb el servei real actual. Per a informació oficial i actualitzada, s’ha de consultar el servei oficial corresponent.
