# Frontend — SFM Assistant

Frontend de l’assistent intel·ligent SFM Assistant.

Aquest frontend està desenvolupat amb React + Vite i ofereix una interfície de xat senzilla per consultar horaris de tren i metro de Mallorca. Es comunica amb el backend mitjançant l’endpoint `POST /chat`.

---

## Resum

El frontend permet a l’usuari interactuar amb el chatbot de manera visual.

Funcionalitats principals:

* Escriure missatges en una interfície de xat.
* Enviar consultes al backend.
* Mostrar respostes del bot.
* Guardar el `conversation_id` al navegador.
* Mantenir el context de conversa entre missatges.
* Mostrar estat de càrrega mentre el backend respon.
* Reiniciar la conversa.
* Mostrar informació de debug durant el desenvolupament.
* Usar els colors i el logo de SFM.

---

## Tecnologies utilitzades

* React
* Vite
* JavaScript
* CSS
* LocalStorage
* Fetch API

---

## Estructura del frontend

frontend/

├── public/
│   └── SFM_Color.svg
│
├── src/
│   ├── App.jsx
│   ├── App.css
│   └── main.jsx
│
├── package.json
├── vite.config.js
└── README.md

---

## Fitxers principals

### `src/App.jsx`

Conté la lògica principal del frontend.

Responsabilitats:

* mantenir l’estat dels missatges
* enviar missatges al backend
* guardar i recuperar el `conversation_id`
* mostrar respostes del bot
* mostrar estat de càrrega
* reiniciar la conversa
* mostrar informació de debug

---

### `src/App.css`

Conté tots els estils de la interfície.

Defineix:

* colors principals
* layout general
* targeta de xat
* capçalera
* botons d’exemple
* bombolles de missatge
* formulari d’enviament
* estat de càrrega
* panell de debug
* disseny responsive

---

### `src/main.jsx`

Punt d’entrada de React.

Renderitza el component principal `App`.

---

### `public/SFM_Color.svg`

Logo de SFM utilitzat a la capçalera de l’aplicació.

---

## Instal·lació

Des de la carpeta del projecte:

`cd frontend`

Instal·la les dependències:

`npm install`

---

## Executar el frontend

Per iniciar el servidor de desenvolupament:

`npm run dev`

Normalment Vite obrirà el frontend a:

`http://localhost:5173`

També pot aparèixer com:

`http://127.0.0.1:5173`

---

## Requisit important

Abans d’usar el frontend, el backend ha d’estar en marxa.

Des de la carpeta `backend/`:

`uvicorn app.main:app --reload`

El backend ha d’estar disponible a:

`http://127.0.0.1:8000`

Pots comprovar-ho obrint:

`http://127.0.0.1:8000/health`

---

## Connexió amb el backend

El frontend envia els missatges a:

`http://127.0.0.1:8000/chat`

Això està definit dins `src/App.jsx`:

`const API_URL = "http://127.0.0.1:8000/chat";`

Durant el desenvolupament local, aquesta URL és suficient.

Si el backend es desplega en un servidor o canvia de port, s’haurà d’actualitzar aquesta constant o substituir-la per una variable d’entorn.

---

## Flux de funcionament

El flux principal del frontend és:

Usuari escriu un missatge
↓
El frontend afegeix el missatge a la conversa
↓
El frontend envia `message` i `conversation_id` a `POST /chat`
↓
El backend interpreta i respon
↓
El frontend guarda el nou `conversation_id` si encara no existia
↓
El frontend mostra la resposta del bot
↓
El frontend actualitza el panell de debug

---

## Request enviat al backend

Quan l’usuari envia un missatge, el frontend fa una petició `POST /chat`.

Exemple:

{
"message": "Vull anar d'Inca a Palma",
"conversation_id": null
}

Si ja hi ha una conversa guardada, s’envia així:

{
"message": "A Palma",
"conversation_id": "uuid-de-la-conversa"
}

---

## Resposta esperada del backend

El backend retorna una resposta amb aquest format:

{
"conversation_id": "uuid-de-la-conversa",
"response": "Resposta final del bot",
"intent_source": "gemini",
"response_source": "gemini",
"debug": {
"intent": "train_query",
"results_count": 5
}
}

El frontend mostra principalment el camp:

`response`

I usa aquests camps per debug:

* `intent_source`
* `response_source`
* `debug`

---

## Gestió del `conversation_id`

El frontend guarda el `conversation_id` dins `localStorage`.

Clau utilitzada:

`sfm_conversation_id`

Això permet mantenir el context de conversa encara que l’usuari enviï diversos missatges seguits.

Exemple:

Usuari:

`Vull sortir d'Inca`

Bot:

`Cap a quina estació vols anar des de inca?`

Usuari:

`A Palma`

El frontend envia el mateix `conversation_id`, i el backend pot completar la consulta com:

`Inca → Palma`

---

## Reiniciar conversa

El botó `Reiniciar conversa` fa tres coses:

* elimina el `conversation_id` de `localStorage`
* buida els missatges anteriors
* torna a mostrar el missatge inicial del bot

Això crea una conversa nova a la pròxima consulta.

---

## Missatge inicial

Quan s’obre l’aplicació, es mostra aquest missatge inicial:

`Hola! Som l’assistent de SFM. Puc ajudar-te a consultar horaris de tren i metro de Mallorca.`

Aquest missatge no ve del backend. És un missatge inicial definit al frontend.

---

## Botons d’exemple

El frontend inclou botons per provar consultes ràpides:

* `Inca → Palma`
* `Dematí`
* `Abans de les 9`
* `Poble sense tren`

Aquests botons no envien directament el missatge. Només omplen el camp de text perquè l’usuari pugui enviar-lo.

---

## Estat de càrrega

Quan l’usuari envia un missatge, el frontend activa `loading`.

Durant aquest estat:

* es desactiva l’input
* es desactiva el botó d’enviar
* es mostra una animació amb punts
* el botó mostra `Cercant...`

Quan arriba la resposta o hi ha un error, `loading` torna a `false`.

---

## Gestió d’errors

Si el frontend no pot connectar amb el backend, mostra aquest missatge:

`Ara mateix no puc connectar amb el servidor. Comprova que el backend està en marxa.`

Aquest error pot aparèixer si:

* el backend no està executant-se
* el port del backend és diferent
* hi ha un problema de CORS
* l’endpoint `/chat` ha fallat
* el backend ha retornat un error HTTP

---

## Debug al frontend

Durant el desenvolupament, el frontend mostra un petit panell de debug.

Aquest panell mostra:

* identificador curt de conversa
* origen de la interpretació del missatge
* origen de la resposta final
* possibles errors de connexió

Exemples:

`intent: gemini`

`intent: rules_fallback`

`resposta: gemini`

`resposta: template`

`resposta: template_fallback`

---

## Significat dels valors de debug

### `intent_source`

Indica com s’ha interpretat el missatge.

Valors possibles:

* `gemini`
* `rules`
* `rules_fallback`
* `pending_context`

### `response_source`

Indica com s’ha generat la resposta final.

Valors possibles:

* `gemini`
* `template`
* `template_fallback`

### `template`

Vol dir que el backend ha generat una resposta segura amb plantilla.

S’usa en casos com:

* salutació
* gràcies
* adeu
* fora de domini
* aclariment
* poble sense tren
* consulta sense resultats

### `template_fallback`

Vol dir que el backend ha intentat usar Gemini per redactar, però Gemini ha fallat o ha generat una resposta no segura.

En aquest cas, el backend torna a una resposta segura amb plantilla.

---

## Estils i identitat visual

El frontend utilitza colors inspirats en SFM.

Colors principals:

`--sfm-blue: #002e6d;`

`--sfm-green: #61a60e;`

Altres colors utilitzats:

`--sfm-blue-soft: #e9f0fa;`

`--sfm-green-soft: #eef7e7;`

`--background: #f4f7fb;`

`--surface: #ffffff;`

La interfície està pensada com una targeta central de xat amb:

* capçalera amb logo
* botons d’exemple
* zona de missatges
* formulari d’entrada
* panell de debug

---

## Responsive design

El CSS inclou adaptació per pantalles petites.

En mòbil:

* la targeta ocupa tota la pantalla
* el formulari passa a disposició vertical
* el botó d’enviar ocupa tota l’amplada
* el logo es redueix
* els marges laterals es fan més petits

---

## Com provar el frontend

Amb backend i frontend en marxa, obre:

`http://localhost:5173`

Prova aquestes consultes:

### Salutació

`Hola`

Resposta esperada:

El bot saluda i explica que pot ajudar amb horaris de tren i metro.

---

### Consulta directa

`Vull anar d'Inca a Palma`

Resposta esperada:

El bot cerca pròximes opcions d’Inca a Palma.

---

### Consulta amb franja

`Quins trens hi ha d'Inca a Palma dematí?`

Resposta esperada:

El bot mostra opcions dins la franja del dematí.

---

### Consulta amb hora límit

`Vull arribar a Palma abans de les 9 des d'Inca`

Resposta esperada:

El bot mostra trens que arriben abans de les 09:00.

---

### Consulta incompleta

`Vull sortir d'Inca`

Resposta esperada:

El bot demana la destinació.

Després escriu:

`A Palma`

Resposta esperada:

El bot completa la consulta i cerca trens d’Inca a Palma.

---

### Poble sense tren

`Vull anar a Vilafranca`

Resposta esperada:

El bot indica que Vilafranca de Bonany no apareix com a aturada dins la xarxa carregada.

---

### Fora de domini

`Quin temps farà demà?`

Resposta esperada:

El bot indica que només pot ajudar amb consultes de tren i metro de Mallorca.

---

## Scripts disponibles

### Instal·lar dependències

`npm install`

### Executar en mode desenvolupament

`npm run dev`

### Generar build de producció

`npm run build`

### Previsualitzar build

`npm run preview`

---

## Build de producció

Per generar una versió de producció:

`npm run build`

Això crearà una carpeta:

`dist/`

La carpeta `dist/` es pot desplegar en serveis com:

* Vercel
* Netlify
* GitHub Pages
* servidor propi
* qualsevol hosting d’arxius estàtics

---

## Variables i configuració futura

Actualment la URL del backend està definida directament a `App.jsx`.

Per una versió més neta, es podria crear un fitxer `.env` del frontend amb:

`VITE_API_URL=http://127.0.0.1:8000/chat`

I dins `App.jsx` usar:

`const API_URL = import.meta.env.VITE_API_URL;`

Això facilitaria canviar entre desenvolupament i producció.

---

## Problemes freqüents

### El frontend no obre

Comprova que has instal·lat dependències:

`npm install`

I executa:

`npm run dev`

---

### El frontend no connecta amb el backend

Comprova que el backend està actiu:

`http://127.0.0.1:8000/health`

També comprova que `API_URL` dins `App.jsx` sigui:

`http://127.0.0.1:8000/chat`

---

### Error de CORS

El backend ha de permetre l’origen del frontend.

Durant desenvolupament, el backend permet:

`http://localhost:5173`

`http://127.0.0.1:5173`

Si uses un altre port o domini, s’ha d’afegir a la configuració CORS del backend.

---

### El bot no recorda la conversa

Comprova que el navegador no estigui bloquejant `localStorage`.

També pots mirar si existeix aquesta clau:

`sfm_conversation_id`

Si vols començar de zero, prem el botó:

`Reiniciar conversa`

---

### El bot respon amb fallback

Si el frontend mostra:

`resposta: template_fallback`

Vol dir que el backend ha intentat usar Gemini per redactar, però ha tornat a una plantilla segura.

Això no és un error del frontend. S’ha de revisar el backend, la quota de Gemini o el `HallucinationGuard`.

---

## Limitacions actuals

El frontend és una demo senzilla.

Limitacions actuals:

* No hi ha login.
* No hi ha historial persistent de converses.
* Només es guarda el `conversation_id`, no tots els missatges.
* Si es recarrega la pàgina, es manté el `conversation_id`, però no es recuperen els missatges antics.
* El panell de debug és visible a la interfície.
* La URL del backend està hardcoded.
* No hi ha tests frontend.
* No hi ha mode producció separat.

---

## Millores futures

Possibles millores:

* Crear variable `VITE_API_URL`.
* Afegir mode producció sense debug visible.
* Guardar historial de missatges a `localStorage`.
* Afegir botó per mostrar/ocultar debug.
* Afegir vista de resultats en targetes.
* Afegir icones per tren i metro.
* Afegir selector d’idioma en el futur.
* Afegir tests amb Vitest o React Testing Library.
* Afegir millor accessibilitat.
* Afegir animacions més suaus.
* Afegir desplegament a Vercel o Netlify.
* Afegir suport per tema clar/fosc.

---

## Desenvolupament recomanat

Flux recomanat de treball:

1. Arrencar el backend.
2. Comprovar `http://127.0.0.1:8000/health`.
3. Arrencar el frontend.
4. Obrir `http://localhost:5173`.
5. Provar una salutació.
6. Provar una consulta completa.
7. Provar una consulta incompleta.
8. Revisar el panell de debug.
9. Si hi ha error, mirar la terminal del backend.

---

## Relació amb el backend

Aquest frontend depèn del backend de SFM Assistant.

La documentació detallada del backend es troba a:

`../backend/README.md`

El backend és responsable de:

* interpretar el missatge
* mantenir context
* consultar dades
* generar resposta
* validar anti-al·lucinacions

El frontend només mostra la conversa i envia/reb missatges.

---

## Nota final

Aquest frontend forma part de SFM Assistant, una demo educativa i de desenvolupament per consultar horaris de tren i metro de Mallorca.

La interfície està pensada per ser simple, clara i útil per demostrar el funcionament del chatbot.
