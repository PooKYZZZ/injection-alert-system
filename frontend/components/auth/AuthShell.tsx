import Image from 'next/image'
import Link from 'next/link'
import type { ReactNode } from 'react'

import styles from './AuthShell.module.css'

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className={styles.shell} aria-label="CyberTrace authentication">
      <aside className={styles.visual} aria-label="CyberTrace security operations">
        <div className={styles.visualMessage}>
          <Link href="/login" className={styles.brand} aria-label="CyberTrace home">
            <Image
              src="/logo.png"
              alt=""
              width={70}
              height={70}
              priority
              className={styles.logo}
            />
            <span>CyberTrace</span>
          </Link>

          <p className={styles.visualEyebrow}>
            WAF–ML security operations
          </p>

          <h2 className={styles.visualTitle}>
            Protect every request.
          </h2>

          <p className={styles.visualDescription}>
            Investigate injection signals with the context your team needs to respond.
          </p>
        </div>

        <div className={styles.visualFooter} aria-hidden="true">
          <span>CyberTrace / internal workspace</span>
          <span>Protected access</span>
        </div>
      </aside>

      <section className={styles.contentPane} aria-label="Authentication form">
        <div className={styles.content}>{children}</div>
      </section>
    </main>
  )
}
