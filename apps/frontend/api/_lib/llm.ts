import { z } from "zod";

interface LlmConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
}

function getPrimaryConfig(): LlmConfig {
  const provider = process.env.DISPATCH_AI_PROVIDER || "kimi";

  if (provider === "kimi" || process.env.KIMI_API_KEY) {
    return {
      baseUrl: "https://api.kimi.com/coding/v1",
      apiKey: process.env.KIMI_API_KEY!,
      model: "kimi-for-coding",
    };
  }

  if (provider === "groq") {
    return {
      baseUrl: "https://api.groq.com/openai/v1",
      apiKey: process.env.GROQ_API_KEY!,
      model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
    };
  }

  return {
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    apiKey: process.env.GEMINI_API_KEY!,
    model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
  };
}

function getFallbackConfig(): LlmConfig | null {
  const primary = process.env.DISPATCH_AI_PROVIDER || "kimi";

  // Kimi primary → fallback to Gemini, then Groq
  if ((primary === "kimi" || process.env.KIMI_API_KEY) && process.env.GEMINI_API_KEY) {
    return {
      baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
      apiKey: process.env.GEMINI_API_KEY,
      model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
    };
  }

  // Gemini primary → fallback to Groq
  if (primary === "gemini" && process.env.GROQ_API_KEY) {
    return {
      baseUrl: "https://api.groq.com/openai/v1",
      apiKey: process.env.GROQ_API_KEY,
      model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
    };
  }

  // Groq primary → fallback to Gemini
  if (primary === "groq" && process.env.GEMINI_API_KEY) {
    return {
      baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
      apiKey: process.env.GEMINI_API_KEY,
      model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
    };
  }

  return null;
}

export async function synthesize<T extends z.ZodType>(
  prompt: string,
  schema: T,
  config?: LlmConfig
): Promise<z.infer<T>> {
  const cfg = config || getPrimaryConfig();
  const fallback = getFallbackConfig();

  const systems = [cfg];
  if (fallback) systems.push(fallback);

  for (const sys of systems) {
    try {
      const response = await fetch(`${sys.baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${sys.apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: sys.model,
          messages: [{ role: "user", content: prompt }],
          response_format: { type: "json_object" },
          temperature: 0.7,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const content = data.choices[0].message.content;
      const parsed = JSON.parse(content);
      return schema.parse(parsed);
    } catch (e) {
      console.warn(`LLM ${sys.model} failed:`, e);
      continue;
    }
  }
  throw new Error("All LLM providers failed");
}
