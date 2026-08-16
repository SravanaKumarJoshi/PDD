'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  Dna,
  Search,
  Database,
  BrainCircuit,
  Microscope,
  Target,
  FolderKanban,
  LogIn,
  LogOut,
  User as UserIcon,
} from 'lucide-react';

export default function Navigation() {
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuth();

  const navItems = [
    { label: 'Overview', href: '/', icon: Dna, public: true },
    { label: 'Recommend', href: '/recommend', icon: Search, public: false },
    { label: 'Dataset Browser', href: '/dataset', icon: Database, public: false },
    { label: 'Model Training', href: '/training', icon: BrainCircuit, public: false },
    { label: 'Explainability', href: '/explainability', icon: Microscope, public: false },
    { label: 'Optimization', href: '/optimization', icon: Target, public: false },
    { label: 'Projects', href: '/projects', icon: FolderKanban, public: false },
  ];

  const visibleNavItems = navItems.filter((item) => item.public || isAuthenticated);

  return (
    <nav className="glass-panel sticky top-0 z-50 border-b border-gray-800 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-transform">
              <Dna className="w-6 h-6 text-gray-950 font-bold" />
            </div>
            <div>
              <span className="font-bold text-lg text-white tracking-wide">BioPolymer <span className="gradient-text-emerald">AI</span></span>
              <span className="block text-[10px] text-emerald-400 font-medium tracking-wider uppercase">Screening Platform</span>
            </div>
          </Link>

          {/* Nav Links */}
          <div className="hidden lg:flex items-center space-x-1">
            {visibleNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                      : 'text-gray-300 hover:text-white hover:bg-gray-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-gray-400'}`} />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* User Auth Widget */}
          <div className="flex items-center gap-3">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-3 bg-gray-900/80 border border-gray-800 rounded-lg px-3 py-1.5">
                <div className="w-7 h-7 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30 text-xs font-bold">
                  {user.display_name ? user.display_name[0].toUpperCase() : user.email[0].toUpperCase()}
                </div>
                <div className="hidden sm:block text-left">
                  <span className="block text-xs font-medium text-gray-200">{user.display_name || user.email.split('@')[0]}</span>
                  <span className="block text-[10px] text-gray-400">{user.role}</span>
                </div>
                <button
                  onClick={logout}
                  title="Logout"
                  className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="flex items-center gap-2 btn-primary text-xs"
              >
                <LogIn className="w-4 h-4" />
                <span>Login / Register</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
