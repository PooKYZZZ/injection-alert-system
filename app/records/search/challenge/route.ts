import { NextResponse } from "next/server";
import { z } from "zod";
import { verifyRecordSearchEnforcementChallengeFromRuntime } from "../../../../lib/enforcement-check-runtime";

const bodySchema = z.object({
  token: z.string().min(1).max(2048),
});

export async function POST(request: Request) {
  try {
    const parsed = bodySchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        { verified: false, status: "INVALID" },
        { status: 400 },
      );
    }
    const result = await verifyRecordSearchEnforcementChallengeFromRuntime(
      parsed.data.token,
    );
    return NextResponse.json(result, { status: 200 });
  } catch {
    return NextResponse.json(
      { verified: false, status: "UNAVAILABLE" },
      { status: 503 },
    );
  }
}
