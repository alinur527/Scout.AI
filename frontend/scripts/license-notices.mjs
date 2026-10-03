import { readFile, mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { SOURCE_URL } from '../src/release.js'

const packages = ['react', 'react-dom', 'scheduler', 'react-router', 'react-router-dom', 'cookie', 'set-cookie-parser', 'axios']
const notices = ['ScoutAI frontend runtime dependency notices. Each dependency retains its original license and copyright. ScoutAI project source: AGPL-3.0-only; see LICENSE.txt and NOTICE.txt.\n']
for (const name of packages) {
  const folder = path.resolve('node_modules', name)
  const metadata = JSON.parse(await readFile(path.join(folder, 'package.json'), 'utf8'))
  let license
  for (const file of ['LICENSE', 'LICENSE.md', 'LICENSE.txt']) {
    try { license = await readFile(path.join(folder, file), 'utf8'); break } catch (error) {
      if (error.code !== 'ENOENT') throw error
    }
  }
  if (!license) throw new Error(`Missing runtime license: ${name}`)
  notices.push(`${name} ${metadata.version}\n${license}`)
}
await mkdir('public', { recursive: true })
await writeFile('public/third-party-licenses.txt', notices.join('\n\n'), 'utf8')
for (const [source, destination] of [
  ['../LICENSE', 'LICENSE.txt'],
  ['../NOTICE', 'NOTICE.txt'],
  ['../docs/THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.txt'],
]) {
  await writeFile(path.join('public', destination), await readFile(source))
}
await writeFile('public/SOURCE.txt', `ScoutAI complete corresponding source: ${SOURCE_URL}\nBuild/run instructions: README.md and docs/OPERATIONS.md in that source.\n`, 'utf8')
