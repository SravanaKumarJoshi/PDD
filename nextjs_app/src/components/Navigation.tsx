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
    <nav className="bg-[#0d1322] sticky top-0 z-50 border-b border-[#1f293d]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold">
              <Dna className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base text-white tracking-tight">BioPolymer <span className="text-blue-400">AI</span></span>
              <span className="block text-[10px] text-slate-400 font-medium tracking-wider uppercase">Screening Platform</span>
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
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* User Auth Widget */}
          <div className="flex items-center gap-3">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-3 bg-[#151c2c] border border-[#222d44] rounded-lg px-3 py-1.5">
                <div className="w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold border border-blue-500/30">
                  {user.display_name ? user.display_name[0].toUpperCase() : user.email[0].toUpperCase()}
                </div>
                <div className="hidden sm:block text-left">
                  <span className="block text-xs font-semibold text-slate-200">{user.display_name || user.email.split('@')[0]}</span>
                  <span className="block text-[10px] text-slate-400 font-medium uppercase">{user.role}</span>
                </div>
                <button
                  onClick={logout}
                  title="Logout"
                  className="p-1 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="flex items-center gap-2 btn-primary text-xs"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In / Register</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}


