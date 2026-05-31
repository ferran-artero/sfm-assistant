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

      const botMessage = {
        role: "bot",
        content: data.response,
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
    } finally {
      setLoading(false);
    }
  };

  const resetConversation = () => {
    localStorage.removeItem(STORAGE_KEY);
    setConversationId(null);
    setMessages(initialMessages);
    setInput("");
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

        <footer className="demo-notice">
          Demo local no oficial. Aquesta aplicació no està vinculada a SFM i la informació pot no coincidir amb els horaris oficials.
        </footer>
      </section>
    </main>
  );
}

export default App;