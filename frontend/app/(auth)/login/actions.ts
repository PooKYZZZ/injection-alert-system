'use server'

import { signIn } from '@/auth'

export async function loginAction(password: string): Promise<void> {
  await signIn('credentials', {
    password,
    redirectTo: '/dashboard'
  })
}