import type { Metadata } from 'next'
import { IBM_Plex_Sans, Inter, Orbitron } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-ibm-plex-sans',
})

const orbitron = Orbitron({
  subsets: ['latin'],
  weight: ['400', '600', '700'],
  variable: '--font-orbitron',
})

export const metadata: Metadata = {
  title: 'Injection Alert System',
  description: 'SOC Dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${ibmPlexSans.variable} ${orbitron.variable}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
