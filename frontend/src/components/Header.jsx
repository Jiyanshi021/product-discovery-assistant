// src/components/Header.jsx  (ya Navbar.jsx – jo bhi tum use kar rahe ho)
import React from "react";
import { Link, NavLink } from "react-router-dom";

const Header = () => {
  return (
    <header className="w-full bg-[#fff9e7] border-b border-[#efe3c2]">
      <nav className="max-w-7xl mx-auto flex items-center justify-between px-8 py-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <span className="text-2xl text-yellow-500">✨</span>
          <span className="font-serif text-xl font-semibold tracking-tight text-slate-900">
            HunnitAI
          </span>
        </Link>

        {/* Center nav – only Home & Chat */}
        <div className="flex items-center gap-10 text-sm font-medium text-slate-800">
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive ? "text-slate-900 font-semibold" : "hover:text-slate-900"
            }
          >
            Home
          </NavLink>
          <NavLink
            to="/chat"
            className={({ isActive }) =>
              isActive ? "text-slate-900 font-semibold" : "hover:text-slate-900"
            }
          >
            Chat
          </NavLink>
        </div>

        {/* Right icons – same as pehle */}
        <div className="flex items-center gap-4 text-slate-700">
          <button className="hover:text-slate-900">
            <span className="material-symbols-outlined text-xl">search</span>
          </button>
          <button className="hover:text-slate-900">
            <span className="material-symbols-outlined text-xl">person</span>
          </button>
        </div>
      </nav>
    </header>
  );
};

export default Header;
