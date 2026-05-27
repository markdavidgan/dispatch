import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";

const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID;
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID;
const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY;
const R2_BUCKET = process.env.R2_BUCKET;

function getClient(): S3Client {
  return new S3Client({
    region: "auto",
    endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: R2_ACCESS_KEY_ID!,
      secretAccessKey: R2_SECRET_ACCESS_KEY!,
    },
  });
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const key = req.query.key as string;
  const fullKey = `dispatch/audio/${key}.wav`;

  const base = process.env.R2_PUBLIC_BASE_URL?.replace(/\/$/, "") || "";
  if (base) {
    return res.redirect(302, `${base}/${fullKey}`);
  }

  const client = getClient();
  const url = await getSignedUrl(
    client,
    new GetObjectCommand({ Bucket: R2_BUCKET, Key: fullKey }),
    { expiresIn: 3600 }
  );
  res.redirect(302, url);
}
