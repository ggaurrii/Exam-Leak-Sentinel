import type { Metadata } from "next";
import { Newsreader, IBM_Plex_Sans } from "next/font/google";
import { Header } from "@/components/Header";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-newsreader",
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Exam Leak Sentinel",
  description: "Real-time detection and review of leaked exam content.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${newsreader.variable} ${plexSans.variable}`}>
      <body>
        <Header />
        {children}
      </body>
    </html>
  );
}
