// src/components/ProductCard.jsx
import React from "react";
import { Link } from "react-router-dom";

const ProductCard = ({ product }) => {
  const { id, title, brand, price, image_url } = product;

  return (
    <Link
      to={`/products/${id}`}
      className="group block h-full"
    >
      <div className="flex flex-col rounded-2xl bg-card-light dark:bg-card-dark shadow-sm overflow-hidden h-full">
        <div className="relative">
          <div
            className="bg-cover bg-center aspect-[4/5] transition-transform duration-300 group-hover:scale-105"
            style={{ backgroundImage: `url('${image_url}')` }}
          />
        </div>
        <div className="p-4 flex flex-col flex-grow">
          <h3 className="font-serif text-lg font-bold leading-tight text-text-light dark:text-text-dark">
            {title}
          </h3>
          {brand && (
            <p className="text-sm text-text-muted-light dark:text-text-muted-dark mt-1">
              {brand}
            </p>
          )}
          {price != null && (
            <p className="text-base font-bold text-text-light dark:text-text-dark mt-auto pt-2">
              ₹{price}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
};

export default ProductCard;
