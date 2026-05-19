```text
# CHECKLIST GENERAL — SFM ASSISTANT

## FASE 0 — Preparació inicial del projecte

[ ] Comprovar que l’estructura de carpetes està creada.
[ ] Crear entorn virtual de Python dins backend/.
[ ] Instal·lar dependències bàsiques.
[ ] Crear .env a partir de .env.example.
[ ] Crear .gitignore.
[ ] Fer primer commit del projecte buit.

Objectiu:
Tenir el projecte ordenat i preparat per començar a programar.
```

```text
## FASE 1 — Backend mínim amb FastAPI

[ ] Omplir requirements.txt.
[ ] Crear config.py.
[ ] Crear models.py amb ChatRequest i ChatResponse.
[ ] Crear main.py amb FastAPI.
[ ] Crear endpoint GET /health.
[ ] Crear endpoint POST /chat amb resposta fixa.
[ ] Executar uvicorn i comprovar /docs.

Objectiu:
Que el backend arrenqui i respongui encara que no tengui lògica real.
```

```text
## FASE 2 — Dades inicials de la demo

[ ] Omplir stations.json amb estacions vàlides.
[ ] Omplir places_without_train.json amb pobles sense tren.
[ ] Crear schedules_sample.json amb horaris de prova.
[ ] Definir un format clar per representar horaris.

Objectiu:
Tenir una petita base de dades falsa però controlada per poder provar el chatbot.
```

```text
## FASE 3 — Station Service

[ ] Crear funció per carregar stations.json.
[ ] Crear funció per carregar places_without_train.json.
[ ] Implementar validate_station().
[ ] Detectar estacions vàlides: Palma, Inca, Manacor, Sineu...
[ ] Detectar llocs coneguts sense tren: Vilafranca, Alcúdia, Llucmajor...
[ ] Detectar errors simples d’escriptura com “Plama” → “Palma”.

Objectiu:
Que el sistema no intenti cercar trens cap a llocs que no tenen estació.
```

```text
## FASE 4 — Train Service amb dades de prova

[ ] Carregar schedules_sample.json.
[ ] Crear search_next_departure().
[ ] Crear search_trains_in_window().
[ ] Crear search_arrival_before().
[ ] Crear search_departure_after().
[ ] Retornar sempre resultats estructurats, no text final.
[ ] Provar consultes simples d’Inca a Palma.

Objectiu:
Que el backend pugui consultar horaris sense IA.
```

```text
## FASE 5 — Conversation Service bàsic

[ ] Crear memòria temporal per conversation_id.
[ ] Guardar last_query.
[ ] Guardar last_results.
[ ] Guardar pending_query.
[ ] Detectar quan falta origen.
[ ] Detectar quan falta destinació.
[ ] Permetre aclariments simples.

Exemple:
Usuari: Quins trens surten demà d’Inca?
Bot: Cap a quina estació vols anar?
Usuari: A Palma
Bot: Demà tens aquests trens d’Inca a Palma...

Objectiu:
Que el chatbot pugui mantenir un mínim de context.
```

```text
## FASE 6 — Intent Service sense Gemini, només regles simples

[ ] Detectar salutacions.
[ ] Detectar consultes de tren bàsiques.
[ ] Detectar “gràcies” i “adeu”.
[ ] Detectar frases fora de domini.
[ ] Retornar una estructura tipus intent.

Objectiu:
Tenir una versió funcional abans d’afegir IA.
```

Aquesta fase és important. Encara que després usem Gemini, tenir unes regles mínimes ens donarà un **fallback segur** si Gemini falla.

```text
## FASE 7 — Integració de Gemini per entendre missatges

[ ] Crear llm_service.py.
[ ] Configurar GEMINI_API_KEY.
[ ] Crear prompt intent_prompt.txt.
[ ] Fer que Gemini retorni només JSON.
[ ] Crear analyze_message().
[ ] Validar que el JSON rebut és correcte.
[ ] Si Gemini falla, usar fallback de regles.

Objectiu:
Que Gemini pugui convertir llenguatge natural en dades estructurades.
```

Exemple de sortida esperada:

```json
{
  "intent": "train_query",
  "origin": "Inca",
  "destination": "Palma",
  "date": "2026-05-20",
  "time_window": "morning",
  "query_type": "list_trains",
  "missing_fields": []
}
```

```text
## FASE 8 — Response Service

[ ] Crear response_service.py.
[ ] Crear respostes segures sense Gemini.
[ ] Crear prompt response_prompt.txt.
[ ] Passar a Gemini només dades verificades.
[ ] Forçar resposta sempre en català.
[ ] Prohibir que Gemini inventi hores, estacions o trajectes.
[ ] Crear fallback amb plantilla si Gemini falla.

Objectiu:
Que les respostes sonin naturals, però només usin informació real.
```

```text
## FASE 9 — Validació anti-al·lucinacions

[ ] Extreure hores de la resposta generada per Gemini.
[ ] Comparar-les amb els horaris reals retornats per Train Service.
[ ] Si apareix una hora inventada, descartar resposta.
[ ] Retornar una plantilla segura.
[ ] Registrar l’error per debug.

Objectiu:
Evitar que Gemini s’inventi trens.
```

```text
## FASE 10 — Connectar el flux complet dins /chat

[ ] Rebre message i conversation_id.
[ ] Crear conversation_id si no existeix.
[ ] Analitzar missatge amb Intent Service.
[ ] Completar dades amb Conversation Service.
[ ] Validar origen i destinació amb Station Service.
[ ] Consultar Train Service si la consulta és completa.
[ ] Generar resposta amb Response Service.
[ ] Validar anti-al·lucinacions.
[ ] Guardar nou context.
[ ] Retornar resposta al frontend.

Objectiu:
Tenir el backend complet de la demo.
```

```text
## FASE 11 — Frontend senzill

[ ] Crear frontend amb Vite + React.
[ ] Crear una pantalla de xat simple.
[ ] Guardar conversation_id al navegador.
[ ] Enviar missatges a POST /chat.
[ ] Mostrar resposta del bot.
[ ] Afegir estat de carregant.
[ ] Afegir botó per reiniciar conversa.

Objectiu:
Tenir una demo visual usable.
```

```text
## FASE 12 — Proves finals de la demo

[ ] Provar: Hola.
[ ] Provar: Vull anar d’Inca a Palma.
[ ] Provar: Vull anar demà dematí d’Inca a Palma.
[ ] Provar: Quins trens arriben a Palma abans de les 9 des d’Inca?
[ ] Provar: I una més tard?
[ ] Provar: No, volia dir de Sineu.
[ ] Provar: Vull anar a Vilafranca.
[ ] Provar: Vull anar de Plama a Inca.
[ ] Provar: Quin temps farà demà?
[ ] Revisar que sempre respon en català.
[ ] Revisar que no inventa horaris.
```

