import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blastudios Editor",
  description: "Editor automático de videos verticales con subtítulos y recorte de silencios.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
