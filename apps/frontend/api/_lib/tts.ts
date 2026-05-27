export async function generateAudio(text: string): Promise<Buffer> {
  const backendUrl = process.env.BACKEND_URL?.replace(/\/$/, "") || "https://dispatch-demo-api.marklab.uk";

  const response = await fetch(`${backendUrl}/api/tts/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const err = await response.text().catch(() => "unknown");
    throw new Error(`Backend TTS failed: ${response.status} ${err}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("audio/")) {
    const preview = await response.text().catch(() => "");
    throw new Error(
      `Backend TTS returned unexpected content-type "${contentType}" (expected audio/*). ` +
      `Preview: ${preview.slice(0, 200)}`
    );
  }

  const data = Buffer.from(await response.arrayBuffer());
  if (data.length === 0) {
    throw new Error("Backend TTS returned empty audio (0 bytes)");
  }

  return data;
}

export function estimateDuration(text: string): number {
  // Google Chirp 3 HD runs at ~150 wpm; ~12.5 chars/sec
  return Math.max(1, Math.round(text.length / 12.5));
}
