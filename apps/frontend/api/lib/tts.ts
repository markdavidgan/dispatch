export async function generateAudio(text: string): Promise<Buffer> {
  const token = process.env.HF_API_TOKEN;
  if (!token) throw new Error("HF_API_TOKEN required for Kokoro TTS");

  // Kokoro-82M via Hugging Face Inference API
  const response = await fetch(
    "https://api-inference.huggingface.co/models/hexgrad/Kokoro-82M",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ inputs: text }),
    }
  );

  if (!response.ok) {
    const err = await response.text().catch(() => "unknown");
    throw new Error(`Kokoro TTS failed: ${response.status} ${err}`);
  }

  return Buffer.from(await response.arrayBuffer());
}

export function estimateDuration(text: string): number {
  // Kokoro runs at ~150 wpm; ~12.5 chars/sec
  return Math.max(1, Math.round(text.length / 12.5));
}
