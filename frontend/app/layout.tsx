import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OpsCore | Freelance Assistant",
  description: "Your AI-powered freelance operating system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col pt-16">
        {/* We add pt-16 here later to account for a fixed Nav, or we do it inline */}
        {children}
      </body>
    </html>
  );
}
