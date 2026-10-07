'use client'

import Image from 'next/image'
import { useState } from 'react'

import styles from '@/app/page.module.css'

type EugeneProfileCardProps = {
  focus: string
  index: number
  name: string
  previousImage: string
  updatedImage: string
}

export function EugeneProfileCard({
  focus,
  index,
  name,
  previousImage,
  updatedImage,
}: EugeneProfileCardProps) {
  const [showPrevious, setShowPrevious] = useState(false)

  return (
    <article className={styles.profileCard}>
      <div className={[styles.profilePhoto, styles.profilePhotoWithImage].join(' ')}>
        <Image
          alt={showPrevious ? '' : `Portrait of ${name}`}
          aria-hidden={showPrevious || undefined}
          className={[
            styles.profilePortrait,
            showPrevious ? styles.profilePortraitInactiveLeft : styles.profilePortraitActive,
          ].join(' ')}
          fill
          sizes="(max-width: 700px) 106px, (max-width: 1100px) 28vw, 300px"
          src={updatedImage}
        />
        <Image
          alt={showPrevious ? `Portrait of ${name}` : ''}
          aria-hidden={!showPrevious || undefined}
          className={[
            styles.profilePortrait,
            showPrevious ? styles.profilePortraitActive : styles.profilePortraitInactiveRight,
          ].join(' ')}
          fill
          sizes="(max-width: 700px) 106px, (max-width: 1100px) 28vw, 300px"
          src={previousImage}
        />
      </div>
      <div className={styles.profileInfo}>
        <p className={styles.profileIndex}>
          TEAM MEMBER <span>{String(index + 1).padStart(2, '0')}</span>
        </p>
        <h3>{name}</h3>
        <p className={styles.profileRole}>{focus}</p>
        <div className={styles.portraitSwitcher}>
          <span className={showPrevious ? undefined : styles.portraitSwitcherOptionActive}>
            New
          </span>
          <label className={styles.portraitToggle}>
            <input
              aria-label={`Use the previous portrait of ${name}`}
              checked={showPrevious}
              className={styles.portraitToggleInput}
              onChange={(event) => setShowPrevious(event.currentTarget.checked)}
              role="switch"
              type="checkbox"
            />
            <span className={styles.portraitToggleTrack} aria-hidden="true">
              <span className={styles.portraitToggleThumb}>
                <span className={styles.portraitToggleChevron} />
              </span>
            </span>
          </label>
          <span className={showPrevious ? styles.portraitSwitcherOptionActive : undefined}>
            Previous
          </span>
        </div>
      </div>
    </article>
  )
}
