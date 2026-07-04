import argon2 from 'argon2'

const MEMORY_COST = 19_456
const TIME_COST = 2
const PARALLELISM = 1
const MAX_PASSWORD_LENGTH = 256
const SAMPLES = 5
const password = 'local benchmark input'

function percentile(values, fraction) {
  const sorted = [...values].sort((left, right) => left - right)
  return sorted[Math.ceil(sorted.length * fraction) - 1]
}

const hashes = []
for (let index = 0; index < SAMPLES; index += 1) {
  hashes.push(
    await argon2.hash(password, {
      type: argon2.argon2id,
      memoryCost: MEMORY_COST,
      timeCost: TIME_COST,
      parallelism: PARALLELISM,
    })
  )
}

const verifyTimes = []
for (const hash of hashes) {
  const startedAt = performance.now()
  if (!(await argon2.verify(hash, password))) {
    throw new Error('Argon2id benchmark verification failed.')
  }
  verifyTimes.push(performance.now() - startedAt)
}

console.log(`Argon2id benchmark:

* memoryCost: ${MEMORY_COST} KiB
* timeCost: ${TIME_COST}
* parallelism: ${PARALLELISM}
* samples: ${SAMPLES}
* p50 verify ms: ${percentile(verifyTimes, 0.5).toFixed(2)}
* p95 verify ms: ${percentile(verifyTimes, 0.95).toFixed(2)}
* max password length: ${MAX_PASSWORD_LENGTH}`)
