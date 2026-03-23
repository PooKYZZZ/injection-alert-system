import NextAuth from 'next-auth'
import { authConfig } from './auth.config'

const { auth } = NextAuth(authConfig)

export default auth((req) => {
  void req
})

export const config = {
  matcher: [
    '/(dashboard|alerts|ml-health)/:path*',
  ],
}
