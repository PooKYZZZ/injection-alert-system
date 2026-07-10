import 'server-only'

import { createHmac, randomInt } from 'node:crypto'

const OTP_CONTEXT = 'cybertrace:email-otp:v1'

function otpKey(): Buffer {
  const raw = process.env.AUTH_EMAIL_OTP_KEY
  if (!raw || raw.length < 32) throw new Error('AUTH_EMAIL_OTP_KEY is not configured.')
  return Buffer.from(raw, 'utf8')
}

export function generateEmailOtp(): string {
  return String(randomInt(0, 1_000_000)).padStart(6, '0')
}

export function digestEmailOtp(code: string): string {
  if (!/^\d{6}$/.test(code)) throw new Error('Email OTP is invalid.')
  return createHmac('sha256', otpKey())
    .update(`${OTP_CONTEXT}:${code}`, 'utf8')
    .digest('hex')
}
