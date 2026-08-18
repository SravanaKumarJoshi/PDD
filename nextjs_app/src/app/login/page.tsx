'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Dna, Lock, Mail, User as UserIcon, ArrowRight, ShieldCheck, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { login, register, isAuthenticated } = useAuth();

  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // If already authenticated, redirect to home
  React.useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegisterMode) {
        await register(email, password, displayName);
      } else {
        await login(email, password);
      }
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = () => {
    setEmail('researcher@biopolymer.ai');
    setPassword('SecurePass123!');
    setDisplayName('Dr. Alex Morgan');
  };

  return (
    <div className="min-h-[75vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-[#111827] rounded-2xl p-8 border border-[#1f293d] shadow-sm relative overflow-hidden animate-fade-in">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 mb-1">
            <Dna className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            {isRegisterMode ? 'Create Platform Account' : 'Sign In'}
          </h2>
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            {isRegisterMode
              ? 'Register with JWT Authentication to access saved screening runs'
              : 'Enter your credentials to access the BioPolymer AI Platform'}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex bg-[#0d1322] rounded-lg p-1 mt-6 border border-[#222d44]">
          <button
            type="button"
            onClick={() => { setIsRegisterMode(false); setError(null); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-md transition-colors ${
              !isRegisterMode
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsRegisterMode(true); setError(null); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-md transition-colors ${
              isRegisterMode
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {isRegisterMode && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  placeholder="Dr. Alex Morgan"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg pl-9 pr-3.5 py-2 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                placeholder="researcher@biopolymer.ai"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg pl-9 pr-3.5 py-2 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg pl-9 pr-3.5 py-2 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary flex items-center justify-center gap-2 py-2.5 mt-2 text-xs font-semibold rounded-lg shadow-sm"
          >
            {loading ? (
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <span>{isRegisterMode ? 'Create Account' : 'Sign In'}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 text-blue-400 font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>JWT Secured</span>
          </div>
          <button
            type="button"
            onClick={handleDemoFill}
            className="text-slate-400 hover:text-blue-400 hover:underline transition-colors font-medium"
          >
            Auto-fill Demo
          </button>
        </div>
      </div>
    </div>
  );
}


