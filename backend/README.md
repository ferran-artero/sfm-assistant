Basat en el backend actual: `main.py` exposa `/chat`, `/health` i endpoints de debug; `models.py` ja retorna `conversation_id`, `response`, `intent_source`, `response_source` i `debug`; i els serveis principals estan separats en `chat_service`, `intent_service`, `conversation_service`, `train_service`, `response_service`, `hallucination_guard`, `station_service` i `llm_service`.   

# Backend — SFM Assistant

Backend de l’assistent intel·ligent SFM Assistant.

Aquest backend està desenvolupat amb FastAPI i s’encarrega de rebre missatges de l’usuari, interpretar-los, mantenir context de conversa, validar estacions, consultar horaris locals i generar una resposta final en català.

La IA no consulta directament els horaris. Gemini només s’utilitza per entendre millor el llenguatge natural i per redactar respostes quan el backend ja ha verificat les dades.

---

## Resum

El backend permet respondre consultes com:

`Vull anar d'Inca a Palma`

`Quins trens hi ha d'Inca a Palma dematí?`

`Vull arribar a Palma abans de les 9 des d'Inca`

`Vull sortir d'Inca`

`A Palma`

`Vull anar a Vilafranca`

El sistema pot:

* Interpretar missatges naturals.
* Detectar salutacions, agraïments i comiats.
* Detectar consultes fora de domini.
* Detectar origen, destinació, data, hora i franja horària.
* Mantenir una conversa amb `conversation_id`.
* Guardar consultes pendents.
* Validar estacions i pobles sense tren.
* Consultar horaris locals en JSON.
* Redactar respostes naturals en català.
* Usar fallback si Gemini falla.
* Bloquejar respostes on Gemini inventi hores.

---

## Tecnologies utilitzades

* Python
* FastAPI
* Uvicorn
* Pydantic
* Pydantic Settings
* Google Gemini API
* JSON com a base de dades local
* `zoneinfo`
* `tzdata`

---

## Estructura del backend

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

---

## Fitxers principals

### `main.py`

Punt d’entrada de FastAPI.

Defineix:

* configuració general de l’app
* CORS per al frontend
* endpoint principal `/chat`
* endpoints de debug
* endpoint `/health`

---

### `config.py`

Carrega la configuració del projecte des del fitxer `.env`.

Variables principals:

* `APP_NAME`
* `ENVIRONMENT`
* `LLM_PROVIDER`
* `GEMINI_API_KEY`
* `GEMINI_MODEL`
* `RESPONSE_LANGUAGE`
* `USE_SAMPLE_DATA`
* `DEBUG`

---

### `models.py`

Defineix els models Pydantic de request i response.

Model principal de request:

`ChatRequest`

Conté:

* `message`
* `conversation_id`

Model principal de response:

`ChatResponse`

Conté:

* `conversation_id`
* `response`
* `intent_source`
* `response_source`
* `debug`

---

## Instal·lació

### 1. Entrar dins el backend

`cd backend`

### 2. Crear entorn virtual

`python -m venv .venv`

### 3. Activar entorn virtual

A Windows PowerShell:

`.\.venv\Scripts\Activate.ps1`

A macOS/Linux:

`source .venv/bin/activate`

### 4. Instal·lar dependències

`pip install -r requirements.txt`

---

## Configuració

Crea un fitxer `.env` a partir de `.env.example`.

A Windows PowerShell:

`Copy-Item .env.example .env`

A macOS/Linux:

`cp .env.example .env`

Exemple de `.env`:

APP_NAME=SFM Assistant
ENVIRONMENT=development

LLM_PROVIDER=gemini
GEMINI_API_KEY=posa_aqui_la_teva_clau
GEMINI_MODEL=gemini-3.1-flash-lite

RESPONSE_LANGUAGE=ca
USE_SAMPLE_DATA=true
DEBUG=true

Important:

* `.env` no s’ha de pujar mai a GitHub.
* `.env.example` sí que pot estar al repositori.
* Si una API key s’ha pujat accidentalment, s’ha de revocar i substituir.

---

## Executar el backend

Des de la carpeta `backend/`:

`uvicorn app.main:app --reload`

El backend quedarà disponible a:

`http://127.0.0.1:8000`

Documentació automàtica de FastAPI:

`http://127.0.0.1:8000/docs`

Endpoint de salut:

`http://127.0.0.1:8000/health`

---

## Endpoint principal

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

## Camps de resposta

### `conversation_id`

Identificador de la conversa.

Si l’usuari no envia cap `conversation_id`, el backend en crea un de nou.

El frontend guarda aquest valor al navegador per mantenir el context.

---

### `response`

Resposta final que s’ha de mostrar a l’usuari.

Sempre ha d’estar en català.

---

### `intent_source`

Indica com s’ha interpretat el missatge.

Possibles valors:

* `gemini`
* `rules`
* `rules_fallback`
* `pending_context`

---

### `response_source`

Indica com s’ha generat la resposta final.

Possibles valors:

* `gemini`
* `template`
* `template_fallback`

---

### `debug`

Informació útil durant desenvolupament.

Pot incloure:

* intent detectat
* query estructurada
* nombre de resultats
* error de Gemini
* camps pendents
* consulta pendent

---

## Flux intern de `/chat`

El flux principal és:

Usuari envia missatge
↓
`ChatService` rep el missatge
↓
`IntentService` interpreta el missatge
↓
`ConversationService` completa informació pendent
↓
`StationService` valida estacions i pobles sense tren
↓
`TrainService` consulta horaris
↓
`ResponseService` genera resposta
↓
`HallucinationGuard` valida que Gemini no inventi hores
↓
El backend retorna `ChatResponse`

---

## Serveis del backend

## `ChatService`

Fitxer:

`app/services/chat_service.py`

És el servei orquestrador.

Responsabilitats:

* rebre el missatge
* crear o recuperar `conversation_id`
* guardar missatges de l’usuari i del bot
* cridar `IntentService`
* cridar `ConversationService`
* gestionar consultes pendents
* consultar `TrainService`
* cridar `ResponseService`
* retornar `ChatResponse`

També resol casos com:

`Vull sortir d'Inca`

Resposta:

`Cap a quina estació vols anar des de inca?`

Després:

`A Palma`

I completa la consulta com:

`Inca → Palma`

---

## `IntentService`

Fitxer:

`app/services/intent_service.py`

S’encarrega de convertir text lliure en una estructura d’intenció.

Primer intenta usar Gemini. Si Gemini falla, usa regles simples com a fallback.

Detecta:

* `greeting`
* `thanks`
* `goodbye`
* `train_query`
* `out_of_domain`
* `empty`

També detecta:

* origen
* destinació
* data
* hora
* franja horària
* tipus de consulta
* llocs sense tren

Exemple d’entrada:

`Vull anar demà dematí d'Inca a Palma`

Exemple de sortida interna:

{
"intent": "train_query",
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

---

## `ConversationService`

Fitxer:

`app/services/conversation_service.py`

Manté memòria temporal en RAM.

Guarda:

* `messages`
* `last_query`
* `last_results`
* `pending_query`

Aquesta memòria permet converses amb aclariments.

Exemple:

Usuari:

`Vull anar a Inca`

El sistema detecta:

{
"destination_stop_id": "inca",
"origin_stop_id": null
}

Resposta:

`Des de quina estació vols sortir per anar a inca?`

Usuari:

`Manacor`

El sistema completa:

{
"origin_stop_id": "manacor",
"destination_stop_id": "inca"
}

La memòria és temporal. Si es reinicia `uvicorn`, es perd.

---

## `StationService`

Fitxer:

`app/services/station_service.py`

Valida estacions i llocs coneguts.

Funcions principals:

* carregar `stations.json`
* carregar `places_without_train.json`
* normalitzar text
* detectar àlies
* detectar typos simples
* diferenciar estacions reals de pobles sense tren

Exemples:

`Palma`
→ estació vàlida

`Plama`
→ possible typo de Palma

`Vilafranca`
→ lloc conegut sense tren

`Alcúdia`
→ lloc conegut sense tren

---

## `TrainService`

Fitxer:

`app/services/train_service.py`

Consulta els horaris locals de `schedules_sample.json`.

Funcions principals:

* `search_next_departure()`
* `search_trains_in_window()`
* `search_arrival_before()`
* `search_departure_after()`
* `search_departures_from_station()`
* `search_arrivals_to_station()`

Aquest servei sempre retorna dades estructurades.

No genera text final.

Exemple de resultat intern:

{
"trip_id": "T1_WEEKDAY_INCA_PALMA_0805",
"route_id": "T1",
"route_name": "T1 Palma - Inca",
"service_id": "train_weekday",
"headsign": "Palma",
"origin": {
"stop_id": "inca",
"sequence": 1,
"time": "08:05"
},
"destination": {
"stop_id": "palma",
"sequence": 16,
"time": "08:43"
},
"duration_minutes": 38
}

---

## `ResponseService`

Fitxer:

`app/services/response_service.py`

Genera la resposta final per a l’usuari.

Casos principals:

* salutacions → template
* gràcies → template
* adeu → template
* fora de domini → template
* consulta incompleta → template
* poble sense tren → template
* consulta sense resultats → template
* consulta amb resultats → Gemini
* error de Gemini → `template_fallback`

Gemini només rep dades verificades pel backend.

---

## `HallucinationGuard`

Fitxer:

`app/services/hallucination_guard.py`

Evita que Gemini inventi hores.

Funcionament:

1. Extreu hores de la resposta generada.
2. Extreu hores dels resultats reals de `TrainService`.
3. Compara les hores.
4. Si Gemini menciona una hora que no apareix als resultats, descarta la resposta.
5. `ResponseService` retorna una plantilla segura.

Exemple:

Resultats reals:

`08:05`, `08:43`

Resposta de Gemini:

`El tren surt a les 08:10`

Resultat:

`08:10` no existeix als resultats → resposta descartada.

---

## `LLMService`

Fitxer:

`app/services/llm_service.py`

Servei genèric per comunicar-se amb Gemini.

Responsabilitats:

* crear client Gemini
* enviar prompts
* forçar resposta JSON
* parsejar resposta
* detectar si Gemini està disponible
* exposar estat a `/debug/llm`

---

## Dades locals

## `stations.json`

Conté les estacions i aturades ferroviàries o de metro carregades a la demo.

Inclou:

* `stop_id`
* `display_name`
* `official_name`
* `aliases`
* `common_typos`
* `modes`
* `routes`
* `valid_rail_stop`
* `valid_train_station`

Serveix perquè el sistema pugui saber si un lloc és una estació vàlida.

---

## `places_without_train.json`

Conté pobles o llocs coneguts de Mallorca que no apareixen com a aturada dins la xarxa carregada.

Exemples:

* Vilafranca de Bonany
* Alcúdia
* Llucmajor
* Campos
* Santanyí
* Artà

Serveix per evitar que el sistema intenti cercar trens cap a llocs sense estació.

---

## `schedules_sample.json`

Conté els horaris locals estructurats.

Estructura general:

{
"metadata": {},
"routes": [],
"service_calendars": [],
"trips": []
}

Cada `trip` representa un viatge complet amb totes les seves aturades.

Exemple conceptual:

{
"trip_id": "T1_WEEKDAY_PALMA_INCA_0555",
"route_id": "T1",
"service_id": "train_weekday",
"direction_id": 0,
"headsign": "Inca",
"stop_times": [
{
"stop_id": "palma",
"sequence": 1,
"time": "05:55"
},
{
"stop_id": "inca",
"sequence": 16,
"time": "06:31"
}
]
}

El sistema no guarda només trajectes origen-destinació. Guarda viatges complets amb `stop_times`, cosa que permet consultar trams intermedis.

---

## Tipus de consulta suportats

El backend pot treballar amb aquests `query_type`:

### `next_departure`

Cerca les pròximes sortides.

Exemple:

`Vull anar d'Inca a Palma`

---

### `list_trains`

Cerca diversos trens dins una franja.

Exemple:

`Quins trens hi ha d'Inca a Palma dematí?`

---

### `departure_after`

Cerca trens que surten després d’una hora.

Exemple:

`Vull sortir d'Inca després de les 17 cap a Palma`

---

### `arrival_before`

Cerca trens que arriben abans d’una hora.

Exemple:

`Vull arribar a Palma abans de les 9 des d'Inca`

---

### `departures_from_station`

Cerca sortides des d’una estació.

Exemple:

`Quins trens surten d'Inca demà dematí?`

---

### `arrivals_to_station`

Cerca arribades a una estació.

Exemple:

`Quins trens arriben a Palma dematí?`

---

### `later`

Consulta relativa.

Exemple:

`I un més tard?`

---

### `earlier`

Consulta relativa.

Exemple:

`I un abans?`

---

## Franges horàries

Les franges horàries internes són:

`morning`
06:00 - 12:00

`midday`
12:00 - 15:00

`afternoon`
15:00 - 20:00

`evening`
20:00 - 23:59

---

## Calendaris de servei

El backend pot treballar amb diferents `service_id`, segons el dia i el mode.

Exemples:

`train_weekday`
Tren en dia laborable.

`train_weekend_holiday`
Tren en dissabte, diumenge o festiu.

`metro_weekday`
Metro en dia laborable.

`metro_saturday`
Metro en dissabte.

`metro_no_service`
Cas especial per dies sense servei de metro carregat.

---

## Prompts

## `intent_prompt.txt`

Prompt que Gemini usa per convertir text natural en JSON estructurat.

Objectiu:

Usuari:

`Vull anar demà dematí d'Inca a Palma`

Sortida esperada:

{
"intent": "train_query",
"confidence": 0.9,
"query": {
"query_type": "list_trains",
"origin_text": "Inca",
"destination_text": "Palma",
"date": "tomorrow",
"time": null,
"time_window": "morning",
"departure_after": null,
"arrival_before": null,
"service_id": null
},
"reason": "L'usuari vol consultar horaris d'un trajecte."
}

---

## `response_prompt.txt`

Prompt que Gemini usa per redactar una resposta natural.

Regles principals:

* respondre sempre en català
* no inventar hores
* no inventar estacions
* no inventar trajectes
* no dir que ha consultat dades en temps real
* usar només `results_json`
* si no hi ha resultats, explicar-ho clarament

---

## Fallbacks

El backend està dissenyat perquè continuï funcionant encara que Gemini falli.

### Fallback d’intenció

Si Gemini falla interpretant el missatge:

`intent_source = rules_fallback`

El sistema usa el parser de regles.

---

### Fallback de resposta

Si Gemini falla redactant:

`response_source = template_fallback`

El sistema genera una resposta amb plantilla segura.

---

### Templates directes

S’usen en casos controlats:

* salutacions
* gràcies
* adeu
* fora de domini
* consultes incompletes
* llocs sense tren
* consultes sense resultats

---

## Endpoints disponibles

## Endpoint principal

### `POST /chat`

Request:

{
"message": "Vull anar d'Inca a Palma",
"conversation_id": null
}

Response:

{
"conversation_id": "...",
"response": "...",
"intent_source": "gemini",
"response_source": "gemini",
"debug": {}
}

---

## Endpoints de debug

### `GET /health`

Comprova si el backend està actiu.

---

### `GET /debug/llm`

Mostra l’estat de Gemini.

Útil per veure:

* model configurat
* si hi ha API key
* si la key és placeholder
* si Gemini està disponible

---

### `GET /debug/intent`

Analitza un missatge sense executar tot el flux.

Exemple:

`/debug/intent?message=Vull anar d'Inca a Palma`

---

### `GET /debug/station/{query}`

Valida una estació o lloc.

Exemples:

`/debug/station/Palma`

`/debug/station/Plama`

`/debug/station/Vilafranca`

---

### `GET /debug/trains/next`

Cerca pròximes sortides.

Exemple:

`/debug/trains/next?origin=inca&destination=palma&after_time=08:00&service_id=train_weekday&limit=3`

---

### `GET /debug/trains/window`

Cerca trens dins una finestra horària.

---

### `GET /debug/trains/arrival-before`

Cerca trens que arriben abans d’una hora.

---

### `GET /debug/trains/departure-after`

Cerca trens que surten després d’una hora.

---

### `GET /debug/conversation/{conversation_id}`

Mostra el context guardat d’una conversa.

---

### `DELETE /debug/conversation/{conversation_id}`

Elimina el context d’una conversa.

---

### `GET /debug/response/simple`

Prova respostes simples per template.

---

### `GET /debug/response/trains`

Prova la generació de resposta a partir de resultats de tren.

---

### `GET /debug/response/place-without-train`

Prova resposta per lloc conegut sense tren.

---

### `GET /debug/hallucination/check`

Valida manualment una resposta contra resultats reals.

---

### `GET /debug/hallucination/log`

Mostra errors recents detectats pel `HallucinationGuard`.

---

### `DELETE /debug/hallucination/log`

Neteja el log d’al·lucinacions.

---

## Casos de prova recomanats

### Salutació

`Hola`

Resposta esperada:

Salutació del bot.

---

### Consulta directa

`Vull anar d'Inca a Palma`

Resposta esperada:

Pròximes opcions d’Inca a Palma.

---

### Consulta amb franja

`Quins trens hi ha d'Inca a Palma dematí?`

Resposta esperada:

Opcions dins la franja del dematí.

---

### Consulta amb hora límit

`Vull arribar a Palma abans de les 9 des d'Inca`

Resposta esperada:

Trens que arriben abans de les 09:00.

---

### Consulta incompleta

`Vull sortir d'Inca`

Resposta esperada:

El bot demana destinació.

Després:

`A Palma`

Resposta esperada:

El bot completa la consulta i cerca Inca → Palma.

---

### Poble sense tren

`Vull anar a Vilafranca`

Resposta esperada:

El bot indica que Vilafranca de Bonany no apareix com a aturada dins la xarxa carregada.

---

### Fora de domini

`Quin temps farà demà?`

Resposta esperada:

El bot indica que només pot ajudar amb consultes de tren i metro.

---

## Logs i debug

Durant desenvolupament és útil mirar:

* resposta de `/chat`
* `intent_source`
* `response_source`
* camp `debug`
* terminal del backend
* `/debug/llm`
* `/debug/hallucination/log`

Valors habituals:

`intent_source = gemini`
Gemini ha interpretat el missatge.

`intent_source = rules_fallback`
Gemini ha fallat i s’han usat regles.

`intent_source = pending_context`
El missatge s’ha usat per completar una consulta pendent.

`response_source = gemini`
Gemini ha redactat la resposta final.

`response_source = template`
Resposta generada amb plantilla.

`response_source = template_fallback`
Gemini ha fallat o ha generat una resposta no segura.

---

## Errors freqüents

### `ZoneInfoNotFoundError`

Error:

`ZoneInfoNotFoundError: No time zone found with key Europe/Madrid`

Solució:

`pip install tzdata`

També comprova que `tzdata` estigui dins `requirements.txt`.

---

### Gemini no està disponible

Comprova:

`/debug/llm`

Possibles causes:

* falta `GEMINI_API_KEY`
* la key és placeholder
* el model no és correcte
* quota superada
* error temporal de Gemini

---

### Quota excedida de Gemini

Si surt error `429 RESOURCE_EXHAUSTED`, pots:

* esperar que es reiniciï la quota
* canviar temporalment de model
* reduir crides a Gemini
* usar més templates
* separar model d’intenció i model de resposta en el futur

Exemple de model lleuger:

GEMINI_MODEL=gemini-3.1-flash-lite

---

### El frontend no rep resposta

Comprova:

`http://127.0.0.1:8000/health`

Si no respon, el backend no està arrancat correctament.

---

## Limitacions actuals

Aquest backend és una demo.

Limitacions conegudes:

* Les dades són locals i poden no estar actualitzades.
* No consulta una API oficial en temps real.
* La memòria de conversa és en RAM.
* La memòria es perd en reiniciar el servidor.
* No hi ha base de dades persistent.
* No hi ha autenticació.
* Els festius estan simplificats.
* Els transbords encara són limitats.
* Gemini pot fallar per quota o format de resposta.
* Encara hi ha endpoints de debug exposats.

---

## Millores futures

Possibles millores:

* Afegir SQLite o PostgreSQL.
* Importar dades GTFS oficials.
* Afegir suport complet de transbords.
* Modelar festius reals.
* Separar model Gemini per intents i per respostes.
* Afegir mode sense Gemini.
* Afegir tests automatitzats.
* Afegir logs estructurats.
* Afegir Docker.
* Afegir autenticació.
* Amagar endpoints de debug en producció.
* Millorar el `HallucinationGuard` per detectar també contradiccions textuals.
* Afegir monitorització de quota Gemini.

---

## Seguretat

No pugis mai `.env` al repositori.

`.env` conté secrets.

`.env.example` és segur perquè només conté placeholders.

Si una API key s’ha exposat:

1. Revoca la clau.
2. Genera’n una de nova.
3. Actualitza `backend/.env`.
4. Elimina la clau del codi.
5. Fes commit i push dels canvis.

---

## Desenvolupament recomanat

Flux recomanat per treballar:

1. Activar entorn virtual.
2. Arrencar backend amb `uvicorn`.
3. Obrir `/docs`.
4. Comprovar `/debug/llm`.
5. Provar `/debug/intent`.
6. Provar `/chat`.
7. Revisar `intent_source`, `response_source` i `debug`.
8. Mirar la terminal si apareix `template_fallback`.

---

## Scripts útils

Activar entorn virtual a Windows:

`.\.venv\Scripts\Activate.ps1`

Instal·lar dependències:

`pip install -r requirements.txt`

Executar backend:

`uvicorn app.main:app --reload`

Obrir documentació:

`http://127.0.0.1:8000/docs`

Comprovar salut:

`http://127.0.0.1:8000/health`

---

## Nota final

Aquest backend forma part de SFM Assistant, una demo educativa i de desenvolupament per consultar horaris de tren i metro de Mallorca.

La informació retornada depèn de les dades locals carregades dins `app/data/`. Per a informació oficial i actualitzada, s’ha de consultar sempre el servei oficial corresponent.
