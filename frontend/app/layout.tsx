import type { Metadata } from 'next'
import { IBM_Plex_Sans, Inter, JetBrains_Mono, Orbitron } from 'next/font/google'
import type { ReactNode } from 'react'
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

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-jetbrains-mono',
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

const themeBootstrapScript = `(() => {
  const storageKey = 'ias-theme';
  const root = document.documentElement;
  const storedTheme = localStorage.getItem(storageKey);
  const hasExplicitTheme = storedTheme === 'light' || storedTheme === 'dark';
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const resolvedTheme = hasExplicitTheme ? storedTheme : systemTheme;

  root.setAttribute('data-theme', resolvedTheme);
  root.style.colorScheme = resolvedTheme;
})();`

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script id="theme-bootstrap" dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
      </head>
      <body className={`${inter.variable} ${ibmPlexSans.variable} ${jetbrainsMono.variable} ${orbitron.variable}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
