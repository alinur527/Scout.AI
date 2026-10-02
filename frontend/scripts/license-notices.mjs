import { readFile, mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const packages = ['react', 'react-dom', 'scheduler', 'react-router', 'react-router-dom', 'cookie', 'set-cookie-parser', 'axios']
const notices = ['ScoutAI frontend runtime dependency notices. These notices do not assign a license to ScoutAI source.\n']
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
