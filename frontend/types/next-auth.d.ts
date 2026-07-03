import type { DefaultSession, DefaultJWT } from 'next-auth'
import type { UserRole } from '@/lib/auth/roles'

declare module 'next-auth' {
  interface Session {
    user: {
      id: string
      role: UserRole
      authz_version: number
    } & DefaultSession['user']
  }

  interface User {
    role: UserRole
    authz_version: number
  }
}

declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    id: string
    role: UserRole
    authz_version: number
  }
}
