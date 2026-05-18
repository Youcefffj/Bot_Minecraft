// Bot Minecraft — se connecte au proxy ViaProxy local (127.0.0.1:25568).
// ViaProxy fait l'auth Microsoft vers le vrai serveur et traduit protocole
// 774 (1.21.11, ce que mineflayer sait parler) → 775 (ce que le serveur exige).
// Le bot ici est donc en "offline" du côté local — toute l'auth est gérée
// par le proxy en amont.

const mineflayer = require('mineflayer')

const PROXY_HOST = '127.0.0.1'
const PROXY_PORT = 25568
const CONNECT_DURATION_MS = 30_000

// BOT_USERNAME hérité de l'env du processus parent (bot.py charge .env via dotenv).
const BOT_USERNAME = process.env.BOT_USERNAME || 'Bot'

const bot = mineflayer.createBot({
  host: PROXY_HOST,
  port: PROXY_PORT,
  username: BOT_USERNAME,      // ignoré par ViaProxy (qui auth via son compte)
  auth: 'offline',
  version: '1.21.11',
})

let exitCode = 0
let disconnectTimer = null

bot.once('login', () => {
  console.log('Connecté au serveur')
  disconnectTimer = setTimeout(() => bot.quit(), CONNECT_DURATION_MS)
})

bot.on('kicked', (reason) => {
  console.log(`Kické : ${reason}`)
  exitCode = 1
})

bot.on('error', (err) => {
  console.log(`Erreur : ${err.message}`)
  exitCode = 1
})

bot.on('end', (reason) => {
  if (disconnectTimer) clearTimeout(disconnectTimer)
  console.log(`Déconnexion propre (${reason})`)
  process.exit(exitCode)
})
