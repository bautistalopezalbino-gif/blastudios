import Editor from "@/components/Editor";

export default function Home() {
  return (
    <main>
      <header>
        <h1>Blastudios Editor</h1>
        <p>Sube un video vertical: recortamos los silencios y añadimos subtítulos animados.</p>
      </header>
      <Editor />
    </main>
  );
}
