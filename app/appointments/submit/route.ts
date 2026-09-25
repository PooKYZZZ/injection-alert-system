import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { browserRedirect } from "@/lib/redirect";
import { validateAppointmentForm } from "../../../lib/validation";
import { generateReferenceNumber } from "../../../lib/reference-number";
import { checkEnforcementFromRuntime } from "../../../lib/enforcement-check-runtime";
import { enforcementRouteResponse } from "../../../lib/enforcement-boundary";
import { ingestAndEnforcePortalPost } from "../../../lib/portal-waf-ingest";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const enforcement = await checkEnforcementFromRuntime("APPOINTMENT_SUBMIT");
  const enforcementResponse = enforcementRouteResponse(enforcement);
  if (enforcementResponse) return enforcementResponse;

  try {
    const formData = await request.formData();
    const fullName = (formData.get("fullName") as string) || "";
    const email = (formData.get("email") as string) || "";
    const branch = (formData.get("branch") as string) || "";
    const serviceType = (formData.get("serviceType") as string) || "";
    const preferredDate = (formData.get("preferredDate") as string) || "";
    const notes = (formData.get("notes") as string) || "";

    const inspection = await ingestAndEnforcePortalPost({
      request,
      requestPath: "/appointments/submit",
      scope: "APPOINTMENT_SUBMIT",
      fields: { branch, serviceType, notes },
    });
    if (inspection) return inspection;

    // Server-side validation
    const validation = validateAppointmentForm({ fullName, email, branch, serviceType, preferredDate });
    if (!validation.isValid) {
      return NextResponse.json(
        { error: "Validation Failed", details: validation.errors },
        { status: 400 }
      );
    }

    const generatedRef = generateReferenceNumber("APT");

    await prisma.appointment.create({
      data: {
        referenceNo: generatedRef,
        fullName,
        email,
        branch,
        serviceType,
        preferredDate,
        notes,
        status: "CONFIRMED",
      },
    });

    return browserRedirect(request, `/success?type=appointment&ref=${encodeURIComponent(generatedRef)}`);
  } catch (error) {
    return NextResponse.json({ error: "Failed to parse form data" }, { status: 400 });
  }
}
