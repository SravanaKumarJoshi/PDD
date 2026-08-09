import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import Navigation from "@/components/Navigation";
import ProtectedRoute from "@/components/ProtectedRoute";

export const metadata: Metadata = {
  title: "BioPolymer AI Screening Platform",
  description: "AI-Powered Decision Support for Biomedical Packaging Material Selection with XGBoost, FAISS, NSGA-II & SHAP",
  keywords: ["biopolymer", "biomedical packaging", "AI material selection", "polysaccharides", "XGBoost", "NSGA-II"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-gray-100 min-h-screen flex flex-col antialiased">
        <AuthProvider>
          <Navigation />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <ProtectedRoute>
              {children}
            </ProtectedRoute>
          </main>
          <footer className="border-t border-gray-800/80 bg-gray-950/60 py-6 mt-12">
            <div className="max-w-7xl mx-auto px-4 text-center text-xs text-gray-500">
              <p className="font-semibold text-gray-400">BioPolymer AI Screening Platform v2.0</p>
              <p className="mt-1">XGBoost • FAISS • NSGA-II • SHAP • Next.js 14 • JWT Auth • MySQL</p>
              <p className="mt-2 text-[11px] text-gray-600">
                ⚕️ For biomedical research & decision support. Experimental validation required before clinical use.
              </p>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
