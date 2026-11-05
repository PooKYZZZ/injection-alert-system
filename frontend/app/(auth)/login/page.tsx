import LoginForm from './login-form'

export const dynamic = 'force-dynamic'

export default function LoginPage() {
  return (
    <LoginForm
      turnstileSiteKey={
        process.env.NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY ?? ''
      }
    />
  )
}
