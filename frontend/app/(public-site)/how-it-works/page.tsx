import type { Metadata } from 'next'

import {
  HowItWorksContent,
  PublicSiteFrame,
} from '../_components/PublicSite'

export const metadata: Metadata = {
  title: 'How it works | CyberTrace',
  description:
    'See how CyberTrace brings recorded request context and separate supporting signals into a human review workflow.',
}

export default function HowItWorksPage() {
  return (
    <PublicSiteFrame currentPage="howItWorks">
      <HowItWorksContent />
    </PublicSiteFrame>
  )
}