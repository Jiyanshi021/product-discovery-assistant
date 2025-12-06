
// src/App.jsx
import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ChatPage from "./pages/ChatPage";
import ProductDetailPage from "./pages/ProductDetailPage.jsx";

function App() {
  return (
    <div className="min-h-screen bg-background-light text-text-light">
      <div className="smai-page mx-auto">
        {/* Header nav */}
        <nav className="flex items-center justify-between px-6 sm:px-10 lg:px-20 py-4 bg-background-light border-b border-black/5">
          {/* Logo (left) */}
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-accent">
              auto_awesome
            </span>
            <span className="font-serif font-semibold text-lg md:text-xl tracking-wide">
              HunnitAssistance AI
            </span>
          </div>

          {/* Center nav links: Home + Chat only */}
          <div className="flex-1 flex justify-center">
            <div className="inline-flex items-center gap-4 md:gap-6">
              <Link
                to="/"
                className="px-4 md:px-5 py-1.5 md:py-2 rounded-full text-sm md:text-base font-medium hover:bg-accent/10 hover:text-accent transition-colors"
              >
                Home
              </Link>
              <Link
                to="/chat"
                className="px-4 md:px-5 py-1.5 md:py-2 rounded-full text-sm md:text-base font-medium hover:bg-accent/10 hover:text-accent transition-colors"
              >
                Chat
              </Link>
            </div>
          </div>

          {/* Right spacer for balance */}
          <div className="w-8 sm:w-12" />
        </nav>

        {/* Routed pages */}
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          {/* product detail route */}
          <Route path="/products/:id" element={<ProductDetailPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
