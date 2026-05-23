import { NextResponse } from "next/server";
import { fetchLive } from "@/lib/live";

export const dynamic = "force-dynamic";

export async function GET() {
  const data = await fetchLive();
  if (!data) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
  return NextResponse.json(data);
}
