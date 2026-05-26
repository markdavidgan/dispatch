import { createHash, randomBytes } from "crypto";

const MASTER_KEY = process.env.DISPATCH_MASTER_KEY;
if (!MASTER_KEY) throw new Error("DISPATCH_MASTER_KEY required");

const KEY = new Uint8Array(createHash("sha256").update(MASTER_KEY).digest());

function bufToU8(buf: Buffer): Uint8Array {
  return new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
}

export async function encrypt(plaintext: string): Promise<string> {
  const iv = randomBytes(12);
  const encoder = new TextEncoder();
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    KEY,
    { name: "AES-GCM" },
    false,
    ["encrypt"]
  );
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: bufToU8(iv) },
    cryptoKey,
    encoder.encode(plaintext)
  );
  const combined = Buffer.concat([iv, Buffer.from(ciphertext)]);
  return combined.toString("base64");
}

export async function decrypt(b64: string): Promise<string> {
  const combined = Buffer.from(b64, "base64");
  const iv = bufToU8(combined.subarray(0, 12));
  const ciphertext = bufToU8(combined.subarray(12));
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    KEY,
    { name: "AES-GCM" },
    false,
    ["decrypt"]
  );
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    cryptoKey,
    ciphertext
  );
  return new TextDecoder().decode(plaintext);
}
