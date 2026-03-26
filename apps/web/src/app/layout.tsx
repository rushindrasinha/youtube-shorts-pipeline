import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShortFactory — AI-Powered YouTube Shorts",
  description: "Turn any topic into a published YouTube Short in minutes. Fully automated: research, script, visuals, voiceover, captions, music, upload.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-[#09090b] font-sans text-zinc-50 antialiased">
        {children}
      </body>
    </html>
  );
}
