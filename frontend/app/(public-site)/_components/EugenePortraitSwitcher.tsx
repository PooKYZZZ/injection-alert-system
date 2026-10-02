'use client'

import Image from 'next/image'
import { useState } from 'react'

import styles from '@/app/page.module.css'

export function EugenePortraitSwitcher({
  updatedImage,
  previousImage,
}: {
  updatedImage: string
  previousImage: string
}) {
  const [showPrevious, setShowPrevious] = useState(false)

  return (
    <>
      <Image
        alt="Portrait of Eugene Dela Cruz"
        className={styles.profilePortrait}
        fill
        sizes="(max-width: 700px) 106px, (max-width: 1100px) 28vw, 300px"
        src={showPrevious ? previousImage : updatedImage}
      />
      <div className={styles.portraitSwitcher}>
        <span aria-hidden="true">New</span>
        <input
          aria-label="Choose Eugene Dela Cruz’s portrait"
          aria-valuetext={showPrevious ? 'Previous portrait' : 'New portrait'}
          max={1}
          min={0}
          onChange={(event) => setShowPrevious(Number(event.currentTarget.value) === 1)}
          step={1}
          type="range"
          value={showPrevious ? 1 : 0}
        />
        <span aria-hidden="true">Previous</span>
      </div>
    </>
  )
}
