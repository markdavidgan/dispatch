export async function generateAudio(text: string): Promise<Buffer> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY is required for TTS");
  }

  const model = process.env.OPENAI_TTS_MODEL || "tts-1";
  const voice = process.env.OPENAI_TTS_VOICE || "alloy";

  const response = await fetch("https://api.openai.com/v1/audio/speech", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      voice,
      input: text,
      response_format: "mp3",
    }),
  });

  if (!response.ok) {
    const err = await response.text().catch(() => "unknown");
    throw new Error(`OpenAI TTS failed: ${response.status} ${err}`);
  }

  const data = Buffer.from(await response.arrayBuffer());
  if (data.length === 0) {
    throw new Error("OpenAI TTS returned empty audio (0 bytes)");
  }

  return data;
}

export function estimateDuration(text: string): number {
  // OpenAI TTS runs at roughly 150 wpm; ~12.5 chars/sec
  return Math.max(1, Math.round(text.length / 12.5));
}
