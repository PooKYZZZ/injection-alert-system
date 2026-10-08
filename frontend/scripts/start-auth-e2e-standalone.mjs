import { spawn } from 'node:child_process'
import { cp, mkdir } from 'node:fs/promises'
import path from 'node:path'

const frontendDirectory = process.cwd()
const standaloneDirectory = path.join(frontendDirectory, '.next', 'standalone')
const staticSource = path.join(frontendDirectory, '.next', 'static')
const staticDestination = path.join(standaloneDirectory, '.next', 'static')
const publicSource = path.join(frontendDirectory, 'public')
const publicDestination = path.join(standaloneDirectory, 'public')
const frontendOrigin = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3000'
const frontendPort = new URL(frontendOrigin).port || '3000'

await mkdir(path.dirname(staticDestination), { recursive: true })
await cp(staticSource, staticDestination, { recursive: true, force: true })
await cp(publicSource, publicDestination, { recursive: true, force: true })

const serverPath = path.join(standaloneDirectory, 'server.js')
const server = spawn(process.execPath, [serverPath], {
  cwd: frontendDirectory,
  env: { ...process.env, PORT: frontendPort },
  stdio: 'inherit',
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.kill(signal))
}

const exitCode = await new Promise((resolve, reject) => {
  server.once('error', reject)
  server.once('exit', (code, signal) => {
    resolve(code ?? (signal ? 1 : 0))
  })
})

process.exitCode = exitCode
