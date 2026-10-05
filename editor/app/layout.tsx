import type { Metadata } from "next";
import "@fontsource/anton/latin-400.css";
import "@fontsource/bangers/latin-400.css";
import "@fontsource/montserrat/latin-900.css";
import "@fontsource/playfair-display/latin-700-italic.css";
import "@fontsource/poppins/latin-600.css";
import "@fontsource/poppins/latin-800.css";
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
