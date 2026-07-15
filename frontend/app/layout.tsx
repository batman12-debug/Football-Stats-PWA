import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import localFont from "next/font/local";

import { PinProvider } from "@/components/pin/PinContext";
import { PinQueueSheet } from "@/components/pin/PinQueueSheet";
import { PinSessionProvider } from "@/components/pin/PinSessionProvider";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const gondens = localFont({
  src: "./fonts/Gondens-DEMO.otf",
  variable: "--font-display",
  display: "swap",
  weight: "400",
});

export const metadata: Metadata = {
  title: "CheckBoard World Cup 2026 Predictions",
  description: "AI powered match predictions for FIFA World Cup 2026",
  icons: {
    icon: [
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${gondens.variable} bg-black`}>
      <body className="min-h-screen bg-black font-sans text-base text-white antialiased">
        <PinProvider>
          <PinSessionProvider>
            <SiteHeader />
            {children}
            <PinQueueSheet />
          </PinSessionProvider>
        </PinProvider>
      </body>
    </html>
  );
}
