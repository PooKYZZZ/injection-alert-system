import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { browserRedirect } from "@/lib/redirect";
import { z } from "zod";
import { generateReferenceNumber } from "@/lib/reference-number";

const formSchema = z.object({
  fullName: z.string().min(2, "Full legal name is required"),
  email: z.string().email("A valid contact email is required"),
  purpose: z.string().min(1, "Intended purpose must be specified"),
  deliveryOption: z.string().min(1, "Please choose a delivery option"),
  remarks: z.string().optional(),
});

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ recordNo: string }> }
) {
  try {
    const { recordNo } = await params;

    // Verify record exists first
    const record = await prisma.record.findUnique({
      where: { recordNo },
    });

    if (!record) {
      return new NextResponse("Registry file record not found", { status: 404 });
    }

    // Parse URL-encoded body (the traditional HTML form content-type)
    const formData = await req.formData();
    const data = {
      fullName: formData.get("fullName") as string,
      email: formData.get("email") as string,
      purpose: formData.get("purpose") as string,
      deliveryOption: formData.get("deliveryOption") as string,
      remarks: (formData.get("remarks") as string) || "",
    };

    // Zod validation
    const parsed = formSchema.safeParse(data);
    if (!parsed.success) {
      return NextResponse.json({ error: "Invalid input" }, { status: 400 });
    }

    const referenceNo = generateReferenceNumber("TXN");

    // Persist as a Transaction in our local database
    await prisma.transaction.create({
      data: {
        referenceNo,
        recordNo,
        serviceType: "Certified Copy Request",
        applicantName: parsed.data.fullName,
        email: parsed.data.email,
        purpose: parsed.data.purpose,
        deliveryOption: parsed.data.deliveryOption,
        remarks: parsed.data.remarks,
        status: "Processing",
      },
    });

    return browserRedirect(
      req,
      `/transactions/status?ref=${encodeURIComponent(referenceNo)}&success=copy`
    );
  } catch (error: any) {
    console.error("Error handling certified copy request:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}
