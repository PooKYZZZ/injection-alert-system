import type { Metadata } from 'next'

import {
  ProjectOverviewContent,
  PublicSiteFrame,
} from './_components/PublicSite'

export const metadata: Metadata = {
  title: 'CyberTrace | Academic Cybersecurity Project',
  description:
    'CyberTrace is Team 12’s academic project exploring clearer review of possible injection activity in web requests.',
}

export default function ProjectOverviewPage() {
  return (
    <PublicSiteFrame currentPage="home">
      <ProjectOverviewContent />
    </PublicSiteFrame>
  )
}
