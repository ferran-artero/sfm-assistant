import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000/chat";
const STORAGE_KEY = "sfm_conversation_id";

const initialMessages = [
  {
    role: "bot",
    content:
      "Hola! Som l’assistent de SFM. Puc ajudar-te a consultar horaris de tren i metro de Mallorca.",
  },
];

function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastDebug, setLastDebug] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const storedConversationId = localStorage.getItem(STORAGE_KEY);

    if (storedConversationId) {
      setConversationId(storedConversationId);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const sendMessage = async (event) => {
    event.preventDefault();

    const trimmedMessage = input.trim();

    if (!trimmedMessage || loading) {
      return;
    }

    const userMessage = {
      role: "user",
      content: trimmedMessage,
    };

    setMessages((previousMessages) => [...previousMessages, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmedMessage,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Error HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.conversation_id) {
        setConversationId(data.conversation_id);
        localStorage.setItem(STORAGE_KEY, data.conversation_id);
      }

      setLastDebug({
        intent_source: data.intent_source,
        response_source: data.response_source,
        debug: data.debug,
      });

      const botMessage = {
        role: "bot",
        content: data.response,
        meta: {
          intent_source: data.intent_source,
          response_source: data.response_source,
        },
      };

      setMessages((previousMessages) => [...previousMessages, botMessage]);
    } catch (error) {
      const errorMessage = {
        role: "bot",
        content:
          "Ara mateix no puc connectar amb el servidor. Comprova que el backend està en marxa.",
        error: true,
      };

      setMessages((previousMessages) => [...previousMessages, errorMessage]);
      setLastDebug({
        error: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  const resetConversation = () => {
    localStorage.removeItem(STORAGE_KEY);
    setConversationId(null);
    setMessages(initialMessages);
    setInput("");
    setLastDebug(null);
  };

  const handleExampleClick = (text) => {
    setInput(text);
  };

  return (
    <main className="app-shell">
      <section className="chat-card">
        <header className="chat-header">
          <div className="brand">
            <img src="/SFM_Color.svg" alt="SFM" className="brand-logo" />
            <div>
              <h1>Assistent SFM</h1>
              <p>Consulta horaris de tren i metro de Mallorca</p>
            </div>
          </div>

          <button className="reset-button" onClick={resetConversation}>
            Reiniciar conversa
          </button>
        </header>

        <section className="examples">
          <button onClick={() => handleExampleClick("Vull anar d'Inca a Palma")}>
            Inca → Palma
          </button>
          <button
            onClick={() =>
              handleExampleClick("Quins trens hi ha d'Inca a Palma dematí?")
            }
          >
            Dematí
          </button>
          <button
            onClick={() =>
              handleExampleClick("Vull arribar a Palma abans de les 9 des d'Inca")
            }
          >
            Abans de les 9
          </button>
          <button onClick={() => handleExampleClick("Vull anar a Vilafranca")}>
            Poble sense tren
          </button>
        </section>

        <section className="messages" aria-live="polite">
          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={`message ${message.role} ${
                message.error ? "message-error" : ""
              }`}
            >
              <div className="message-bubble">
                <p>{message.content}</p>

                {message.meta?.intent_source || message.meta?.response_source ? (
                  <div className="message-meta">
                    {message.meta.intent_source && (
                      <span>intent: {message.meta.intent_source}</span>
                    )}
                    {message.meta.response_source && (
                      <span>resposta: {message.meta.response_source}</span>
                    )}
                  </div>
                ) : null}
              </div>
            </article>
          ))}

          {loading && (
            <article className="message bot">
              <div className="message-bubble loading-bubble">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </article>
          )}

          <div ref={messagesEndRef} />
        </section>

        <form className="chat-form" onSubmit={sendMessage}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Escriu una consulta: Vull anar d'Inca a Palma..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            {loading ? "Cercant..." : "Enviar"}
          </button>
        </form>

        <footer className="debug-panel">
          <strong>Debug</strong>
          <span>
            conversa:{" "}
            {conversationId ? conversationId.slice(0, 8) + "..." : "nova"}
          </span>
          {lastDebug?.intent_source && (
            <span>intent: {lastDebug.intent_source}</span>
          )}
          {lastDebug?.response_source && (
            <span>resposta: {lastDebug.response_source}</span>
          )}
          {lastDebug?.error && <span className="debug-error">{lastDebug.error}</span>}
        </footer>
      </section>
    </main>
  );
}

export default App;