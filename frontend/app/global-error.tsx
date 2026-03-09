'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="en">
      <body style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
        <h2>Something went wrong</h2>
        <p>An unexpected error occurred. Please try again.</p>
        {process.env.NODE_ENV === 'development' && <pre>{error.message}</pre>}
        <button onClick={reset}>Try again</button>
      </body>
    </html>
  )
}
