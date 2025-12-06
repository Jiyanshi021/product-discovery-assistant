// src/pages/ProductDetailPage.jsx
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchProductById } from "../api.js";

const ProductDetailPage = () => {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | success | error

  useEffect(() => {
    async function load() {
      try {
        setStatus("loading");
        const data = await fetchProductById(id);
        setProduct(data);
        setStatus("success");
      } catch (err) {
        console.error("Error loading product detail:", err);
        setStatus("error");
      }
    }
    load();
  }, [id]);

  if (status === "loading") {
    return (
      <main className="w-full max-w-5xl mx-auto px-6 sm:px-10 lg:px-20 py-10">
        <p className="text-sm text-text-muted-light">Loading product...</p>
      </main>
    );
  }

  if (status === "error" || !product) {
    return (
      <main className="w-full max-w-5xl mx-auto px-6 sm:px-10 lg:px-20 py-10">
        <p className="text-sm text-red-500 mb-4">
          Failed to load product details.
        </p>
        <Link
          to="/"
          className="text-sm text-accent underline underline-offset-2"
        >
          ← Back to curated looks
        </Link>
      </main>
    );
  }

  const {
    title,
    price,
    description,
    image_url,
    category,
    url,
    features,
  } = product;

  return (
    <main className="w-full max-w-5xl mx-auto px-6 sm:px-10 lg:px-20 py-10">
      {/* Back link */}
      <div className="mb-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-text-muted-light hover:text-accent"
        >
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          Back to curated looks
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:items-start">
        {/* Image */}
        <div className="rounded-2xl overflow-hidden bg-card-light shadow-sm">
          {image_url ? (
            <img
              src={image_url}
              alt={title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="aspect-[4/5] flex items-center justify-center text-text-muted-light text-sm">
              No image available
            </div>
          )}
        </div>

        {/* Details */}
        <div className="flex flex-col gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold text-text-light mb-2">
              {title}
            </h1>
            {category && (
              <p className="text-xs uppercase tracking-wide text-text-muted-light">
                {category}
              </p>
            )}
          </div>

          {price != null && (
            <p className="text-2xl font-semibold text-text-light">
              ₹{price}
            </p>
          )}

          {description && (
            <div className="mt-2">
              <h2 className="text-sm font-semibold mb-1">Description</h2>
              <p className="text-sm leading-relaxed text-text-muted-light">
                {description}
              </p>
            </div>
          )}

          {/* Features – show nicely even if dict */}
          {features && (
            <div className="mt-2">
              <h2 className="text-sm font-semibold mb-2">Features</h2>

              {Array.isArray(features) ? (
                <ul className="list-disc list-inside text-sm text-text-muted-light space-y-1">
                  {features.map((f, idx) => (
                    <li key={idx}>{f}</li>
                  ))}
                </ul>
              ) : (
                // if dict with product_features, fabric_features, function etc.
                <div className="space-y-3 text-sm text-text-muted-light">
                  {features.product_features && (
                    <div>
                      <p className="font-medium mb-1">Product features</p>
                      <ul className="list-disc list-inside space-y-1">
                        {features.product_features.map((f, idx) => (
                          <li key={idx}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {features.fabric_features && (
                    <div>
                      <p className="font-medium mb-1">Fabric features</p>
                      <ul className="list-disc list-inside space-y-1">
                        {features.fabric_features.map((f, idx) => (
                          <li key={idx}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {features.function && (
                    <div>
                      <p className="font-medium mb-1">Function</p>
                      <ul className="list-disc list-inside space-y-1">
                        {features.function.map((f, idx) => (
                          <li key={idx}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {url && (
            <div className="mt-4">
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center px-4 py-2 rounded-full bg-accent text-white text-sm font-medium hover:opacity-90 transition"
              >
                View on store
              </a>
            </div>
          )}
        </div>
      </div>
    </main>
  );
};

export default ProductDetailPage;
