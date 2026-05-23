import type { Metadata } from "next";
import { Inter_Tight, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import Nav from "@/components/Nav";
import "./globals.css";

const interTight = Inter_Tight({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-inter-tight",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Dispatch",
  description: "Daily editorial brief for your projects.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${interTight.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen">
        <header className="border-b border-ink sticky top-0 bg-paper z-20">
          <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-4 flex items-center justify-between gap-6">
            <Link href="/" className="font-disp font-extrabold text-lg tracking-tight flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-signal" style={{ animation: "on-air 3.6s ease-in-out infinite" }} aria-hidden title="Dispatch is on the air" />
              DISPATCH
            </Link>
            <Nav />
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
