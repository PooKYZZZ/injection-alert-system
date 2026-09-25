import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { browserRedirect } from "@/lib/redirect";
import { validateSupportForm } from "../../../lib/validation";
import { generateReferenceNumber } from "../../../lib/reference-number";
import { checkEnforcementFromRuntime } from "../../../lib/enforcement-check-runtime";
import { enforcementRouteResponse } from "../../../lib/enforcement-boundary";
import { ingestAndEnforcePortalPost } from "../../../lib/portal-waf-ingest";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const enforcement = await checkEnforcementFromRuntime("SUPPORT_SUBMIT");
  const enforcementResponse = enforcementRouteResponse(enforcement);
  if (enforcementResponse) return enforcementResponse;

  try {
    const formData = await request.formData();
    const subject = (formData.get("subject") as string) || "";
    const category = (formData.get("category") as string) || "";
    const email = (formData.get("email") as string) || "";
    const referenceNo = (formData.get("referenceNo") as string) || "";
    const message = (formData.get("message") as string) || "";

    const inspection = await ingestAndEnforcePortalPost({
      request,
      requestPath: "/support/submit",
      scope: "SUPPORT_SUBMIT",
      fields: { subject, category, message },
    });
    if (inspection) return inspection;

    // Server-side validation
    const validation = validateSupportForm({ email, category, subject, message });
    if (!validation.isValid) {
      return NextResponse.json(
        { error: "Validation Failed", details: validation.errors },
        { status: 400 }
      );
    }

    const generatedRef = generateReferenceNumber("SUP");

    await prisma.supportTicket.create({
      data: {
        subject,
        category,
        email,
        referenceNo: generatedRef,
        message,
        status: "PENDING_REVIEW",
      },
    });

    return browserRedirect(request, `/success?type=support&ref=${encodeURIComponent(generatedRef)}`);
  } catch (error) {
    return NextResponse.json({ error: "Failed to parse form data" }, { status: 400 });
  }
}
