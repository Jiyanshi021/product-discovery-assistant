// src/pages/HomePage.jsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ProductCard from "../components/ProductCard.jsx";


// NEW
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
 // FastAPI base

const HomePage = () => {
  const [products, setProducts] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | success | error

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setStatus("loading");

        const res = await fetch(`${API_BASE_URL}/products/`);

        if (!res.ok) {
          const text = await res.text();
          console.error("❌ /products failed:", res.status, res.statusText);
          console.error("Response body:", text);
          throw new Error(`Failed to fetch products: ${res.status}`);
        }

        const data = await res.json();
        const list = Array.isArray(data) ? data : data.items ?? [];

        console.log("✅ Products from backend:", list);
        setProducts(list);
        setStatus("success");
      } catch (err) {
        console.error("🚨 Error while fetching products from backend:", err);
        setStatus("error");
        setProducts([]);
      }
    };

    fetchProducts();
  }, []);

  return (
    <>
      <main className="w-full max-w-7xl mx-auto px-6 sm:px-10 lg:px-20 py-10">
        {/* Hero */}
        <div className="flex flex-col items-center justify-center text-center my-8 md:my-16">
          <h1 className="font-serif text-4xl md:text-5xl font-bold mb-4 text-text-light">
            Find Your Signature Style
          </h1>
          <p className="text-text-muted-light max-w-xl mb-4 md:mb-6">
            Discover outfits from Hunnit, tailored to your vibe,
            occasions, and comfort.
          </p>
        </div>

        {/* Products Grid */}
        <div className="mt-8 md:mt-12">
          {status === "loading" && (
            <p className="text-center text-sm text-text-muted-light">
              Loading curated looks from backend...
            </p>
          )}

          {status === "error" && (
            <p className="text-center text-xs text-red-500 mb-4">
              Some issue in loading products from backend
            </p>
          )}

          {status === "success" && products.length === 0 && (
            <p className="text-center text-sm text-text-muted-light">
              No products found in backend.
            </p>
          )}

          {products.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-8">
              {products.map((p) => (
                <ProductCard key={p.id || p.title} product={p} />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Floating Chat CTA: tooltip + bubble */}
      <div className="fixed bottom-6 right-6 md:bottom-8 md:right-8 flex flex-col items-end gap-2">
        {/* Small box above bubble */}
        <div className="rounded-2xl bg-card-light/90 border border-accent/40 shadow-md px-4 py-2 text-xs sm:text-sm text-text-light max-w-[220px]">
          Get outfit suggestions with AI
        </div>

        {/* Chat Bubble → /chat */}
        <Link
          to="/chat"
          className="inline-flex items-center justify-center rounded-full shadow-lg bg-accent text-white w-14 h-14 md:w-16 md:h-16 hover:scale-105 transition-transform"
          aria-label="Open AI chat"
        >
          <span className="text-2xl md:text-3xl">💬</span>
        </Link>
      </div>
    </>
  );
};

export default HomePage;
