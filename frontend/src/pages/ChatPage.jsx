// src/pages/ChatPage.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { searchProducts } from "../api.js";
import ProductCard from "../components/ProductCard.jsx";

const ChatPage = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: "bot",
      text:
        "Hi! Ask me for outfits, like **“show me oversized hoodies under 2000”**.",
      products: [],
      primaryProductId: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  // ---------- auto-scroll to newest message ----------
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ---------- helpers for safe text + simple markdown ----------

  const toSafeText = (value) => {
    if (typeof value === "string") return value;
    if (value === null || value === undefined) return "";
    if (Array.isArray(value)) return value.join(" ");
    try {
      return String(value);
    } catch {
      return "";
    }
  };

  // convert "This is **bold** text" into React nodes with <strong>
  const renderInlineBold = (text) => {
    const parts = text.split("**");
    return parts.map((part, idx) => {
      const isBold = idx % 2 === 1;
      if (!part) return null;
      return isBold ? (
        <strong key={idx}>{part}</strong>
      ) : (
        <span key={idx}>{part}</span>
      );
    });
  };

  // split into paragraphs on blank lines, keep spacing
  const renderBotText = (raw) => {
    const safe = toSafeText(raw);
    if (!safe) return null;

    const paragraphs = safe.split(/\n{2,}/); // 2+ newlines = new paragraph

    return paragraphs.map((para, idx) => (
      <p key={idx} className={idx > 0 ? "mt-2" : ""}>
        {renderInlineBold(para)}
      </p>
    ));
  };

  // ---------- order products based on how they appear in answer text ----------

  const orderProductsByAnswerText = (products, answerText) => {
    const text = (answerText || "").toLowerCase();

    return products.slice().sort((a, b) => {
      const titleA = (a.title || "").toLowerCase();
      const titleB = (b.title || "").toLowerCase();

      const idxA = text.indexOf(titleA);
      const idxB = text.indexOf(titleB);

      const safeIdxA = idxA === -1 ? Number.MAX_SAFE_INTEGER : idxA;
      const safeIdxB = idxB === -1 ? Number.MAX_SAFE_INTEGER : idxB;

      if (safeIdxA !== safeIdxB) {
        return safeIdxA - safeIdxB; // jo pehle text me aaya, uska card pehle
      }

      // tie-breaker: rank agar ho, warna id
      const ra = a.rank ?? 9999;
      const rb = b.rank ?? 9999;
      if (ra !== rb) return ra - rb;

      const idA = a.product_id ?? a.id ?? 0;
      const idB = b.product_id ?? b.id ?? 0;
      return idA - idB;
    });
  };

  // ----------------------- send handler ------------------------

  async function handleSend(e) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const now = Date.now();

    const userMessage = {
      id: now,
      sender: "user",
      text: trimmed,
      products: [],
      primaryProductId: null,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await searchProducts(trimmed, 5);

      const rawResults = Array.isArray(res.results) ? res.results : [];
      const answerText =
        res.answer ||
        "I couldn't find anything specific, but here are some options.";

      // 👉 Pehle answer text decide karo, fir uske hisaab se product order
      const orderedResults = orderProductsByAnswerText(rawResults, answerText);

      const botMessage = {
        id: now + 1,
        sender: "bot",
        text: answerText,
        products: orderedResults,
        primaryProductId:
          res.primary_product_id || (orderedResults[0]?.id ?? null),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error(err);
      const errorMessage = {
        id: now + 2,
        sender: "bot",
        text: "Something went wrong while searching. Please try again.",
        products: [],
        primaryProductId: null,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  // -------------------------- UI -------------------------------

  return (
    <main className="w-full px-4 sm:px-8 lg:px-20 py-8 min-h-[calc(100vh-4rem)]">
      <div className="max-w-5xl mx-auto">
        {/* Back button */}
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium text-accent hover:bg-accent/10 transition-colors"
        >
          <span className="material-symbols-outlined text-xl">
            arrow_back
          </span>
          <span>Back</span>
        </button>

        {/* Heading */}
        <h1 className="mt-4 font-serif text-3xl md:text-4xl font-bold text-text-light text-center">
          Chat with your AI Stylist
        </h1>
        <p className="mt-1 text-center text-xs sm:text-sm text-text-muted-light">
          Tell me your vibe, budget or occasion and I’ll suggest outfits from Hunnit.
        </p>

        {/* Chat container */}
        <div className="mt-8 flex flex-col bg-card-light/70 rounded-3xl shadow-lg p-4 sm:p-6 md:p-8 h-[68vh] sm:h-[74vh] md:h-[78vh] border border-accent/10">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-1 md:pr-2">
            {messages.map((m) => {
              const safeText = toSafeText(m.text);

              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${
                    m.sender === "user" ? "items-end" : "items-start"
                  }`}
                >
                  {/* Bubble */}
                  <div
                    className={`max-w-[90%] sm:max-w-[75%] rounded-2xl px-4 py-2 leading-relaxed ${
                      m.sender === "user"
                        ? "bg-accent text-white text-sm"
                        : "bg-card-light text-text-light text-sm"
                    }`}
                  >
                    {m.sender === "bot" ? renderBotText(safeText) : safeText}
                  </div>

                  {/* Product cards for this assistant message */}
                  {m.sender === "bot" &&
                    m.products &&
                    m.products.length > 0 && (
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
                        {m.products.map((p) => {
                          const id = p.product_id || p.id;

                          return (
                            <div key={id} className="animate-fadeIn">
                              <ProductCard
                                product={{
                                  id,
                                  title: p.title,
                                  brand: p.brand,
                                  price: p.price,
                                  image_url: p.image_url,
                                }}
                                isPrimary={
                                  m.primaryProductId
                                    ? id === m.primaryProductId
                                    : false
                                }
                              />
                            </div>
                          );
                        })}
                      </div>
                    )}
                </div>
              );
            })}

            {loading && (
              <div className="flex justify-start">
                <div className="max-w-[70%] rounded-2xl px-4 py-2 text-sm bg-card-light text-text-muted-light animate-pulse">
                  Typing…
                </div>
              </div>
            )}

            {/* auto-scroll anchor */}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form
            onSubmit={handleSend}
            className="mt-4 flex items-center gap-2 sm:gap-3 border-t border-text-light/10 pt-3"
          >
            <input
              type="text"
              className="flex-1 rounded-full bg-background-light border border-text-light/20 px-3 sm:px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
              placeholder="Describe what you want to wear..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-full px-5 sm:px-6 py-2 text-sm font-medium bg-accent text-white hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                "Send"
              )}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
};

export default ChatPage;
