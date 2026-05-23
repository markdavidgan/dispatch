import { NextResponse } from "next/server";
import { revalidatePath } from "next/cache";

const API_URL = process.env.DISPATCH_API_URL || "http://localhost:10060";

export const dynamic = "force-dynamic";

export async function POST() {
  const clientId = process.env.CF_ACCESS_CLIENT_ID;
  const clientSecret = process.env.CF_ACCESS_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    return NextResponse.json({ error: "not configured" }, { status: 500 });
  }

  try {
    const res = await fetch(`${API_URL}/brief/refresh`, {
      method: "POST",
      headers: {
        "CF-Access-Client-Id": clientId,
        "CF-Access-Client-Secret": clientSecret,
      },
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: "collector refused" },
        { status: res.status }
      );
    }

    revalidatePath("/");
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 503 });
  }
}
