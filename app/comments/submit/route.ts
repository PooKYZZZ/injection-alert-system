import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { browserRedirect } from "@/lib/redirect";
import { z } from "zod";
import { checkEnforcementFromRuntime } from "../../../lib/enforcement-check-runtime";
import { enforcementRouteResponse } from "../../../lib/enforcement-boundary";
import { ingestAndEnforcePortalPost } from "../../../lib/portal-waf-ingest";

const commentSchema = z.object({
  displayName: z.string().trim().min(2).max(80),
  message: z.string().trim().min(5).max(1000),
});

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const enforcement = await checkEnforcementFromRuntime("COMMENTS_SUBMIT");
  const enforcementResponse = enforcementRouteResponse(enforcement);
  if (enforcementResponse) return enforcementResponse;

  try {
    const formData = await request.formData();
    const data = {
      displayName: formData.get("displayName") as string,
      message: formData.get("message") as string,
    };

    const inspection = await ingestAndEnforcePortalPost({
      request,
      requestPath: "/comments/submit",
      scope: "COMMENTS_SUBMIT",
      fields: { message: data.message || "" },
    });
    if (inspection) return inspection;

    const parsed = commentSchema.safeParse(data);
    if (!parsed.success) {
      return NextResponse.json({ error: "Invalid input" }, { status: 400 });
    }

    await prisma.comment.create({
      data: {
        displayName: parsed.data.displayName,
        message: parsed.data.message,
      },
    });

    return browserRedirect(request, "/comments?posted=1");
  } catch (error) {
    console.error("Error handling comment submission:", error);
    return NextResponse.json({ error: "Failed to submit comment" }, { status: 500 });
  }
}
