import type { DefaultSession, DefaultJWT } from 'next-auth'
import type { UserRole } from '@/lib/auth/roles'

declare module 'next-auth' {
  interface Session {
    user: {
      id: string
      role: UserRole
      authz_version: number
      auth_level?: 'password' | 'recovery' | 'mfa'
      auth_method?: 'password' | 'totp' | 'backup_code' | 'email_otp'
      auth_time?: number
    } & DefaultSession['user']
  }

  interface User {
    role: UserRole
    authz_version: number
    auth_level?: 'password' | 'recovery' | 'mfa'
    auth_method?: 'password' | 'totp' | 'backup_code' | 'email_otp'
    auth_time?: number
  }
}

declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    id: string
    role: UserRole
    authz_version: number
    auth_level?: 'password' | 'recovery' | 'mfa'
    auth_method?: 'password' | 'totp' | 'backup_code' | 'email_otp'
    auth_time?: number
  }
}
