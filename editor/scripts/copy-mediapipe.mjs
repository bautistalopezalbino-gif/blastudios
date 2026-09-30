// Copia los binarios WASM de MediaPipe a public/ para servirlos desde la propia app.
import { cpSync } from "node:fs";

cpSync("node_modules/@mediapipe/tasks-vision/wasm", "public/mediapipe/wasm", { recursive: true });
