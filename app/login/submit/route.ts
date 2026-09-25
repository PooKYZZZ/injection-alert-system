import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { browserRedirect } from '@/lib/redirect';
import { z } from 'zod';
import { checkEnforcementFromRuntime } from '../../../lib/enforcement-check-runtime';
import { enforcementRouteResponse } from '../../../lib/enforcement-boundary';
import { ingestAndEnforcePortalPost } from '../../../lib/portal-waf-ingest';

const formSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

export async function POST(req: NextRequest) {
  const enforcement = await checkEnforcementFromRuntime("LOGIN_SUBMIT");
  const enforcementResponse = enforcementRouteResponse(enforcement);
  if (enforcementResponse) return enforcementResponse;

  try {
    const formData = await req.formData();
    const data = {
      username: formData.get('username') as string,
      password: formData.get('password') as string,
    };

    const inspection = await ingestAndEnforcePortalPost({
      request: req,
      requestPath: "/login/submit",
      scope: "LOGIN_SUBMIT",
      fields: { username: data.username || "" },
    });
    if (inspection) return inspection;

    const parsed = formSchema.safeParse(data);
    if (!parsed.success) {
      return NextResponse.json({ error: "Invalid input" }, { status: 400 });
    }

    await prisma.loginAttempt.create({
      data: {
        username: parsed.data.username,
        success: false,
      },
    });

    return browserRedirect(req, "/success?type=login");
  } catch (error) {
    console.error('Error handling login submission:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
