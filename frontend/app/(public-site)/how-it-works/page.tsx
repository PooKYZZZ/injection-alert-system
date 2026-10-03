import type { Metadata } from 'next'

import {
  HowItWorksContent,
  PublicSiteFrame,
} from '../_components/PublicSite'

export const metadata: Metadata = {
  title: 'How it works | CyberTrace',
  description:
    'Explore a safe, interactive walkthrough of how CyberTrace presents request context, separate security signals, and analyst review.',
}

export default function HowItWorksPage() {
  return (
    <PublicSiteFrame currentPage="howItWorks">
      <HowItWorksContent />
    </PublicSiteFrame>
  )
}
