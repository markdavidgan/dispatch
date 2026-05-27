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

  return Buffer.from(await response.arrayBuffer());
}

export function estimateDuration(text: string): number {
  // Google Chirp 3 HD runs at ~150 wpm; ~12.5 chars/sec
  return Math.max(1, Math.round(text.length / 12.5));
}
