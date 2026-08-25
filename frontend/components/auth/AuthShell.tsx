import Image from 'next/image'
import Link from 'next/link'
import type { ReactNode } from 'react'

import styles from './AuthShell.module.css'

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className={styles.shell} aria-label="CyberTrace authentication">
      <div className={styles.surface}>
        <header className={styles.header}>
          <Link href="/login" className={styles.brand} aria-label="CyberTrace home">
            <Image src="/logo.png" alt="" width={28} height={28} priority className={styles.logo} />
            <span>CyberTrace</span>
          </Link>
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </main>
  )
}
