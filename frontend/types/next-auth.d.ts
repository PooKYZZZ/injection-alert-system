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
      mfa_challenge_expires_at?: string
      mfa_challenge_purpose?:
        | 'login_mfa'
        | 'mfa_enrollment'
        | 'recent_reauthentication'
        | 'mfa_recovery'
    } & DefaultSession['user']
  }

  interface User {
    role: UserRole
    authz_version: number
    auth_level?: 'password' | 'recovery' | 'mfa'
    auth_method?: 'password' | 'totp' | 'backup_code' | 'email_otp'
    auth_time?: number
    mfa_challenge_expires_at?: string
    mfa_challenge_purpose?:
      | 'login_mfa'
      | 'mfa_enrollment'
      | 'recent_reauthentication'
      | 'mfa_recovery'
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
    mfa_challenge_expires_at?: string
    mfa_challenge_purpose?:
      | 'login_mfa'
      | 'mfa_enrollment'
      | 'recent_reauthentication'
      | 'mfa_recovery'
  }
}
