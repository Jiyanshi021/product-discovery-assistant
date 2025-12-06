// // src/App.jsx
// import React from "react";
// import { Routes, Route } from "react-router-dom";

// import Header from "./components/Header.jsx";
// import HomePage from "./pages/HomePage.jsx";
// import ChatPage from "./pages/ChatPage.jsx";
// import ProductDetailPage from "./pages/ProductDetailPage.jsx";

// function App() {
//   return (
//     <div className="min-h-screen bg-background-light text-text-light">
//       {/* Sticky header on all pages */}
//       <Header />

//       {/* Page content */}
//       <Routes>
//         <Route path="/" element={<HomePage />} />
//         <Route path="/chat" element={<ChatPage />} />
//         <Route path="/products/:id" element={<ProductDetailPage />} />
//       </Routes>
//     </div>
//   );
// }

// export default App;



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
        <nav className="flex items-center justify-between px-6 sm:px-10 lg:px-20 py-4 bg-background-light">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-accent">auto_awesome</span>
            <span className="font-serif font-semibold text-lg tracking-wide">
              StyleMatch AI
            </span>
          </div>

          {/* Center nav links */}
          <div className="hidden md:flex items-center gap-8 text-sm">
            <Link
              to="/"
              className="hover:text-accent transition-colors"
            >
              Home
            </Link>
            <Link
              to="/chat"
              className="hover:text-accent transition-colors"
            >
              Chat
            </Link>
            <button
              type="button"
              className="hover:text-accent transition-colors"
            >
              Men
            </button>
            <button
              type="button"
              className="hover:text-accent transition-colors"
            >
              Women
            </button>
            <button
              type="button"
              className="hover:text-accent transition-colors"
            >
              Accessories
            </button>
          </div>

          {/* Icons */}
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-full hover:bg-black/5">
              <span className="material-symbols-outlined text-lg">search</span>
            </button>
            <button className="p-2 rounded-full hover:bg-black/5">
              <span className="material-symbols-outlined text-lg">person</span>
            </button>
          </div>
        </nav>

        {/* Routed pages */}
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          {/* NEW: product detail route */}
          <Route path="/products/:id" element={<ProductDetailPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
