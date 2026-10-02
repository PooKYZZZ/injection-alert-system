import Image from 'next/image'
import Link from 'next/link'
import type { ReactNode } from 'react'

import styles from '@/app/page.module.css'

const DASHBOARD_URL = 'https://app.cybertracesystems.com/login'

const focusAreas = [
  {
    number: '01',
    title: 'See the request clearly',
    copy: 'Bring the method, route, and available request details into one readable record.',
  },
  {
    number: '02',
    title: 'Understand the signals',
    copy: 'Review the model’s suggestion alongside any firewall findings recorded for the request.',
  },
  {
    number: '03',
    title: 'Keep people in control',
    copy: 'Analysts review the available context and record a decision; the system does not make the final call.',
  },
]

const technicalNotes = [
  'The operational security workflow focuses on possible SQL- and code-injection records. A model confidence score is one signal for review, not proof of an attack or a calibrated probability.',
  'ModSecurity and the OWASP Core Rule Set (CRS) may record matched rules and scores. CyberTrace links those findings to a request only when the available identifiers support the connection; they remain separate from the model result, response status, and saved action.',
  'Some request details are redacted or unavailable. CyberTrace leaves missing evidence unknown instead of filling it in, and a saved action by itself does not confirm that a request was blocked.',
  'Traffic History can include Normal records when a user opts in. Those records remain read-only and do not receive the security-record triage workflow.',
]

type TeamMember = {
  name: string
  initials: string
  focus: string
  image?: string
}

const teamMembers: TeamMember[] = [
  {
    name: 'Mark Angelo A. Aquino',
    initials: 'MA',
    focus: 'Systems Administration',
    image: '/team/mark-angelo-aquino.webp',
  },
  {
    name: 'Junaid Bantuas',
    initials: 'JB',
    focus: 'Intelligent Systems',
    image: '/team/junaid-bantuas.webp',
  },
  {
    name: 'Eugene Dela Cruz',
    initials: 'ED',
    focus: 'Data Science',
    image: '/team/eugene-dela-cruz.webp',
  },
  {
    name: 'Froilan Gayao',
    initials: 'FG',
    focus: 'Systems Administration',
    image: '/team/froilan-gayao.webp',
  },
  {
    name: 'Faron Jabez Nonan',
    initials: 'FN',
    focus: 'Systems Administration',
    image: '/team/faron-jabez-nonan.webp',
  },
]

type PublicPage = 'home' | 'aboutProject' | 'howItWorks' | 'aboutUs'

const navigationItems: {
  page: Exclude<PublicPage, 'home'>
  href: string
  label: string
}[] = [
  { page: 'aboutProject', href: '/about-project', label: 'About the Project' },
  { page: 'howItWorks', href: '/how-it-works', label: 'How it works' },
  { page: 'aboutUs', href: '/about-us', label: 'About Us' },
]

export function PublicSiteFrame({
  currentPage,
  children,
}: {
  currentPage: PublicPage
  children: ReactNode
}) {
  return (
    <div className={styles.site}>
      <a className={styles.skipLink} href="#main-content">
        Skip to main content
      </a>

      <header className={styles.header} id="top">
        <div className={styles.headerInner}>
          <Link className={styles.brand} href="/" prefetch={false} aria-label="CyberTrace project overview">
            <Image
              className={styles.brandMark}
              src="/logo.png"
              alt=""
              width={44}
              height={44}
              priority
            />
            <span className={styles.wordmark}>CyberTrace</span>
            <span className={styles.brandDivider} aria-hidden="true" />
            <span className={styles.brandDescriptor}>Project overview</span>
          </Link>

          <nav className={styles.navigation} aria-label="Project pages">
            {navigationItems.map((item) => (
              <Link className={currentPage === item.page ? styles.currentNavigation : undefined} href={item.href} prefetch={false} aria-current={currentPage === item.page ? 'page' : undefined} key={item.page}>
                {item.label}
              </Link>
            ))}
          </nav>

          <a className={styles.headerCta} href={DASHBOARD_URL}>
            <span>Open CyberTrace Dashboard</span>
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      </header>

      <main id="main-content">{children}</main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <Link className={styles.footerBrand} href="/" prefetch={false}>
            <Image
              src="/logo.png"
              alt=""
              width={30}
              height={30}
              className={styles.footerMark}
            />
            <span>CyberTrace</span>
          </Link>
          <p>
            An academic cybersecurity project by Team 12. No affiliation with
            or endorsement by a government agency or land-records authority is
            implied.
          </p>
          <a className={styles.footerDashboard} href={DASHBOARD_URL}>
            Dashboard login <span aria-hidden="true">↗</span>
          </a>
        </div>
      </footer>
    </div>
  )
}

export function ProjectOverviewContent() {
  return (
    <>
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroGlow} aria-hidden="true" />
        <div className={styles.heroInner}>
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>
              <span className={styles.eyebrowMark} aria-hidden="true" />
              Academic cybersecurity project · Team 12
            </p>
            <h1 id="hero-title">
              Security review
              <br />
              starts with context.
            </h1>
            <p className={styles.heroLead}>
              Investigating suspicious web activity can mean reading long
              requests and scattered evidence over and over. CyberTrace
              explores how to make that review clearer, more focused, and less
              tiring.
            </p>
            <p className={styles.heroAudience}>
              A student project designed to help analysts find useful context
              while keeping people in charge of the decision.
            </p>

            <div className={styles.heroActions}>
              <a className={styles.primaryButton} href={DASHBOARD_URL}>
                <span>Open CyberTrace Dashboard</span>
                <span className={styles.buttonArrow} aria-hidden="true">
                  ↗
                </span>
              </a>
              <a className={styles.textButton} href="#explore-project">
                Explore the project
                <span aria-hidden="true">↓</span>
              </a>
            </div>

            <div className={styles.heroNote}>
              <span className={styles.noteRule} aria-hidden="true" />
              <p>
                An academic prototype. The public overview, dashboard, and
                protected demo are separate sites.
              </p>
            </div>
          </div>

          <figure className={styles.heroFigure}>
            <div className={styles.figureTopline}>
              <span className={styles.figureIndex}>PROJECT MAP / 01</span>
              <span className={styles.figureBadge}>Original illustration</span>
            </div>
            <picture>
              <source
                media="(max-width: 520px)"
                srcSet="/assets/cybertrace-evidence-map-mobile.svg"
                type="image/svg+xml"
              />
              <Image
                className={styles.evidenceMap}
                src="/assets/cybertrace-evidence-map.svg"
                alt="Concept illustration showing a web request becoming a clearer traffic record with available supporting information for an analyst to review. It is not live data."
                width={1080}
                height={680}
                priority
                sizes="(max-width: 880px) 92vw, 49vw"
              />
            </picture>
            <figcaption className={styles.figureCaption}>
              <span className={styles.captionDot} aria-hidden="true" />
              A concept illustration, not a live dashboard.
            </figcaption>
          </figure>
        </div>

        <div className={styles.heroBaseline} aria-hidden="true">
          <span>Evidence before assumption</span>
          <span className={styles.baselineLine} />
          <span>Academic capstone</span>
        </div>
      </section>

      <section
        className={styles.exploreSection}
        id="explore-project"
        aria-labelledby="explore-title"
      >
        <div className={styles.contentWidth}>
          <div className={styles.sectionIndex}>
            <span>01</span>
            <span>Explore CyberTrace</span>
          </div>
          <div className={styles.exploreHeading}>
            <h2 id="explore-title">Choose a place to start.</h2>
            <p>
              Learn why the project exists, follow how a record reaches review,
              or meet the students behind it.
            </p>
          </div>

          <div className={styles.destinationGrid}>
            <Link
              className={styles.destinationCard}
              href="/about-project"
              id="about-project"
             prefetch={false}>
              <span className={styles.destinationIndex}>01 / THE PURPOSE</span>
              <h3>About the Project</h3>
              <p>
                The investigation burden CyberTrace is designed to study and
                the context it brings together.
              </p>
              <span className={styles.destinationLink}>Read about the project <span aria-hidden="true">↗</span></span>
            </Link>
            <Link
              className={styles.destinationCard}
              href="/how-it-works"
              id="how-it-works"
             prefetch={false}>
              <span className={styles.destinationIndex}>02 / THE WORKFLOW</span>
              <h3>How it works</h3>
              <p>
                See how request details, separate signals, and analyst review
                fit together.
              </p>
              <span className={styles.destinationLink}>Follow the workflow <span aria-hidden="true">↗</span></span>
            </Link>
            <Link
              className={styles.destinationCard}
              href="/about-us"
              id="about-us"
             prefetch={false}>
              <span className={styles.destinationIndex}>03 / THE TEAM</span>
              <h3>About Us</h3>
              <p>
                Meet the five Team 12 members listed in the project materials.
              </p>
              <span className={styles.destinationLink}>Meet Team 12 <span aria-hidden="true">↗</span></span>
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}

export function AboutProjectContent() {
  return (
    <section className={styles.projectSection} aria-labelledby="project-title">
      <div className={styles.contentWidth}>
        <Link className={styles.pageBackLink} href="/" prefetch={false}>
          ← Project overview
        </Link>
        <div className={styles.sectionIndex}>
          <span>01</span>
          <span>About the Project</span>
        </div>
        <div className={styles.sectionIntro}>
          <div className={styles.projectIntroGrid}>
            <div>
              <h1 id="project-title">
                Less time searching. More focus for review.
              </h1>
              <p className={styles.sectionLead}>
                Analysts may need to inspect long, complex requests and large
                amounts of raw evidence when investigating possible attacks.
                Repeating that work across many records takes time and can
                become mentally exhausting. CyberTrace focuses on possible
                injection attacks: web requests that may try to make a site
                treat user input as instructions.
              </p>
            </div>
            <p className={styles.projectQuestion}>
              <span>WHAT CYBERTRACE AIMS TO DO</span>
              Bring the useful details together so each record is easier to
              understand before an analyst decides what to do.
            </p>
          </div>
        </div>

        <div className={styles.projectBodyGrid}>
          <div className={styles.focusGrid}>
            {focusAreas.map((area) => (
              <article
                className={styles.focusCard}
                key={area.number}
              >
                <span className={styles.cardNumber}>{area.number}</span>
                <h2>{area.title}</h2>
                <p>{area.copy}</p>
              </article>
            ))}
          </div>
        </div>

        <details className={styles.technicalDetails}>
          <summary>
            <span>Technical details</span>
            <span>How the prototype handles model and firewall findings</span>
          </summary>
          <ul>
            {technicalNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </details>

        <Link className={styles.pageNextLink} href="/how-it-works" prefetch={false}>
          See how the workflow works <span aria-hidden="true">→</span>
        </Link>
      </div>
    </section>
  )
}

const workflowStages = [
  {
    number: '01',
    label: 'REQUEST CONTEXT',
    title: 'Start with the details that exist.',
    copy: 'A traffic record can show the request information that was recorded, such as its method, route, time, and available request data. Missing details remain unknown.',
  },
  {
    number: '02',
    label: 'SEPARATE SIGNALS',
    title: 'Read each finding for what it is.',
    copy: 'The model suggests a likely request category and gives a confidence score. Firewall findings may also be shown when they are recorded and can be linked to the request.',
  },
  {
    number: '03',
    label: 'ANALYST REVIEW',
    title: 'Leave the decision with a person.',
    copy: 'Analysts open the record in Traffic History, review its available context, and use the supported triage tools to record their assessment.',
  },
]

export function HowItWorksContent() {
  return (
    <section className={styles.howPage} aria-labelledby="workflow-title">
      <div className={styles.contentWidth}>
        <Link className={styles.howBackLink} href="/" prefetch={false}>
          ← Project overview
        </Link>
        <div className={styles.sectionIndex}>
          <span>02</span>
          <span>How it works</span>
        </div>

        <div className={styles.howIntro}>
          <h1 id="workflow-title">A clearer path from request to review.</h1>
          <p>
            CyberTrace brings available request details into Traffic History.
            Model suggestions and firewall findings stay separate, so an
            analyst can review what each one actually says.
          </p>
        </div>

        <figure className={styles.howFlow} aria-labelledby="flow-caption">
          <div className={styles.howFlowRow}>
            <div className={styles.howNode}>
              <span className={styles.howNodeLabel}>01 / REQUEST CONTEXT</span>
              <h2>Request details</h2>
              <p>Method, route, time, and other information when recorded.</p>
            </div>
            <span className={styles.howArrow} aria-hidden="true">→</span>
            <div className={[styles.howNode, styles.howRecordNode].join(' ')}>
              <span className={styles.howNodeLabel}>TRAFFIC HISTORY</span>
              <h2>One reviewable record</h2>
              <p>Available request context with supporting signals kept distinct.</p>
            </div>
            <span className={styles.howArrow} aria-hidden="true">→</span>
            <div className={styles.howNode}>
              <span className={styles.howNodeLabel}>03 / HUMAN REVIEW</span>
              <h2>Analyst assessment</h2>
              <p>A person reviews the evidence and records a supported triage decision.</p>
            </div>
          </div>

          <div className={styles.signalGroup}>
            <p className={styles.signalGroupLabel}>
              Supporting signals appear when recorded and available
            </p>
            <div className={styles.signalGrid}>
              <div className={styles.signalCard}>
                <span className={styles.signalTag}>MODEL SUGGESTION</span>
                <p>A likely request category and its confidence score.</p>
              </div>
              <div className={styles.signalCard}>
                <span className={styles.signalTag}>FIREWALL FINDING</span>
                <p>Recorded rule evidence, when it can be linked to this request.</p>
              </div>
            </div>
          </div>

          <figcaption id="flow-caption">
            A conceptual view. Not every record has all signals or complete
            request details.
          </figcaption>
        </figure>

        <ol className={styles.howStages}>
          {workflowStages.map((stage) => (
            <li className={styles.howStage} key={stage.number}>
              <div className={styles.howStageMeta}>
                <span>{stage.number}</span>
                <span>{stage.label}</span>
              </div>
              <h2>{stage.title}</h2>
              <p>{stage.copy}</p>
            </li>
          ))}
        </ol>

        <p className={styles.howBoundary}>
          A model score is not proof of an attack, and a recorded action alone
          does not prove the request was blocked. CyberTrace is an academic
          prototype that supports human review.
        </p>

        <details className={[styles.technicalDetails, styles.howDetails].join(' ')}>
          <summary>
            <span>Technical notes</span>
            <span>What the prototype records and what remains separate</span>
          </summary>
          <ul>
            <li>
              The local proof path uses ModSecurity with the OWASP Core Rule
              Set. A finding appears with a traffic record only when the
              available identifiers support the link.
            </li>
            <li>
              Model output, confidence, firewall evidence, response status,
              recorded action, and applied enforcement describe different
              facts. One does not establish the others.
            </li>
            <li>
              Some request details may be redacted or unavailable. The
              prototype leaves those gaps unknown instead of filling them in.
            </li>
          </ul>
        </details>

        <a className={styles.howDashboardLink} href={DASHBOARD_URL}>
          Open the CyberTrace Dashboard <span aria-hidden="true">↗</span>
        </a>
      </div>
    </section>
  )
}

export function AboutUsContent() {
  return (
    <section className={styles.teamSection} aria-labelledby="team-title">
      <div className={styles.contentWidth}>
        <Link className={styles.pageBackLink} href="/" prefetch={false}>
          ← Project overview
        </Link>
        <div className={styles.sectionIndex}>
          <span>03</span>
          <span>About Us</span>
        </div>
        <header className={styles.aboutIntro}>
          <div>
            <h1 id="team-title">Meet Team 12.</h1>
            <p className={styles.teamLead}>
              We are the students behind CyberTrace, an academic project about
              making suspicious web activity clearer to review.
            </p>
          </div>
          <p className={styles.aboutIntroCopy}>
            We bring request context, supporting evidence, and human review
            together—without asking a model to make the final call.
          </p>
        </header>

        <section className={styles.teamProfiles} aria-labelledby="team-profiles-title">
          <div className={styles.profileSectionHeading}>
            <div>
              <p className={styles.profileEyebrow}>TEAM 12</p>
              <h2 id="team-profiles-title">The people behind the project</h2>
            </div>
            <p>Meet the students and their areas of focus.</p>
          </div>

          <ul className={styles.profileGrid} aria-label="Team 12 members">
            {teamMembers.map((member, index) => (
              <li key={member.name}>
                <article className={styles.profileCard}>
                  <div
                    className={[
                      styles.profilePhoto,
                      member.image ? styles.profilePhotoWithImage : '',
                    ].filter(Boolean).join(' ')}
                  >
                    {member.image ? (
                      <Image
                        alt={`Portrait of ${member.name}`}
                        className={styles.profilePortrait}
                        fill
                        sizes="(max-width: 700px) 106px, (max-width: 1100px) 28vw, 300px"
                        src={member.image}
                      />
                    ) : (
                      <div
                        role="img"
                        aria-label={`Formal portrait placeholder for ${member.name}`}
                      >
                        <span className={styles.profileMonogram} aria-hidden="true">
                          {member.initials}
                        </span>
                        <span className={styles.profilePhotoLabel}>
                          Add formal portrait
                        </span>
                      </div>
                    )}
                  </div>
                  <div className={styles.profileInfo}>
                    <p className={styles.profileIndex}>
                      TEAM MEMBER <span>{String(index + 1).padStart(2, '0')}</span>
                    </p>
                    <h3>{member.name}</h3>
                    <p className={styles.profileRole}>{member.focus}</p>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        </section>

        <aside className={styles.adviserCard} aria-labelledby="adviser-title">
          <div
            className={[
              styles.profilePhoto,
              styles.profilePhotoWithImage,
              styles.adviserPhoto,
            ].join(' ')}
          >
            <Image
              alt="Portrait of Robin Valenzuela, Team Adviser"
              className={styles.profilePortrait}
              fill
              sizes="(max-width: 700px) 146px, (max-width: 1100px) 125px, 180px"
              src="/team/robin-valenzuela.webp"
            />
          </div>
          <div className={styles.adviserCopy}>
            <p className={styles.profileEyebrow}>PROJECT GUIDANCE</p>
            <h2 id="adviser-title">Our project adviser</h2>
            <p className={styles.adviserName}>Robin Valenzuela · Team Adviser</p>
            <p>Academic guidance for Team 12 throughout the CyberTrace project.</p>
          </div>
        </aside>
      </div>
    </section>
  )
}
