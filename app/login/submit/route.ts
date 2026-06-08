import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { browserRedirect } from '@/lib/redirect';
import { z } from 'zod';

const formSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const data = {
      username: formData.get('username') as string,
      password: formData.get('password') as string,
    };

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
