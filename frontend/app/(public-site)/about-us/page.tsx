import type { Metadata } from 'next'

import {
  AboutUsContent,
  PublicSiteFrame,
} from '../_components/PublicSite'

export const metadata: Metadata = {
  title: 'About Us | CyberTrace',
  description:
    'Meet Team 12, the students behind the CyberTrace academic project.',
}

export default function AboutUsPage() {
  return (
    <PublicSiteFrame currentPage="aboutUs">
      <AboutUsContent />
    </PublicSiteFrame>
  )
}
