import type { Metadata } from 'next'

import {
  AboutProjectContent,
  PublicSiteFrame,
} from '../_components/PublicSite'

export const metadata: Metadata = {
  title: 'About the Project | CyberTrace',
  description:
    'Why Team 12 built CyberTrace to make evidence-heavy security review clearer and less tiring.',
}

export default function AboutProjectPage() {
  return (
    <PublicSiteFrame currentPage="aboutProject">
      <AboutProjectContent />
    </PublicSiteFrame>
  )
}
