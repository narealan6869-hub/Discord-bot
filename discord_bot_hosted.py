"""
Bot Discord — Alan
Version hébergée avec keep-alive Flask pour Render.
Toutes les 87 commandes + tickets + musique + anti-crash + anti-mod.
"""
import os
import threading
from flask import Flask

# ─── Keep-alive Flask (pour Render free tier) ───
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot Discord en ligne !"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_web, daemon=True)
    t.start()

import os
import json
import random
import asyncio
import aiohttp
import re
import urllib.parse
from datetime import timedelta, datetime, timezone
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands, tasks

# ─── Configuration ───
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Tracking ───
START_FILE = "/tmp/discord_bot_started"
START_TIME = datetime.now()
BOT_START_TIME = datetime.now(timezone.utc)
IS_RESTART = os.path.exists(START_FILE)
os.makedirs(os.path.dirname(START_FILE), exist_ok=True)
with open(START_FILE, "w") as f:
    f.write(START_TIME.isoformat())

# ─── Stockage JSON ───
DATA_DIR = "/tmp/discord_bot_data"
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filename):
    try:
        with open(os.path.join(DATA_DIR, filename), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(filename, data):
    with open(os.path.join(DATA_DIR, filename), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─── Snipe / Edit snipe ───
sniped_messages = {}
edited_messages = {}

# ─── Spam detection ───
user_messages = defaultdict(lambda: deque(maxlen=5))
user_warnings = defaultdict(lambda: defaultdict(int))  # guild_id -> user_id -> count

# ─── Mute tracking for wrong channel ───
wrong_channel_warnings = defaultdict(lambda: defaultdict(int))

# ─── Music queues ───
music_queues = defaultdict(list)
now_playing = {}

# ─── Bad words list ───
# ─── Anti-link whitelist ───
LINK_WHITELIST = [
    "discord.com", "discord.gg", "youtube.com", "youtu.be", "google.com",
    "github.com", "twitter.com", "x.com", "instagram.com", "tiktok.com",
    "twitch.tv", "spotify.com", "reddit.com", "wikipedia.org", "giphy.com",
]

LINK_REGEX = re.compile(r'https?://[^\s]+')

# ─── WYR / NHI / Truth / Dare ───
WYR_QUESTIONS = [
    "Avoir le pouvoir de voler mais avoir peur des hauteurs", "Avoir le pouvoir d'invisibilité mais être nu",
    "Ne jamais pouvoir mentir", "Ne jamais pouvoir arrêter de parler",
    "Vivre sans musique", "Vivre sans films", "Être le plus intelligent du monde",
    "Être le plus beau/beille du monde", "Toujours avoir froid", "Toujours avoir chaud",
    "Manger la même chose toute ta vie", "Ne plus jamais manger ta nourriture préférée",
    "Voyager dans le passé", "Voyager dans le futur", "Être riche et seul",
    "Être pauvre et entouré d'amis", "Ne plus jamais dormir", "Ne plus jamais manger",
    "Avoir des super pouvoirs mais les perdre après 1 an", "Ne jamais en avoir mais vivre 200 ans",
]

NHI_QUESTIONS = [
    "J'ai déjà envoyé un message au mauvais personne", "J'ai déjà pleuré devant un film",
    "J'ai déjà menti sur mon âge", "J'ai déjà mangé quelque chose tombé par terre",
    "J'ai déjà chanté sous la douche", "J'ai déjà oublié l'anniversaire de quelqu'un",
    "J'ai déjà menti pour sortir d'une situation", "J'ai déjà râlé sur quelqu'un en ligne",
    "J'ai déjà dormi en cours/travail", "J'ai déjà menti sur un CV",
    "J'ai déjà bavardé pendant un film au cinéma", "J'ai déjà mangé un plat sans le réchauffer",
]

TRUTH_QUESTIONS = [
    "Quel est ton plus grand secret ?", "Quelle est la chose la plus embarrassante que tu as faite ?",
    "Qui aimes-tu secrètement ?", "Quelle est ta plus grande peur ?",
    "Quel est le mensonge le plus gros que tu as dit ?", "Quelle est la pire chose que tu as dite sur quelqu'un ?",
    "Quelle est la chose dont tu es le plus fier ?", "Quel est ton plus grand regret ?",
    "Si tu pouvais changer une chose sur toi, ce serait quoi ?", "Quelle est la pire rumeur que tu as lancée ?",
]

DARE_QUESTIONS = [
    "Chante une chanson pendant 30 secondes", "Envoie un message drôle au dernier message que tu as reçu",
    "Imite un animal au choix", "Fais 10 pompes", "Dis ta pire blague",
    "Change ton surnom en 'Rien' pendant 10 minutes", "Envoie un meme dans le salon",
    "Fais une révérence à la dernière personne qui a parlé", "Crée un acrostiche avec le nom de quelqu'un du serveur",
]

DAD_JOKES = [
    "Pourquoi les plongeurs plongent-ils en arrière ? Sinon ils tomberaient dans le bateau.",
    "Que fait une fraise sur un cheval ? Tagada tagada !",
    "Pourquoi le livre de maths est triste ? Il a plein de problèmes.",
    "Quel est le comble pour un électricien ? Ne pas être au courant.",
    "Que dit un escargot quand il croise une limace ? Oh la nudiste !",
    "Pourquoi les fantômes ne mentent pas ? Ils sont transparents.",
    "Que fait une vache avec une radio ? De la meuh-sique !",
    "Que fait un papier quand il a froid ? Il claque.",
]

SHOP_ITEMS = {
    "vip": {"name": "Rôle VIP", "price": 5000, "description": "Un statut VIP"},
    "lottery": {"name": "Ticket de loterie", "price": 500, "description": "Tente ta chance !"},
    "shield": {"name": "Bouclier anti-vol", "price": 1000, "description": "Protège 24h"},
    "boost": {"name": "Boost XP", "price": 2000, "description": "Double XP 1h"},
    "rename": {"name": "Changement de surnom", "price": 300, "description": "Change ton surnom"},
}

BALL_RESPONSES = [
    "Oui, absolument.", "C'est certain.", "Sans aucun doute.", "Oui, définitivement.",
    "Tu peux compter dessus.", "Très probable.", "Bonne perspective.", "Les signes disont oui.",
    "Hmm, je ne suis pas sûr.", "Demande plus tard.", "Je ne peux pas prédire maintenant.",
    "Concentre-toi et redemande.", "Mieux vaut ne pas te le dire.",
    "Mes sources disent non.", "Très peu probable.", "Le doute est grand.",
    "Non, définitivement non.", "Non.", "N'y compte pas.",
]

DM_RESPONSES = [
    "Salut ! Comment ça va ?", "Yep je suis là ! 🤖", "Quoi de neuf ?",
    "Je t'écoute !", "Hmm intéressant !", "Ah ouais ? Raconte !",
    "Mdr ! 😄", "Trop bien !", "Ah d'accord, je vois !", "Franchement ? Pas mal !",
    "Haha j'avoue !", "Carrément !", "OKOK je note 😎",
    "Mais oui bien sûr !", "Sérieux ?! Raconte plus !",
    "T'inquiète, je suis là pour toi mec.", "On fait comment alors ?",
    "Pas de souci, je gère !", "Tu peux compter sur moi !",
    "Honnêtement ? Je dirais oui.", "Mmm, bonne question... tu penses quoi toi ?",
]

# ─── Helper: économie ───
def get_balance(uid):
    d = load_json("economy.json")
    return d.get(str(uid), {"balance": 100, "last_daily": None, "last_work": None})

def set_balance(uid, data):
    d = load_json("economy.json")
    d[str(uid)] = data
    save_json("economy.json", d)

# ─── Helper: XP ───
def get_xp(uid, gid):
    d = load_json("levels.json")
    return d.get(f"{gid}_{uid}", {"xp": 0, "level": 0})

def set_xp(uid, gid, data):
    d = load_json("levels.json")
    d[f"{gid}_{uid}"] = data
    save_json("levels.json", d)

# ─── Helper: warnings ───
def get_warnings(gid, uid):
    d = load_json("warnings.json")
    return d.get(f"{gid}_{uid}", [])

def add_warning(gid, uid, reason, mod):
    d = load_json("warnings.json")
    key = f"{gid}_{uid}"
    if key not in d: d[key] = []
    d[key].append({"reason": reason, "mod": mod, "date": datetime.now().isoformat()})
    save_json("warnings.json", d)
    return len(d[key])

def clear_warnings(gid, uid):
    d = load_json("warnings.json")
    d[f"{gid}_{uid}"] = []
    save_json("warnings.json", d)

# ─── Helper: guild config ───
def get_guild_config(gid):
    d = load_json("guild_config.json")
    return d.get(str(gid), {
        "welcome_channel": None,
        "welcome_message": "Bienvenue {user} sur {server} ! 🎉",
        "goodbye_channel": None,
        "goodbye_message": "{user} a quitté le serveur. 👋",
        "autorole": None,
        "automod_enabled": False,
        "anti_link": False,
        
        "anti_spam": False,
        "log_channel": None,
        "muted_role": None,
        "xp_rewards": {},
        "yt_channels": [],
        "auto_messages": [],
        "restricted_channels": {},
    })

def set_guild_config(gid, config):
    d = load_json("guild_config.json")
    d[str(gid)] = config
    save_json("guild_config.json", d)

# ─── DM notification ───
async def notify_owner_restart():
    try:
        app_info = await bot.application_info()
        owner = app_info.owner
        embed = discord.Embed(
            title="⚠️ Bot redémarré",
            description=f"Salut {owner.name} ! J'ai été coupé et je viens de redémarrer.\n**Heure:** {START_TIME.strftime('%d/%m/%Y à %H:%M:%S')}\nJe suis de retour ✅",
            color=discord.Color.orange(),
        )
        embed.set_footer(text="Notification automatique")
        await owner.send(embed=embed)
        print(f"   📩 DM envoyé à {owner.name}")
    except Exception as e:
        print(f"   ❌ DM impossible: {e}")

# ═══════════════════════════════════════
# AUTO-MODÉRATION
# ═══════════════════════════════════════

async def check_automod(message):
    """Vérifie si un message viole les règles d'auto-modération."""
    if not message.guild or message.author.bot:
        return False
    config = get_guild_config(message.guild.id)
    if not config.get("automod_enabled"):
        return False
    
    content = message.content.lower()
    violated = False
    reason = ""
    
    # Anti-liens
    if not violated and config.get("anti_link"):
        links = LINK_REGEX.findall(message.content)
        for link in links:
            domain = re.sub(r'https?://(?:www\.)?', '', link).split('/')[0]
            if not any(wl in domain for wl in LINK_WHITELIST):
                violated = True
                reason = f"Lien non autorisé: {link}"
                break
    
    # Anti-spam: 20+ emojis en 1 minute = spam
    if not violated and config.get("anti_spam"):
        emoji_count = len(re.findall(r'[😀-🫿☀-➿🇠-🇿⬀-⯿]', message.content))
        if emoji_count >= 5:
            key = f"{message.guild.id}_{message.author.id}"
            spam_tracker = load_json("spam_tracker.json")
            now = datetime.now().timestamp()
            if key not in spam_tracker:
                spam_tracker[key] = []
            spam_tracker[key] = [t for t in spam_tracker[key] if now - t < 60]
            spam_tracker[key].append(now)
            save_json("spam_tracker.json", spam_tracker)
            if len(spam_tracker[key]) >= 20:
                violated = True
                reason = f"Spam d'emojis détecté ({len(spam_tracker[key])} emojis en moins de 60s)"
                spam_tracker[key] = []  # reset
                save_json("spam_tracker.json", spam_tracker)
    
    if violated:
        try:
            await message.delete()
            print(f"   🗑️ Message supprimé: {message.author} | {reason}")
        except discord.Forbidden:
            print(f"   ⚠️ Impossible de supprimer le message de {message.author} (permissions insuffisantes)")
            # Envoyer quand même l'avertissement même si on peut pas supprimer
        except Exception as e:
            print(f"   ❌ Erreur suppression: {e}")
        # Avertir (stocké en JSON pour persister)
        automod_warnings = load_json("automod_warnings.json")
        key = f"{message.guild.id}_{message.author.id}"
        if key not in automod_warnings:
            automod_warnings[key] = 0
        automod_warnings[key] += 1
        total = automod_warnings[key]
        save_json("automod_warnings.json", automod_warnings)
        
        embed = discord.Embed(
            title="⚠️ Auto-Modération",
            description=f"{message.author.mention}, ton message a été supprimé.\n**Raison:** {reason}\n**Avertissement:** {total}/3",
            color=discord.Color.orange(),
        )
        try:
            await message.channel.send(embed=embed, delete_after=10)
        except:
            pass
        
        # Log
        if config.get("log_channel"):
            try:
                log_ch = message.guild.get_channel(int(config["log_channel"]))
                if log_ch:
                    log_embed = discord.Embed(
                        title="🛡️ Auto-Mod — Action",
                        description=f"**User:** {message.author.mention}\n**Raison:** {reason}\n**Warn:** {total}/3\n**Message:** {message.content[:500]}",
                        color=discord.Color.red(),
                        timestamp=datetime.now(timezone.utc),
                    )
                    await log_ch.send(embed=log_embed)
            except:
                pass
        
        # Auto-mute après 3 avertissements
        if total >= 3:
            muted_role_id = config.get("muted_role")
            if muted_role_id:
                try:
                    muted_role = message.guild.get_role(int(muted_role_id))
                    if muted_role:
                        await message.author.add_roles(muted_role, reason=f"Auto-mod: 3 avertissements ({reason})")
                        embed = discord.Embed(
                            title="🔇 Auto-Mute",
                            description=f"{message.author.mention} a été muté automatiquement après 3 avertissements.",
                            color=discord.Color.dark_red(),
                        )
                        await message.channel.send(embed=embed)
                        if config.get("log_channel"):
                            log_ch = message.guild.get_channel(int(config["log_channel"]))
                            if log_ch:
                                await log_ch.send(embed=embed)
                        user_warnings[message.guild.id][message.author.id] = 0
                except:
                    pass
        return True
    return False

# ─── Restriction de salon (mute auto pour mauvais salon) ───
async def check_channel_restriction(message):
    if not message.guild or message.author.bot:
        return
    config = get_guild_config(message.guild.id)
    restricted = config.get("restricted_channels", {})
    ch_id = str(message.channel.id)
    if ch_id in restricted:
        rule = restricted[ch_id]
        # rule = {"allowed_topic": "gaming", "warning": "Ce salon est pour X, va dans Y"}
        warning = rule.get("warning", f"Ce salon est réservé à: {rule.get('allowed_topic', 'topic')}")
        warning_count = wrong_channel_warnings[message.guild.id][message.author.id]
        wrong_channel_warnings[message.guild.id][message.author.id] += 1
        total = wrong_channel_warnings[message.guild.id][message.author.id]
        
        if total <= 3:
            try:
                embed = discord.Embed(
                    title="⚠️ Mauvais salon",
                    description=f"{message.author.mention}, {warning}\n**Avertissement {total}/3** — après 3, c'est le mute !",
                    color=discord.Color.orange(),
                )
                await message.channel.send(embed=embed, delete_after=15)
            except:
                pass
        
        if total >= 3:
            muted_role_id = config.get("muted_role")
            if muted_role_id:
                try:
                    muted_role = message.guild.get_role(int(muted_role_id))
                    if muted_role:
                        await message.author.add_roles(muted_role, reason="Mute auto: 3 avertissements mauvais salon")
                        embed = discord.Embed(
                            title="🔇 Mute automatique",
                            description=f"{message.author.mention} a été muté après 3 avertissements pour mauvais salon.",
                            color=discord.Color.dark_red(),
                        )
                        await message.channel.send(embed=embed)
                        wrong_channel_warnings[message.guild.id][message.author.id] = 0
                except:
                    pass

# ═══════════════════════════════════════
# AUTO-MESSAGES (messages programmés)
# ═══════════════════════════════════════

async def send_auto_messages():
    """Boucle qui envoie les messages automatiques programmés."""
    await bot.wait_until_ready()
    await asyncio.sleep(10)  # Délai initial
    while not bot.is_closed():
        try:
            now = datetime.now(timezone.utc)
            for guild in bot.guilds:
                config = get_guild_config(guild.id)
                changed = False
                for am in config.get("auto_messages", []):
                    last_sent_str = am.get("last_sent")
                    # Calculer l'intervalle en secondes
                    mins = am.get("interval_minutes")
                    if mins is None:
                        mins = am.get("interval_hours", 1) * 60
                    interval_seconds = int(mins) * 60
                    # Vérifier si on doit envoyer
                    should_send = False
                    if not last_sent_str:
                        # Premier envoi: attendre un cycle complet avant d'envoyer
                        am["last_sent"] = now.isoformat()
                        changed = True
                    else:
                        try:
                            last = datetime.fromisoformat(last_sent_str)
                            if last.tzinfo is None:
                                last = last.replace(tzinfo=timezone.utc)
                            elapsed = (now - last).total_seconds()
                            if elapsed >= interval_seconds:
                                should_send = True
                        except:
                            should_send = True
                    if should_send:
                        ch = guild.get_channel(int(am["channel_id"]))
                        if ch:
                            try:
                                await ch.send(am["message"])
                                am["last_sent"] = now.isoformat()
                                changed = True
                            except Exception as e:
                                print(f"Erreur auto-message: {e}")
                if changed:
                    set_guild_config(guild.id, config)
        except Exception as e:
            print(f"Erreur boucle auto-messages: {e}")
        await asyncio.sleep(30)  # Vérifier toutes les 30s

# ═══════════════════════════════════════
# NOTIFICATIONS YOUTUBE
# ═══════════════════════════════════════

async def check_youtube():
    """Vérifie les nouvelles vidéos YouTube périodiquement."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            for guild in bot.guilds:
                config = get_guild_config(guild.id)
                for yt in config.get("yt_channels", []):
                    channel_id = yt.get("channel_id")
                    notify_channel = yt.get("notify_channel")
                    last_video = yt.get("last_video_id")
                    if not channel_id or not notify_channel:
                        continue
                    # RSS feed YouTube
                    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(rss_url) as resp:
                            if resp.status == 200:
                                text = await resp.text()
                                # Parser simple pour RSS
                                import xml.etree.ElementTree as ET
                                root = ET.fromstring(text)
                                entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                                if entries:
                                    latest = entries[0]
                                    video_id_elem = latest.find("{http://www.youtube.com/xml/schemas/2015}videoId")
                                    title_elem = latest.find("{http://www.w3.org/2005/Atom}title")
                                    if video_id_elem is not None and title_elem is not None:
                                        video_id = video_id_elem.text
                                        title = title_elem.text
                                        if video_id != last_video:
                                            yt["last_video_id"] = video_id
                                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                                            ch = guild.get_channel(int(notify_channel))
                                            if ch:
                                                embed = discord.Embed(
                                                    title="🎬 Nouvelle vidéo YouTube !",
                                                    description=f"**{title}**\n{video_url}",
                                                    color=discord.Color.red(),
                                                )
                                                embed.set_footer(text=f"Chaîne: {yt.get('name', 'YouTube')}")
                                                try:
                                                    await ch.send(embed=embed)
                                                except:
                                                    pass
                    set_guild_config(guild.id, config)
        except:
            pass
        await asyncio.sleep(300)  # Check every 5 min

# ═══════════════════════════════════════
# ÉVÉNEMENTS
# ═══════════════════════════════════════



async def heartbeat_check():
    """Vérifie que le bot est connecté et reconnecte si besoin."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            if bot.is_ws_ratelimited():
                print("⚠️ WebSocket ratelimited, attente...")
            if not bot.is_ready():
                print("⚠️ Bot pas prêt, reconnexion...")
        except:
            pass
        await asyncio.sleep(60)

@bot.event
async def on_error(event, *args, **kwargs):
    """Capture TOUTES les erreurs non gérées pour empêcher le crash."""
    import traceback
    print(f"⚠️ Erreur dans l'événement '{event}':")
    traceback.print_exc()
    # Ne jamais crasher — juste logger

@bot.event
async def on_ready():
    print(f"✅ {bot.user} en ligne !")
    print(f"   🔒 Anti-crash: ON | Reconnexion auto: ON")
    print(f"   ID: {bot.user.id}")
    print(f"   Serveurs: {len(bot.guilds)}")
    try:
        synced = await bot.tree.sync()
        print(f"   {len(synced)} slash commands.")
    except Exception as e:
        print(f"   Erreur sync: {e}")
    # Enregistrer les vues persistantes (tickets)
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())
    print("   🎫 Vues de tickets enregistrées.")
    bot.loop.create_task(heartbeat_check())
    if IS_RESTART:
        print("   🔄 Redémarrage — notification...")
        await notify_owner_restart()
    
    # ─── Activer l'automod par défaut sur tous les serveurs ───
    for guild in bot.guilds:
        d = load_json("guild_config.json")
        gid = str(guild.id)
        if gid not in d:
            d[gid] = {}
        # Toujours activer l'automod (ne pas laisser disabled)
        if not d[gid].get("automod_enabled"):
            d[gid]["automod_enabled"] = True
        if "anti_spam" not in d[gid]:
            d[gid]["anti_spam"] = True
        if "anti_link" not in d[gid]:
            d[gid]["anti_link"] = False
        if "welcome_message" not in d[gid]:
            d[gid]["welcome_message"] = "Bienvenue {user} sur {server} ! 🎉"
        save_json("guild_config.json", d)
        print(f"   ⚙️ Config init: {guild.name} | automod={d[gid]['automod_enabled']} spam={d[gid].get('anti_spam')} ")
    else:
        print("   🟢 Premier démarrage.")
    # Démarrer les tâches de fond
    bot.loop.create_task(send_auto_messages())
    bot.loop.create_task(check_youtube())

@bot.event
async def on_message(message):
    try:
        await _on_message_inner(message)
    except Exception as e:
        print(f"❌ on_message crash évité: {e}")
        try:
            if not message.author.bot:
                await message.reply("❌ Une erreur est survenue.", delete_after=5)
        except:
            pass

async def _on_message_inner(message):
    # === DM HANDLER: le bot discute en privé ===
    if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
        msg_lower = message.content.lower()
        # Réponses contextuelles simples
        if any(w in msg_lower for w in ["bonjour", "salut", "hey", "coucou", "yo", "cc"]):
            await message.reply(f"Salut {message.author.name} ! 👋 Comment ça va ?")
        elif any(w in msg_lower for w in ["ça va", "ca va", "comment vas", "comment tu vas"]):
            await message.reply("Ça va super bien, merci ! Et toi ? 😄")
        elif any(w in msg_lower for w in ["bien", "super", "cool", "génial", "nickel"]):
            await message.reply("Trop bien ! Content de l'entendre ! 🎉")
        elif any(w in msg_lower for w in ["mal", "pas bien", "nul", "fatigué", "déprimé", "deprimé", "triste"]):
            await message.reply("Oh non... 😔 Tu veux en parler ? Je suis là pour toi mec.")
        elif any(w in msg_lower for w in ["merci", "thanks", "cimer"]):
            await message.reply("De rien ! Toujours là pour toi ! 🤖💙")
        elif any(w in msg_lower for w in ["aide", "help", "commandes", "commande"]):
            await message.reply("Va sur le serveur et tape `/help` pour voir toutes mes commandes ! 📖")
        elif any(w in msg_lower for w in ["au revoir", "bye", "ciao", "à plus", "a plus", "tchao"]):
            await message.reply("À bientôt ! 👋 Repasse quand tu veux !")
        elif "?" in message.content:
            await message.reply(random.choice([
                "Bonne question ! 🤔 Qu'est-ce que tu en penses toi ?",
                "Hmm... laisse-moi réfléchir. Je dirais que ça dépend !",
                "Franchement, je dirais oui ! Tu penses quoi ?",
                "Je ne suis pas sûr mais je dirais que oui !",
                "Excellente question ! Tu devrais essayer et voir !",
            ]))
        else:
            await message.reply(random.choice(DM_RESPONSES))
        return

    # === Auto-modération ===
    if message.guild and not message.author.bot:
        mod_violated = await check_automod(message)
        if mod_violated:
            return
        await check_channel_restriction(message)
    
    # === CHAT: le bot répond quand on le mentionne dans le serveur ===
    if message.guild and not message.author.bot and bot.user in message.mentions:
        msg_lower = message.content.lower()
        # Nettoyer la mention du message
        clean_msg = re.sub(r'<@!?\d+>', '', message.content).strip()
        if any(w in msg_lower for w in ["bonjour", "salut", "hey", "coucou", "yo", "cc"]):
            await message.reply(f"Salut {message.author.name} ! 👋 Comment ça va ?")
        elif any(w in msg_lower for w in ["ça va", "ca va", "comment vas", "comment tu vas"]):
            await message.reply("Ça va super bien, merci ! Et toi ? 😄")
        elif any(w in msg_lower for w in ["bien", "super", "cool", "génial", "nickel"]):
            await message.reply("Trop bien ! Content de l'entendre ! 🎉")
        elif any(w in msg_lower for w in ["mal", "pas bien", "nul", "fatigué", "déprimé", "deprimé", "triste"]):
            await message.reply("Oh non... 😔 Tu veux en parler ? Je suis là pour toi mec.")
        elif any(w in msg_lower for w in ["merci", "thanks", "cimer"]):
            await message.reply("De rien ! Toujours là pour toi ! 🤖💙")
        elif any(w in msg_lower for w in ["aide", "help", "commandes", "commande"]):
            await message.reply("Tape `/help` pour voir toutes mes commandes ! 📖")
        elif any(w in msg_lower for w in ["au revoir", "bye", "ciao", "à plus", "a plus", "tchao"]):
            await message.reply("À bientôt ! 👋")
        elif "?" in clean_msg:
            await message.reply(random.choice([
                "Bonne question ! 🤔 Qu'est-ce que tu en penses ?",
                "Hmm... laisse-moi réfléchir. Je dirais que ça dépend !",
                "Franchement, je dirais oui ! Tu penses quoi ?",
                "Je ne suis pas sûr mais je dirais que oui !",
                "Excellente question ! Tu devrais essayer et voir !",
            ]))
        elif clean_msg:
            await message.reply(random.choice(DM_RESPONSES))
        return
    
    # === XP system ===
    if not message.author.bot and message.guild:
        uid, gid = message.author.id, message.guild.id
        xp_data = get_xp(uid, gid)
        xp_data["xp"] += 1  # 1 XP par message
        xp_needed = 100  # 100 messages = 1 niveau
        if xp_data["xp"] >= xp_needed:
            xp_data["level"] += 1
            xp_data["xp"] -= 100
            config = get_guild_config(gid)
            # Role reward
            rewards = config.get("xp_rewards", {})
            if str(xp_data["level"]) in rewards:
                role_id = rewards[str(xp_data["level"])]
                try:
                    role = message.guild.get_role(int(role_id))
                    if role and role not in message.author.roles:
                        await message.author.add_roles(role)
                except:
                    pass
            
            # === Creer / utiliser le salon XP (lecture seule) ===
            xp_channel_id = config.get("xp_channel")
            xp_channel = None
            
            # Verifier si le salon existe
            if xp_channel_id:
                try:
                    xp_channel = message.guild.get_channel(int(xp_channel_id))
                except:
                    xp_channel = None
            
            # Creer le salon automatiquement s'il n'existe pas
            if not xp_channel:
                try:
                    overwrites = {
                        message.guild.default_role: discord.PermissionOverwrite(
                            send_messages=False,
                            send_messages_in_threads=False,
                            create_public_threads=False,
                            add_reactions=True,
                            read_messages=True,
                            view_channel=True,
                        ),
                        message.guild.me: discord.PermissionOverwrite(
                            send_messages=True,
                            manage_messages=True,
                            read_messages=True,
                            view_channel=True,
                        ),
                    }
                    # Donner acces aux admins
                    for role in message.guild.roles:
                        if role.permissions.manage_guild:
                            overwrites[role] = discord.PermissionOverwrite(
                                send_messages=True, manage_messages=True, read_messages=True
                            )
                    
                    xp_channel = await message.guild.create_text_channel(
                        name="📊-niveaux-xp",
                        overwrites=overwrites,
                        topic="Salon automatique - Annonces de niveaux XP (lecture seule)",
                        reason="Creation auto du salon XP"
                    )
                    config["xp_channel"] = str(xp_channel.id)
                    set_guild_config(gid, config)
                    
                    # Message d'accueil
                    welcome_embed = discord.Embed(
                        title="📊 Salon des Niveaux XP",
                        description=(
                            "Ce salon est **automatique** et en **lecture seule**.\n"
                            "Vous ne pouvez pas envoyer de messages ici.\n\n"
                            "Chaque fois qu'un membre gagne un niveau, une annonce s'affiche ici !\n"
                            "Utilisez `/rank` pour voir votre niveau et votre XP."
                        ),
                        color=discord.Color.blue(),
                    )
                    welcome_embed.set_footer(text="Bot Discord - Systeme XP")
                    await xp_channel.send(embed=welcome_embed)
                except Exception as e:
                    print(f"Erreur creation salon XP: {e}")
            
            # Annonce de niveau dans le salon XP
            if xp_channel:
                try:
                    embed = discord.Embed(
                        title="📈 NIVEAU SUPÉRIEUR !",
                        description=(
                            f"🎉 **{message.author.display_name}** vient d'atteindre le **niveau {xp_data['level']}** !\n"
                            f"XP total: **{xp_data['xp']}** / 100\n"
                            f"Membre: {message.author.mention}"
                        ),
                        color=discord.Color.gold(),
                    )
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    embed.set_footer(text=f"Niveau {xp_data['level']} • {message.author.name}")
                    await xp_channel.send(embed=embed)
                except:
                    pass
            
            # Annonce courte dans le salon original (auto-supprime)
            try:
                embed = discord.Embed(
                    title="📈 Niveau supérieur !",
                    description=f"GG {message.author.mention} ! Tu es niveau **{xp_data['level']}** 🎉",
                    color=discord.Color.gold(),
                )
                await message.channel.send(embed=embed, delete_after=10)
            except:
                pass
        set_xp(uid, gid, xp_data)
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    try:
        if not message.author.bot:
            sniped_messages[message.channel.id] = {
                "content": message.content, "author": message.author, "time": datetime.now(),
            }
    except Exception as e:
        print(f"⚠️ on_message_delete erreur: {e}")

@bot.event
async def on_message_edit(before, after):
    try:
        if not before.author.bot and before.content != after.content:
            edited_messages[before.channel.id] = {
                "before": before.content, "after": after.content,
                "author": before.author, "time": datetime.now(),
            }
    except Exception as e:
        print(f"⚠️ on_message_edit erreur: {e}")
@bot.event
async def on_member_join(member):
    config = get_guild_config(member.guild.id)
    welcome_msg = config.get("welcome_message", "Bienvenue {user} sur {server} ! 🎉")
    welcome_msg = welcome_msg.replace("{user}", member.mention).replace("{server}", member.guild.name).replace("{username}", member.name)
    ch_id = config.get("welcome_channel")
    # N'envoyer le message que si un salon de bienvenue est explicitement configuré
    # PAS de fallback sur le salon système pour éviter les doublons
    if ch_id:
        try:
            ch = member.guild.get_channel(int(ch_id))
            if ch:
                embed = discord.Embed(
                    title="🎉 Bienvenue !",
                    description=welcome_msg,
                    color=discord.Color.green(),
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Nous sommes maintenant {member.guild.member_count} membres.")
                await ch.send(embed=embed)
        except Exception as e:
            print(f"Erreur bienvenue: {e}")
    # Auto-role
    autorole_id = config.get("autorole")
    if autorole_id:
        try:
            role = member.guild.get_role(int(autorole_id))
            if role:
                await member.add_roles(role, reason="Auto-role")
        except:
            pass

@bot.event
async def on_member_remove(member):
    config = get_guild_config(member.guild.id)
    goodbye_msg = config.get("goodbye_message", "{user} a quitté le serveur. 👋")
    goodbye_msg = goodbye_msg.replace("{user}", member.name).replace("{server}", member.guild.name)
    ch_id = config.get("goodbye_channel") or config.get("welcome_channel")
    if ch_id:
        try:
            ch = member.guild.get_channel(int(ch_id))
            if ch:
                embed = discord.Embed(
                    title="👋 Au revoir",
                    description=goodbye_msg,
                    color=discord.Color.red(),
                )
                await ch.send(embed=embed)
        except:
            pass

# ═══════════════════════════════════════
# MUSIQUE
# ═══════════════════════════════════════

import yt_dlp

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extractaudio': True,
    'noplaylist': True,
}

async def search_youtube(query):
    """Cherche une vidéo YouTube et retourne le titre et l'URL audio."""
    ydl = yt_dlp.YoutubeDL(YDL_OPTIONS)
    loop = asyncio.get_event_loop()
    
    def extract():
        if query.startswith("http"):
            info = ydl.extract_info(query, download=False)
        else:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in info:
                info = info['entries'][0]
        return info
    
    info = await loop.run_in_executor(None, extract)
    return {
        'title': info.get('title', 'Inconnu'),
        'url': info['url'],
        'webpage_url': info.get('webpage_url', ''),
        'duration': info.get('duration', 0),
        'uploader': info.get('uploader', 'Inconnu'),
    }

async def play_next(ctx_or_interaction, guild_id):
    """Joue la prochaine chanson dans la queue."""
    if not music_queues[guild_id]:
        now_playing.pop(guild_id, None)
        vc = discord.utils.get(bot.voice_clients, guild__id=guild_id)
        if vc:
            await vc.disconnect()
        return
    
    song = music_queues[guild_id].pop(0)
    now_playing[guild_id] = song
    vc = discord.utils.get(bot.voice_clients, guild__id=guild_id)
    
    if not vc:
        return
    
    source = discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS)
    
    def after_play(error):
        if error:
            print(f"Erreur playback: {error}")
        asyncio.run_coroutine_threadsafe(play_next(None, guild_id), bot.loop)
    
    vc.play(source, after=after_play)
    
    # Notifier
    try:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{song['title']}**\nPar: {song['uploader']}",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Durée: {song['duration']//60}:{song['duration']%60:02d}")
        if ctx_or_interaction and hasattr(ctx_or_interaction, 'channel'):
            await ctx_or_interaction.channel.send(embed=embed)
    except:
        pass

@bot.tree.command(name="play", description="Joue une musique depuis YouTube.")
@app_commands.describe(requete="Titre ou URL YouTube.")
async def play(interaction: discord.Interaction, requete: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Tu dois être dans un salon vocal.", ephemeral=True)
        return
    
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()
    
    await interaction.response.defer()
    try:
        song = await search_youtube(requete)
        music_queues[interaction.guild.id].append(song)
        
        if vc.is_playing() or vc.is_paused():
            embed = discord.Embed(
                title="✅ Ajouté à la queue",
                description=f"**{song['title']}**\nPar: {song['uploader']}",
                color=discord.Color.blue(),
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"🎵 Lecture de: **{song['title']}**")
            await play_next(interaction, interaction.guild.id)
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur: {e}")

@bot.tree.command(name="skip", description="Passe à la chanson suivante.")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        await interaction.response.send_message("❌ Rien n'est en train de jouer.")
        return
    vc.stop()
    await interaction.response.send_message("⏭️ Chanson suivante...")

@bot.tree.command(name="stop", description="Arrête la musique et déconnecte.")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        await interaction.response.send_message("❌ Je ne suis pas en vocal.")
        return
    music_queues[interaction.guild.id].clear()
    now_playing.pop(interaction.guild.id, None)
    await vc.disconnect()
    await interaction.response.send_message("⏹️ Musique arrêtée et déconnecté.")

@bot.tree.command(name="queue", description="Affiche la file d'attente.")
async def queue(interaction: discord.Interaction):
    q = music_queues[interaction.guild.id]
    np_song = now_playing.get(interaction.guild.id)
    if not q and not np_song:
        await interaction.response.send_message("📭 La file d'attente est vide.")
        return
    embed = discord.Embed(title="🎵 File d'attente", color=discord.Color.blue())
    if np_song:
        embed.add_field(name="▶️ En cours", value=f"**{np_song['title']}**", inline=False)
    if q:
        desc = "\n".join(f"{i+1}. **{s['title']}**" for i, s in enumerate(q[:10]))
        embed.add_field(name=f"📋 À venir ({len(q)})", value=desc, inline=False)
    else:
        embed.add_field(name="📋 À venir", value="Vide", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="Affiche la chanson en cours.")
async def nowplaying(interaction: discord.Interaction):
    song = now_playing.get(interaction.guild.id)
    if not song:
        await interaction.response.send_message("❌ Rien ne joue actuellement.")
        return
    embed = discord.Embed(title="🎵 En cours", description=f"**{song['title']}**\nPar: {song['uploader']}", color=discord.Color.green())
    embed.set_footer(text=f"Durée: {song['duration']//60}:{song['duration']%60:02d}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pause", description="Met en pause.")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        await interaction.response.send_message("❌ Rien ne joue.")
        return
    vc.pause()
    await interaction.response.send_message("⏸️ En pause.")

@bot.tree.command(name="resume", description="Reprend la musique.")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_paused():
        await interaction.response.send_message("❌ Pas en pause.")
        return
    vc.resume()
    await interaction.response.send_message("▶️ Reprise.")

@bot.tree.command(name="join", description="Rejoint ton salon vocal.")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Tu dois être en vocal.", ephemeral=True)
        return
    vc = interaction.guild.voice_client
    if vc:
        await vc.move_to(interaction.user.voice.channel)
    else:
        await interaction.user.voice.channel.connect()
    await interaction.response.send_message(f"✅ Connecté à **{interaction.user.voice.channel.name}**")

@bot.tree.command(name="leave", description="Quitte le salon vocal.")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        await interaction.response.send_message("❌ Je ne suis pas en vocal.")
        return
    music_queues[interaction.guild.id].clear()
    now_playing.pop(interaction.guild.id, None)
    await vc.disconnect()
    await interaction.response.send_message("👋 Déconnecté.")

# ═══════════════════════════════════════
# MODÉRATION
# ═══════════════════════════════════════

@bot.tree.command(name="ping", description="Affiche la latence.")
async def ping(interaction: discord.Interaction):
    ms = round(bot.latency * 1000)
    color = discord.Color.green() if ms < 200 else discord.Color.orange()
    embed = discord.Embed(title="🏓 Pong !", description=f"Latence: **{ms} ms**", color=color)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear", description="Supprime des messages.")
@app_commands.describe(nombre="Nombre (1-100).")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int):
    if nombre < 1 or nombre > 100:
        await interaction.response.send_message("❌ Entre 1 et 100.", ephemeral=True)
        return
    deleted = await interaction.channel.purge(limit=nombre)
    embed = discord.Embed(title="🧹 Supprimés", description=f"**{len(deleted)}** messages.", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="kick", description="Expulse un membre.")
@app_commands.describe(membre="Le membre.", raison="La raison.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune"):
    if membre.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ Tu ne peux pas.", ephemeral=True)
        return
    try: await membre.send(f"🦶 Expulsé de **{interaction.guild.name}**. Raison: {raison}")
    except: pass
    await membre.kick(reason=raison)
    embed = discord.Embed(title="🦶 Expulsion", description=f"{membre.mention} expulsé.\n**Raison:** {raison}", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ban", description="Bannit un membre.")
@app_commands.describe(membre="Le membre.", raison="La raison.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune"):
    if membre.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ Tu ne peux pas.", ephemeral=True)
        return
    try: await membre.send(f"🔨 Banni de **{interaction.guild.name}**. Raison: {raison}")
    except: pass
    await membre.ban(reason=raison)
    embed = discord.Embed(title="🔨 Bannissement", description=f"{membre.mention} banni.\n**Raison:** {raison}", color=discord.Color.dark_red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unban", description="Débannit.")
@app_commands.describe(user_id="L'ID.")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.name} débanni.")
    except Exception as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout un membre.")
@app_commands.describe(membre="Le membre.", duree="Minutes.", raison="La raison.")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, membre: discord.Member, duree: int, raison: str = "Aucune"):
    if membre.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ Tu ne peux pas.", ephemeral=True)
        return
    await membre.timeout(timedelta(minutes=duree), reason=raison)
    embed = discord.Embed(title="⏱️ Timeout", description=f"{membre.mention}: **{duree} min**.\n**Raison:** {raison}", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="untimeout", description="Retire le timeout.")
@app_commands.describe(membre="Le membre.")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, membre: discord.Member):
    await membre.timeout(None)
    embed = discord.Embed(title="✅ Timeout retiré", description=f"{membre.mention} libéré.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warn", description="Avertit un membre.")
@app_commands.describe(membre="Le membre.", raison="La raison.")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    count = add_warning(interaction.guild.id, membre.id, raison, interaction.user.name)
    try: await membre.send(f"⚠️ Avertissement sur **{interaction.guild.name}**.\nRaison: {raison}\nTotal: {count}")
    except: pass
    embed = discord.Embed(title="⚠️ Avertissement", description=f"{membre.mention} averti.\n**Raison:** {raison}\n**Total:** {count}", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warnings", description="Voir les avertissements.")
@app_commands.describe(membre="Le membre.")
@app_commands.checks.has_permissions(manage_messages=True)
async def warnings(interaction: discord.Interaction, membre: discord.Member):
    warns = get_warnings(interaction.guild.id, membre.id)
    if not warns:
        await interaction.response.send_message(f"✅ {membre.mention} n'a aucun avertissement.")
        return
    embed = discord.Embed(title=f"Avertissements de {membre.name}", color=discord.Color.orange())
    for i, w in enumerate(warns, 1):
        embed.add_field(name=f"#{i} — {w['date'][:10]}", value=f"**Raison:** {w['reason']}\n**Mod:** {w['mod']}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clearwarnings", description="Supprime les avertissements.")
@app_commands.describe(membre="Le membre.")
@app_commands.checks.has_permissions(manage_messages=True)
async def clearwarnings(interaction: discord.Interaction, membre: discord.Member):
    clear_warnings(interaction.guild.id, membre.id)
    await interaction.response.send_message(f"✅ Avertissements de {membre.mention} supprimés.")

@bot.tree.command(name="slowmode", description="Active le slowmode.")
@app_commands.describe(duree="Secondes (0 = off).")
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, duree: int):
    await interaction.channel.edit(slowmode_delay=duree)
    await interaction.response.send_message(f"✅ Slowmode: **{duree}s**" if duree else "✅ Slowmode off.")

@bot.tree.command(name="lock", description="Verrouille le salon.")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 Salon verrouillé.")

@bot.tree.command(name="unlock", description="Déverrouille le salon.")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 Salon déverrouillé.")

@bot.tree.command(name="nickname", description="Change un surnom.")
@app_commands.describe(membre="Le membre.", surnom="Le surnom.")
@app_commands.checks.has_permissions(manage_nicknames=True)
async def nickname(interaction: discord.Interaction, membre: discord.Member, surnom: str):
    try:
        await membre.edit(nick=surnom)
        await interaction.response.send_message(f"✅ Surnom changé: **{surnom}**")
    except Exception as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

@bot.tree.command(name="snipe", description="Dernier message supprimé.")
async def snipe(interaction: discord.Interaction):
    sniped = sniped_messages.get(interaction.channel.id)
    if not sniped:
        await interaction.response.send_message("❌ Aucun message supprimé.")
        return
    embed = discord.Embed(description=sniped["content"], color=discord.Color.red(), timestamp=sniped["time"])
    embed.set_author(name=sniped["author"].name, icon_url=sniped["author"].display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsnipe", description="Dernier message édité.")
async def editsnipe(interaction: discord.Interaction):
    sniped = edited_messages.get(interaction.channel.id)
    if not sniped:
        await interaction.response.send_message("❌ Aucun message édité.")
        return
    embed = discord.Embed(title="📝 Édité", color=discord.Color.orange(), timestamp=sniped["time"])
    embed.add_field(name="Avant", value=sniped["before"][:1024] or "*vide*", inline=False)
    embed.add_field(name="Après", value=sniped["after"][:1024] or "*vide*", inline=False)
    embed.set_author(name=sniped["author"].name, icon_url=sniped["author"].display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="role", description="Donne/retire un rôle.")
@app_commands.describe(membre="Le membre.", role="Le rôle.")
@app_commands.checks.has_permissions(manage_roles=True)
async def role(interaction: discord.Interaction, membre: discord.Member, role: discord.Role):
    if role in membre.roles:
        await membre.remove_roles(role)
        await interaction.response.send_message(f"✅ Rôle {role.mention} retiré de {membre.mention}.")
    else:
        await membre.add_roles(role)
        await interaction.response.send_message(f"✅ Rôle {role.mention} ajouté à {membre.mention}.")

# ═══════════════════════════════════════
# CONFIG: WELCOME / GOODBYE / AUTOROLE
# ═══════════════════════════════════════

@bot.tree.command(name="setwelcome", description="Configure le salon de bienvenue.")
@app_commands.describe(channel="Le salon où le bot accueillera les nouveaux membres.")
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    config = get_guild_config(interaction.guild.id)
    config["welcome_channel"] = str(channel.id)
    set_guild_config(interaction.guild.id, config)
    embed = discord.Embed(title="✅ Bienvenue configuré", description=f"Les nouveaux membres seront accueillis dans {channel.mention}.\n\nLe bot enverra automatiquement un message de bienvenue quand quelqu'un rejoint !", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setgoodbye", description="Configure le message de départ.")
@app_commands.describe(channel="Le salon.", message="Le message ({user}, {server}).")
async def setgoodbye(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    config = get_guild_config(interaction.guild.id)
    config["goodbye_channel"] = str(channel.id)
    config["goodbye_message"] = message
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Message de départ configuré dans {channel.mention}.")

@bot.tree.command(name="setautorole", description="Configure le rôle automatique.")
@app_commands.describe(role="Le rôle à donner aux nouveaux membres.")
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    config = get_guild_config(interaction.guild.id)
    config["autorole"] = str(role.id)
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Auto-rôle configuré: {role.mention}")

@bot.tree.command(name="removeautorole", description="Désactive l'auto-rôle.")
async def removeautorole(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    config = get_guild_config(interaction.guild.id)
    config["autorole"] = None
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message("✅ Auto-rôle désactivé.")

# ═══════════════════════════════════════
# CONFIG: AUTO-MODÉRATION
# ═══════════════════════════════════════

@bot.tree.command(name="automod-enable", description="Active l'auto-modération.")
async def automod_enable(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    try:
        config = get_guild_config(interaction.guild.id)
        config["automod_enabled"] = True
        set_guild_config(interaction.guild.id, config)
        embed = discord.Embed(title="✅ Auto-Mod activé", description="L'auto-modération est active !", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)

@bot.tree.command(name="automod-disable", description="Désactive l'auto-modération.")
async def automod_disable(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    try:
        config = get_guild_config(interaction.guild.id)
        config["automod_enabled"] = False
        set_guild_config(interaction.guild.id, config)
        await interaction.response.send_message("✅ Auto-Mod désactivé.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)

@bot.tree.command(name="anti-link", description="Active/désactive l'anti-liens.")
@app_commands.describe(active="Activer ou non.")
async def anti_link(interaction: discord.Interaction, active: bool):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    try:
        config = get_guild_config(interaction.guild.id)
        config["anti_link"] = active
        set_guild_config(interaction.guild.id, config)
        await interaction.response.send_message(f"✅ Anti-liens: **{'activé' if active else 'désactivé'}**.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)

@bot.tree.command(name="anti-spam", description="Active/désactive l'anti-spam.")
@app_commands.describe(active="Activer ou non.")
async def anti_spam(interaction: discord.Interaction, active: bool):
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu as besoin de la permission **Gérer le serveur**.", ephemeral=True)
        return
    try:
        config = get_guild_config(interaction.guild.id)
        config["anti_spam"] = active
        set_guild_config(interaction.guild.id, config)
        await interaction.response.send_message(f"✅ Anti-spam: **{'activé' if active else 'désactivé'}**.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)

@bot.tree.command(name="set-muted-role", description="Définit le rôle 'muted'.")
@app_commands.describe(role="Le rôle.")
@app_commands.checks.has_permissions(manage_guild=True)
async def set_muted_role(interaction: discord.Interaction, role: discord.Role):
    config = get_guild_config(interaction.guild.id)
    config["muted_role"] = str(role.id)
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Rôle muted: {role.mention}")

@bot.tree.command(name="set-log-channel", description="Définit le salon de logs.")
@app_commands.describe(channel="Le salon de logs.")
@app_commands.checks.has_permissions(manage_guild=True)
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_guild_config(interaction.guild.id)
    config["log_channel"] = str(channel.id)
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Salon de logs: {channel.mention}")

@bot.tree.command(name="restrict-channel", description="Restreint un salon (mute auto si hors-sujet).")
@app_commands.describe(channel="Le salon.", sujet="Le sujet autorisé.", warning="Message d'avertissement (optionnel).")
@app_commands.checks.has_permissions(manage_guild=True)
async def restrict_channel(interaction: discord.Interaction, channel: discord.TextChannel, sujet: str, warning: str = ""):
    config = get_guild_config(interaction.guild.id)
    config["restricted_channels"][str(channel.id)] = {
        "allowed_topic": sujet,
        "warning": warning or f"⚠️ Ce salon est réservé à: {sujet}. 3 avertissements = mute !",
    }
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Salon {channel.mention} restreint: **{sujet}**.\n3 avertissements = mute auto.")

@bot.tree.command(name="unrestrict-channel", description="Lève la restriction.")
@app_commands.describe(channel="Le salon.")
@app_commands.checks.has_permissions(manage_guild=True)
async def unrestrict_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_guild_config(interaction.guild.id)
    config["restricted_channels"].pop(str(channel.id), None)
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Restriction levée: {channel.mention}.")

# ═══════════════════════════════════════
# CONFIG: AUTO-MESSAGES
# ═══════════════════════════════════════


@bot.tree.command(name="auto-message", description="Programme un message automatique (en minutes).")
@app_commands.describe(channel="Le salon.", interval_minutes="Intervalle en minutes (ex: 3 pour 3 min).", message="Le message.")
@app_commands.checks.has_permissions(manage_guild=True)
async def auto_message(interaction: discord.Interaction, channel: discord.TextChannel, interval_minutes: int, message: str):
    config = get_guild_config(interaction.guild.id)
    config["auto_messages"].append({"channel_id": str(channel.id), "interval_minutes": interval_minutes, "message": message, "last_sent": None})
    set_guild_config(interaction.guild.id, config)
    embed = discord.Embed(title="✅ Message auto", description=f"**Salon:** {channel.mention}\n**Intervalle:** {interval_minutes} min\n**Message:** {message}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="auto-message-list", description="Liste les messages auto.")
@app_commands.checks.has_permissions(manage_guild=True)
async def auto_message_list(interaction: discord.Interaction):
    config = get_guild_config(interaction.guild.id)
    msgs = config.get("auto_messages", [])
    if not msgs:
        await interaction.response.send_message("❌ Aucun message auto.")
        return
    embed = discord.Embed(title="📋 Messages auto", color=discord.Color.blue())
    for i, am in enumerate(msgs):
        ch = interaction.guild.get_channel(int(am["channel_id"]))
        mins = am.get("interval_minutes", am.get("interval_hours", 1) * 60)
        embed.add_field(name=f"#{i+1} — {ch.mention if ch else '?'}", value=f"⏰ {mins} min\n💬 {am['message'][:200]}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="auto-message-remove", description="Supprime un message auto.")
@app_commands.describe(index="Le numéro.")
@app_commands.checks.has_permissions(manage_guild=True)
async def auto_message_remove(interaction: discord.Interaction, index: int):
    config = get_guild_config(interaction.guild.id)
    msgs = config.get("auto_messages", [])
    if index < 1 or index > len(msgs):
        await interaction.response.send_message("❌ Index invalide.", ephemeral=True)
        return
    msgs.pop(index - 1)
    config["auto_messages"] = msgs
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Message auto #{index} supprimé.")

# ═══════════════════════════════════════
# CONFIG: NOTIFICATIONS YOUTUBE
# ═══════════════════════════════════════

@bot.tree.command(name="yt-notify", description="Active les notifications YouTube.")
@app_commands.describe(channel_id="ID chaîne YouTube.", notify_channel="Salon Discord.", name="Nom (optionnel).")
@app_commands.checks.has_permissions(manage_guild=True)
async def yt_notify(interaction: discord.Interaction, channel_id: str, notify_channel: discord.TextChannel, name: str = "YouTube"):
    config = get_guild_config(interaction.guild.id)
    config["yt_channels"].append({"channel_id": channel_id, "notify_channel": str(notify_channel.id), "name": name, "last_video_id": None})
    set_guild_config(interaction.guild.id, config)
    embed = discord.Embed(title="✅ Notifications YT", description=f"**Chaîne:** {name}\n**Salon:** {notify_channel.mention}\nVérif toutes les 5 min.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="yt-notify-list", description="Liste les chaînes YT suivies.")
@app_commands.checks.has_permissions(manage_guild=True)
async def yt_notify_list(interaction: discord.Interaction):
    config = get_guild_config(interaction.guild.id)
    yts = config.get("yt_channels", [])
    if not yts:
        await interaction.response.send_message("❌ Aucune chaîne.")
        return
    embed = discord.Embed(title="🎬 Chaînes YT", color=discord.Color.red())
    for i, yt in enumerate(yts):
        ch = interaction.guild.get_channel(int(yt["notify_channel"]))
        embed.add_field(name=f"#{i+1} — {yt['name']}", value=f"**ID:** `{yt['channel_id']}`\n**Salon:** {ch.mention if ch else '?'}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="yt-notify-remove", description="Supprime une chaîne YT.")
@app_commands.describe(index="Le numéro.")
@app_commands.checks.has_permissions(manage_guild=True)
async def yt_notify_remove(interaction: discord.Interaction, index: int):
    config = get_guild_config(interaction.guild.id)
    yts = config.get("yt_channels", [])
    if index < 1 or index > len(yts):
        await interaction.response.send_message("❌ Index invalide.", ephemeral=True)
        return
    yts.pop(index - 1)
    config["yt_channels"] = yts
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Chaîne YT #{index} supprimée.")

# ═══════════════════════════════════════
# CONFIG: XP REWARDS
# ═══════════════════════════════════════

@bot.tree.command(name="xp-reward", description="Définit un rôle reward pour un niveau.")
@app_commands.describe(level="Le niveau.", role="Le rôle.")
@app_commands.checks.has_permissions(manage_guild=True)
async def xp_reward(interaction: discord.Interaction, level: int, role: discord.Role):
    config = get_guild_config(interaction.guild.id)
    config["xp_rewards"][str(level)] = str(role.id)
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Niveau **{level}** → Rôle {role.mention}")

@bot.tree.command(name="xp-reward-remove", description="Supprime un reward.")
@app_commands.describe(level="Le niveau.")
@app_commands.checks.has_permissions(manage_guild=True)
async def xp_reward_remove(interaction: discord.Interaction, level: int):
    config = get_guild_config(interaction.guild.id)
    config["xp_rewards"].pop(str(level), None)
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message(f"✅ Reward niveau {level} supprimé.")

@bot.tree.command(name="set-xp-channel", description="Définit le salon d'annonces XP (lecture seule auto).")
@app_commands.describe(channel="Le salon à utiliser (laisser vide pour auto-créer).")
@app_commands.checks.has_permissions(manage_guild=True)
async def set_xp_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    config = get_guild_config(interaction.guild.id)
    if channel:
        # Utiliser le salon existant et le mettre en lecture seule
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            # Donner accès au bot
            bot_overwrite = channel.overwrites_for(interaction.guild.me)
            bot_overwrite.send_messages = True
            bot_overwrite.manage_messages = True
            await channel.set_permissions(interaction.guild.me, overwrite=bot_overwrite)
        except:
            pass
        config["xp_channel"] = str(channel.id)
        set_guild_config(interaction.guild.id, config)
        embed = discord.Embed(
            title="✅ Salon XP configuré",
            description=f"**Salon:** {channel.mention}\nCe salon est maintenant en **lecture seule**. Les annonces de niveau s'y afficheront automatiquement !",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
    else:
        # Auto-créer le salon
        config["xp_channel"] = None
        set_guild_config(interaction.guild.id, config)
        await interaction.response.send_message("✅ Le salon XP sera créé automatiquement au prochain niveau gagné !")

@bot.tree.command(name="remove-xp-channel", description="Désactive le salon d'annonces XP.")
@app_commands.checks.has_permissions(manage_guild=True)
async def remove_xp_channel(interaction: discord.Interaction):
    config = get_guild_config(interaction.guild.id)
    old_channel = config.get("xp_channel")
    config["xp_channel"] = None
    set_guild_config(interaction.guild.id, config)
    await interaction.response.send_message("✅ Salon XP désactivé. Le salon ne sera pas supprimé mais aucune annonce ne sera envoyée.")

# ═══════════════════════════════════════
# XP / NIVEAUX
# ═══════════════════════════════════════

@bot.tree.command(name="rank", description="Ton niveau et XP.")
@app_commands.describe(membre="Le membre (optionnel).")
async def rank(interaction: discord.Interaction, membre: discord.Member = None):
    user = membre or interaction.user
    xp_data = get_xp(user.id, interaction.guild.id)
    xp_needed = (xp_data["level"] + 1) * 100
    embed = discord.Embed(title=f"📊 Niveau de {user.name}", color=discord.Color.gold())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Niveau", value=f"**{xp_data['level']}**", inline=True)
    embed.add_field(name="XP", value=f"**{xp_data['xp']}** / {xp_needed}", inline=True)
    progress = int((xp_data["xp"] / max(xp_needed,1)) * 20)
    bar = "█" * progress + "░" * (20 - progress)
    embed.add_field(name="Progression", value=f"`{bar}`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="xpleaderboard", description="Classement des niveaux.")
async def xpleaderboard(interaction: discord.Interaction):
    data = load_json("levels.json")
    guild_users = [(k, v) for k, v in data.items() if k.startswith(f"{interaction.guild.id}_")]
    sorted_users = sorted(guild_users, key=lambda x: x[1].get("xp",0) + x[1].get("level",0)*100, reverse=True)[:10]
    if not sorted_users:
        await interaction.response.send_message("❌ Aucune donnée.")
        return
    embed = discord.Embed(title="🏆 Top niveaux", color=discord.Color.gold())
    medals = ["🥇", "🥈", "🥉"]
    for i, (key, ud) in enumerate(sorted_users):
        uid = int(key.split("_")[1])
        try: user = await bot.fetch_user(uid); name = user.name
        except: name = f"User {uid}"
        prefix = medals[i] if i < 3 else f"**{i+1}.**"
        embed.add_field(name=f"{prefix} {name}", value=f"Niv. **{ud.get('level',0)}** — {ud.get('xp',0)} XP", inline=False)
    await interaction.response.send_message(embed=embed)

# ═══════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════

@bot.tree.command(name="help", description="Liste des commandes.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Commandes", color=discord.Color.blue())
    embed.add_field(name="🛡️ Modération", value="`clear` `kick` `ban` `unban` `timeout` `untimeout` `warn` `warnings` `clearwarnings` `slowmode` `lock` `unlock` `nickname` `snipe` `editsnipe` `role`", inline=False)
    embed.add_field(name="🤖 Auto-Mod", value="`automod-enable` `automod-disable` `anti-link` `anti-spam` `set-muted-role` `set-log-channel` `restrict-channel` `unrestrict-channel` `ticket-setup` `ticket-close` `ticket-add`", inline=False)
    embed.add_field(name="🎵 Musique", value="`play` `skip` `stop` `queue` `nowplaying` `pause` `resume` `join` `leave`", inline=False)
    embed.add_field(name="📊 XP", value="`rank` `xpleaderboard` `xp-reward` `xp-reward-remove` `set-xp-channel` `remove-xp-channel`", inline=False)
    embed.add_field(name="🎬 YouTube", value="`yt-notify` `yt-notify-list` `yt-notify-remove`", inline=False)
    embed.add_field(name="📢 Auto-Messages", value="`auto-message` `auto-message-list` `auto-message-remove`", inline=False)
    embed.add_field(name="🎉 Welcome", value="`setwelcome` `setgoodbye` `setautorole` `removeautorole`", inline=False)
    embed.add_field(name="💰 Économie", value="`balance` `daily` `work` `rob` `pay` `shop` `buy` `bet` `leaderboard` `slots`", inline=False)
    embed.add_field(name="🎮 Fun", value="`8ball` `roll` `coinflip` `choose` `meme` `rps` `cat` `dog` `slots` `giveaway` `poll` `say` `calc`", inline=False)
    embed.add_field(name="🔧 Utilitaire", value="`ping` `serverinfo` `userinfo` `avatar` `servericon` `botinfo` `uptime` `roleinfo` `invite` `membercount` `weather` `reminder` `poll` `say` `calc`", inline=False)
    embed.set_footer(text="Le bot répond aussi en DM ! 💬")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Infos du serveur.")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=f"Infos: {g.name}", color=discord.Color.blue())
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="ID", value=g.id, inline=True)
    embed.add_field(name="Propriétaire", value=g.owner.mention, inline=True)
    embed.add_field(name="Boost", value=f"Niv. {g.premium_tier} ({g.premium_subscription_count})", inline=True)
    embed.add_field(name="Membres", value=g.member_count, inline=True)
    embed.add_field(name="Salons texte", value=len(g.text_channels), inline=True)
    embed.add_field(name="Salons vocaux", value=len(g.voice_channels), inline=True)
    embed.add_field(name="Rôles", value=len(g.roles), inline=True)
    embed.add_field(name="Créé le", value=g.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Emojis", value=len(g.emojis), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Infos d'un membre.")
@app_commands.describe(membre="Le membre (optionnel).")
async def userinfo(interaction: discord.Interaction, membre: discord.Member = None):
    m = membre or interaction.user
    embed = discord.Embed(title=f"Infos: {m.name}", color=m.color)
    embed.set_thumbnail(url=m.display_avatar.url)
    embed.add_field(name="ID", value=m.id, inline=True)
    embed.add_field(name="Surnom", value=m.nick or "Aucun", inline=True)
    embed.add_field(name="Bot", value="Oui" if m.bot else "Non", inline=True)
    embed.add_field(name="Compte créé", value=m.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="A rejoint", value=m.joined_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Rôles", value=f"{len(m.roles)-1} rôles", inline=True)
    statuses = {"online":"🟢","idle":"🟡","dnd":"🔴","offline":"⚫"}
    embed.add_field(name="Statut", value=statuses.get(str(m.status),"⚫"), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Avatar d'un membre.")
@app_commands.describe(membre="Le membre (optionnel).")
async def avatar(interaction: discord.Interaction, membre: discord.Member = None):
    m = membre or interaction.user
    embed = discord.Embed(title=f"Avatar de {m.name}", color=discord.Color.purple())
    embed.set_image(url=m.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="servericon", description="Icône du serveur.")
async def servericon(interaction: discord.Interaction):
    if not interaction.guild.icon:
        await interaction.response.send_message("❌ Pas d'icône.")
        return
    embed = discord.Embed(title=f"Icône: {interaction.guild.name}", color=discord.Color.blue())
    embed.set_image(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="botinfo", description="Infos du bot.")
async def botinfo(interaction: discord.Interaction):
    uptime = datetime.now(timezone.utc) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    embed = discord.Embed(title="🤖 Bot Info", color=discord.Color.green())
    embed.add_field(name="Nom", value=bot.user.name, inline=True)
    embed.add_field(name="ID", value=bot.user.id, inline=True)
    embed.add_field(name="Serveurs", value=len(bot.guilds), inline=True)
    embed.add_field(name="Membres", value=sum(g.member_count for g in bot.guilds), inline=True)
    embed.add_field(name="Uptime", value=f"{h}h {m}m {s}s", inline=True)
    embed.add_field(name="Latence", value=f"{round(bot.latency*1000)} ms", inline=True)
    embed.add_field(name="Commandes", value="80+", inline=True)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="uptime", description="Temps de fonctionnement.")
async def uptime(interaction: discord.Interaction):
    uptime = datetime.now(timezone.utc) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    embed = discord.Embed(title="⏱️ Uptime", description=f"En ligne depuis **{h}h {m}m {s}s**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roleinfo", description="Infos d'un rôle.")
@app_commands.describe(role="Le rôle.")
async def roleinfo(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(title=f"Rôle: {role.name}", color=role.color)
    embed.add_field(name="ID", value=role.id, inline=True)
    embed.add_field(name="Membres", value=len(role.members), inline=True)
    embed.add_field(name="Position", value=role.position, inline=True)
    embed.add_field(name="Couleur", value=str(role.color), inline=True)
    embed.add_field(name="Mentionnable", value="Oui" if role.mentionable else "Non", inline=True)
    embed.add_field(name="Créé le", value=role.created_at.strftime("%d/%m/%Y"), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="invite", description="Lien d'invitation.")
@app_commands.checks.has_permissions(create_instant_invite=True)
async def invite(interaction: discord.Interaction):
    inv = await interaction.channel.create_invite(max_age=86400, max_uses=1)
    embed = discord.Embed(title="📨 Invitation", description=f"{inv.url}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="membercount", description="Nombre de membres.")
async def membercount(interaction: discord.Interaction):
    g = interaction.guild
    humans = len([m for m in g.members if not m.bot])
    bots = g.member_count - humans
    embed = discord.Embed(title="📊 Membres", color=discord.Color.blue())
    embed.add_field(name="Total", value=g.member_count, inline=True)
    embed.add_field(name="Humains", value=humans, inline=True)
    embed.add_field(name="Bots", value=bots, inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="weather", description="Météo.")
@app_commands.describe(ville="La ville.")
async def weather(interaction: discord.Interaction, ville: str):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://wttr.in/{ville}?format=j1") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    c = data["current_condition"][0]
                    embed = discord.Embed(title=f"🌤️ {ville}", color=discord.Color.blue())
                    embed.add_field(name="🌡️ Temp", value=f"{c['temp_C']}°C (ressenti {c['FeelsLikeC']}°C)", inline=True)
                    embed.add_field(name="💧 Humidité", value=f"{c['humidity']}%", inline=True)
                    embed.add_field(name="💨 Vent", value=f"{c['windspeedKmph']} km/h", inline=True)
                    embed.add_field(name="☁️ Ciel", value=c["weatherDesc"][0]["value"], inline=True)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Introuvable.")
    except:
        await interaction.followup.send("❌ Erreur.")


@bot.tree.command(name="reminder", description="Définit un rappel.")
@app_commands.describe(minutes="Minutes.", rappel="Le rappel.")
async def reminder(interaction: discord.Interaction, minutes: int, rappel: str):
    if minutes < 1 or minutes > 1440:
        await interaction.response.send_message("❌ 1 à 1440 min.", ephemeral=True)
        return
    await interaction.response.send_message(f"⏰ Rappel dans **{minutes} min**: {rappel}")
    await asyncio.sleep(minutes * 60)
    embed = discord.Embed(title="⏰ Rappel", description=f"Hey {interaction.user.mention} !\n**{rappel}**", color=discord.Color.orange())
    try: await interaction.user.send(embed=embed)
    except: pass


@bot.tree.command(name="poll", description="Crée un sondage.")
@app_commands.describe(question="Question.", options="Options avec |.")
async def poll(interaction: discord.Interaction, question: str, options: str):
    parts = [o.strip() for o in options.split("|") if o.strip()]
    if len(parts) < 2 or len(parts) > 10:
        await interaction.response.send_message("❌ 2 à 10 options avec `|`.", ephemeral=True)
        return
    emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    desc = "\n".join(f"{emojis[i]} {o}" for i, o in enumerate(parts))
    embed = discord.Embed(title=f"📊 {question}", description=desc, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    for i in range(len(parts)): await msg.add_reaction(emojis[i])

@bot.tree.command(name="say", description="Le bot répète.")
@app_commands.describe(message="Le message.")
async def say(interaction: discord.Interaction, message: str):
    if interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message(f"💬 {interaction.user.mention}: {message}")

@bot.tree.command(name="giveaway", description="Lance un giveaway.")
@app_commands.describe(duree="Minutes.", prix="Le prix.")
@app_commands.checks.has_permissions(manage_messages=True)
async def giveaway(interaction: discord.Interaction, duree: int, prix: str):
    embed = discord.Embed(title="🎉 GIVEAWAY !", description=f"**Prix:** {prix}\n**Durée:** {duree} min\n**Par:** {interaction.user.mention}\n\nRéagis avec 🎉 !", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")
    await asyncio.sleep(duree * 60)
    msg = await interaction.channel.fetch_message(msg.id)
    users = [u for u in {r async for r in msg.reactions[0].users()} if not u.bot]
    if users:
        winner = random.choice(users)
        await interaction.channel.send(content=winner.mention, embed=discord.Embed(title="🎉 GAGNANT !", description=f"**{prix}**\nGagnant: {winner.mention} 🥳", color=discord.Color.gold()))
    else:
        await interaction.channel.send("🎉 Personne n'a participé !")

@bot.tree.command(name="calc", description="Calculatrice.")
@app_commands.describe(expression="L'expression.")
async def calc(interaction: discord.Interaction, expression: str):
    try:
        allowed = "0123456789+-*/().,% "
        if not all(c in allowed for c in expression):
            await interaction.response.send_message("❌ Caractères interdits.", ephemeral=True)
            return
        result = eval(expression)
        embed = discord.Embed(title="🧮 Calcul", description=f"**{expression} = {result}**", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

# ═══════════════════════════════════════
# FUN
# ═══════════════════════════════════════

@bot.tree.command(name="8ball", description="Boule magique.")
@app_commands.describe(question="Ta question.")
async def ball(interaction: discord.Interaction, question: str):
    r = random.choice(BALL_RESPONSES)
    embed = discord.Embed(title="🎱 Boule magique", description=f"**Q:** {question}\n**R:** {r}", color=discord.Color.purple())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roll", description="Lance un dé.")
@app_commands.describe(maximum="Max (défaut: 6).")
async def roll(interaction: discord.Interaction, maximum: int = 6):
    result = random.randint(1, max(1, maximum))
    embed = discord.Embed(title="🎲 Dé", description=f"🎲 **{result}** (sur {maximum})", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="coinflip", description="Pile ou face.")
async def coinflip(interaction: discord.Interaction):
    r = random.choice(["Pile", "Face"])
    embed = discord.Embed(title="🪙 Pile ou Face", description=f"**{r}**", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="choose", description="Le bot choisit.")
@app_commands.describe(options="Options avec |.")
async def choose(interaction: discord.Interaction, options: str):
    parts = [o.strip() for o in options.split("|") if o.strip()]
    if len(parts) < 2:
        await interaction.response.send_message("❌ 2 options min avec `|`.", ephemeral=True)
        return
    embed = discord.Embed(title="🤔 Choix", description=f"Je choisis: **{random.choice(parts)}**", color=discord.Color.teal())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="meme", description="Meme aléatoire.")
async def meme(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title=data.get("title","Meme"), url=data.get("postLink",""), color=discord.Color.orange())
                    embed.set_image(url=data.get("url",""))
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Erreur.")
    except:
        await interaction.followup.send("❌ Erreur.")

@bot.tree.command(name="rps", description="Pierre, papier, ciseaux.")
@app_commands.describe(choix="Ton choix.")
@app_commands.choices(choix=[
    app_commands.Choice(name="Pierre", value="pierre"),
    app_commands.Choice(name="Papier", value="papier"),
    app_commands.Choice(name="Ciseaux", value="ciseaux"),
])
async def rps(interaction: discord.Interaction, choix: app_commands.Choice[str]):
    bc = random.choice(["pierre","papier","ciseaux"])
    emojis = {"pierre":"🪨","papier":"📄","ciseaux":"✂️"}
    if choix.value == bc:
        result = "Égalité !"; color = discord.Color.orange()
    elif (choix.value=="pierre" and bc=="ciseaux") or (choix.value=="papier" and bc=="pierre") or (choix.value=="ciseaux" and bc=="papier"):
        result = "Tu gagnes ! 🎉"; color = discord.Color.green()
    else:
        result = "Je gagne ! 🤖"; color = discord.Color.red()
    embed = discord.Embed(title="🪨📄✂️ RPS", description=f"**Toi:** {emojis[choix.value]}\n**Bot:** {emojis[bc]}\n{result}", color=color)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="cat", description="Photo de chat.")
async def cat(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🐱 Miaou !", color=discord.Color.orange())
                    embed.set_image(url=data[0]["url"])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Pas de chat.")
    except:
        await interaction.followup.send("❌ Erreur.")

@bot.tree.command(name="dog", description="Photo de chien.")
async def dog(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🐶 Wouf !", color=discord.Color.gold())
                    embed.set_image(url=data["message"])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Pas de chien.")
    except:
        await interaction.followup.send("❌ Erreur.")



@bot.tree.command(name="slots", description="Machine à sous.")
async def slots(interaction: discord.Interaction):
    emojis = ["🍒","🍋","🍊","🍇","🔔","💎"]
    a, b, c = [random.choice(emojis) for _ in range(3)]
    bal = get_balance(interaction.user.id)
    if a == b == c:
        result = "🎉 JACKPOT ! +500 pièces !"; color = discord.Color.gold(); bal["balance"] += 500
    elif a == b or b == c or a == c:
        result = "✨ Deux sur trois ! +50 pièces !"; color = discord.Color.green(); bal["balance"] += 50
    else:
        result = "❌ Perdu !"; color = discord.Color.red()
    set_balance(interaction.user.id, bal)
    embed = discord.Embed(title="🎰 Slots", description=f"| {a} | {b} | {c} |\n\n{result}", color=color)
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════
# ÉCONOMIE
# ═══════════════════════════════════════

@bot.tree.command(name="balance", description="Ton solde.")
@app_commands.describe(membre="Le membre (optionnel).")
async def balance(interaction: discord.Interaction, membre: discord.Member = None):
    user = membre or interaction.user
    bal = get_balance(user.id)
    embed = discord.Embed(title=f"💰 Solde de {user.name}", description=f"**{bal['balance']} pièces**", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Récompense quotidienne.")
async def daily(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    if bal.get("last_daily"):
        last = datetime.fromisoformat(bal["last_daily"])
        if (datetime.now() - last).total_seconds() < 86400:
            remaining = 86400 - (datetime.now() - last).total_seconds()
            await interaction.response.send_message(f"⏳ Reviens dans **{int(remaining//3600)}h {int((remaining%3600)//60)}m**.")
            return
    reward = random.randint(100, 500)
    bal["balance"] += reward
    bal["last_daily"] = datetime.now().isoformat()
    set_balance(interaction.user.id, bal)
    embed = discord.Embed(title="🎁 Daily", description=f"+**{reward} pièces** !\nSolde: **{bal['balance']}**", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="Travaille.")
async def work(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    if bal.get("last_work"):
        last = datetime.fromisoformat(bal["last_work"])
        if (datetime.now() - last).total_seconds() < 3600:
            remaining = 3600 - (datetime.now() - last).total_seconds()
            await interaction.response.send_message(f"⏳ Dans **{int(remaining//60)}m**.")
            return
    jobs = ["Programmeur","Cuisinier","Chanteur","Jardinier","Artiste","Livreur","Médecin","Pilote","Streamer","Astronaute"]
    reward = random.randint(50, 200)
    bal["balance"] += reward
    bal["last_work"] = datetime.now().isoformat()
    set_balance(interaction.user.id, bal)
    embed = discord.Embed(title="💼 Travail", description=f"Tu as travaillé comme **{random.choice(jobs)}** !\n+**{reward} pièces**\nSolde: **{bal['balance']}**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rob", description="Vole un membre.")
@app_commands.describe(membre="La cible.")
async def rob(interaction: discord.Interaction, membre: discord.Member):
    if membre.id == interaction.user.id:
        await interaction.response.send_message("❌ Tu ne peux pas te voler.", ephemeral=True)
        return
    tb = get_balance(membre.id)
    if tb["balance"] < 100:
        await interaction.response.send_message(f"❌ {membre.mention} est trop pauvre.", ephemeral=True)
        return
    if random.random() < 0.4:
        stolen = random.randint(50, min(500, tb["balance"]))
        tb["balance"] -= stolen; set_balance(membre.id, tb)
        rb = get_balance(interaction.user.id); rb["balance"] += stolen; set_balance(interaction.user.id, rb)
        embed = discord.Embed(title="🦹 Vol réussi", description=f"+**{stolen} pièces** volées !", color=discord.Color.green())
    else:
        fine = random.randint(50, 200)
        rb = get_balance(interaction.user.id); rb["balance"] = max(0, rb["balance"] - fine); set_balance(interaction.user.id, rb)
        embed = discord.Embed(title="🚔 Vol échoué", description=f"Amende: **{fine} pièces**.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pay", description="Donne des pièces.")
@app_commands.describe(membre="Le destinataire.", montant="Le montant.")
async def pay(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if montant <= 0:
        await interaction.response.send_message("❌ Invalide.", ephemeral=True)
        return
    bal = get_balance(interaction.user.id)
    if bal["balance"] < montant:
        await interaction.response.send_message("❌ Pas assez.", ephemeral=True)
        return
    bal["balance"] -= montant; set_balance(interaction.user.id, bal)
    tb = get_balance(membre.id); tb["balance"] += montant; set_balance(membre.id, tb)
    embed = discord.Embed(title="💸 Transfert", description=f"{interaction.user.mention} → {membre.mention}: **{montant} pièces**.", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="shop", description="Boutique.")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Boutique", color=discord.Color.gold())
    for k, item in SHOP_ITEMS.items():
        embed.add_field(name=f"{item['name']} — {item['price']} pièces", value=item["description"], inline=False)
    embed.set_footer(text="Utilise /buy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy", description="Achète un item.")
@app_commands.describe(item="L'item.")
@app_commands.choices(item=[app_commands.Choice(name=v["name"], value=k) for k, v in SHOP_ITEMS.items()])
async def buy(interaction: discord.Interaction, item: app_commands.Choice[str]):
    bal = get_balance(interaction.user.id)
    it = SHOP_ITEMS[item.value]
    if bal["balance"] < it["price"]:
        await interaction.response.send_message(f"❌ Pas assez. Prix: **{it['price']}**", ephemeral=True)
        return
    bal["balance"] -= it["price"]; set_balance(interaction.user.id, bal)
    embed = discord.Embed(title="✅ Achat", description=f"**{it['name']}** pour **{it['price']} pièces**.\nSolde: **{bal['balance']}**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bet", description="Parie tes pièces.")
@app_commands.describe(montant="Le montant.")
async def bet(interaction: discord.Interaction, montant: int):
    if montant <= 0:
        await interaction.response.send_message("❌ Invalide.", ephemeral=True)
        return
    bal = get_balance(interaction.user.id)
    if bal["balance"] < montant:
        await interaction.response.send_message("❌ Pas assez.", ephemeral=True)
        return
    if random.random() < 0.45:
        bal["balance"] += montant; set_balance(interaction.user.id, bal)
        embed = discord.Embed(title="🎰 Gagné !", description=f"+**{montant} pièces** !\nSolde: **{bal['balance']}**", color=discord.Color.green())
    else:
        bal["balance"] -= montant; set_balance(interaction.user.id, bal)
        embed = discord.Embed(title="💸 Perdu", description=f"-**{montant} pièces**.\nSolde: **{bal['balance']}**", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="Classement riches.")
async def leaderboard(interaction: discord.Interaction):
    data = load_json("economy.json")
    sorted_users = sorted(data.items(), key=lambda x: x[1].get("balance",0), reverse=True)[:10]
    if not sorted_users:
        await interaction.response.send_message("❌ Aucune donnée.")
        return
    embed = discord.Embed(title="🏆 Richesse", color=discord.Color.gold())
    medals = ["🥇","🥈","🥉"]
    for i, (uid, ud) in enumerate(sorted_users):
        try: user = await bot.fetch_user(int(uid)); name = user.name
        except: name = f"User {uid}"
        prefix = medals[i] if i < 3 else f"**{i+1}.**"
        embed.add_field(name=f"{prefix} {name}", value=f"💰 {ud.get('balance',0)} pièces", inline=False)
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════
# SYSTÈME DE TICKETS
# ═══════════════════════════════════════

TICKET_DATA_FILE = "tickets.json"

def load_tickets():
    if os.path.exists(TICKET_DATA_FILE):
        with open(TICKET_DATA_FILE, "r") as f:
            return json.load(f)
    return {"tickets": {}, "panel_channel": None, "category_id": None}

def save_tickets(data):
    with open(TICKET_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(member: discord.Member) -> bool:
    """Vérifie si un membre est admin ou a la permission manage_guild."""
    return member.guild_permissions.administrator or member.guild_permissions.manage_guild

class TicketPanelView(discord.ui.View):
    """Panneau de tickets — persistant."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Postuler pour le Staff", style=discord.ButtonStyle.primary, custom_id="ticket_staff", emoji="📋")
    async def staff_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "staff")

    @discord.ui.button(label="🆘 Demande d'aide", style=discord.ButtonStyle.success, custom_id="ticket_help", emoji="❓")
    async def help_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "help")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        await interaction.response.defer(ephemeral=True)
        data = load_tickets()
        guild = interaction.guild
        user = interaction.user

        # Vérifier si l'utilisateur a DÉJÀ un ticket ouvert — 1 seul ticket par personne
        for tid, tinfo in data["tickets"].items():
            if tinfo.get("user_id") == str(user.id) and tinfo.get("status") == "open":
                existing_ch = guild.get_channel(int(tinfo["channel_id"]))
                if existing_ch:
                    await interaction.followup.send(
                        f"❌ Tu as déjà un ticket ouvert : {existing_ch.mention}\nFerme-le avant d'en ouvrir un nouveau.",
                        ephemeral=True
                    )
                    return
                else:
                    # Salon supprimé mais ticket encore enregistré — nettoyer
                    data["tickets"][tid]["status"] = "closed"
                    save_tickets(data)

        # Créer/récupérer la catégorie
        category = None
        if data.get("category_id"):
            category = guild.get_channel(int(data["category_id"]))
        if not category:
            try:
                category = await guild.create_category("🎫 Tickets")
                data["category_id"] = str(category.id)
                save_tickets(data)
            except Exception as e:
                await interaction.followup.send(f"❌ Erreur création catégorie: {e}", ephemeral=True)
                return

        # Numéro du ticket
        ticket_num = sum(1 for t in data["tickets"].values() if t.get("type") == ticket_type) + 1
        if ticket_type == "staff":
            channel_name = f"candidature-{user.name[:20]}"
        else:
            channel_name = f"aide-{user.name[:20]}"

        # Permissions du salon
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True),
        }
        # Tous les rôles admin/manage_guild voient le ticket
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, manage_messages=True)

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name[:100],
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {user.name} | Type: {ticket_type} | Statut: Ouvert"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur création salon: {e}", ephemeral=True)
            return

        # Sauvegarder
        ticket_id = str(ticket_channel.id)
        data["tickets"][ticket_id] = {
            "user_id": str(user.id),
            "user_name": user.name,
            "channel_id": str(ticket_channel.id),
            "type": ticket_type,
            "status": "open",
            "created_at": datetime.now().isoformat()
        }
        save_tickets(data)

        # Message du formulaire
        if ticket_type == "staff":
            embed = discord.Embed(
                title="📋 Candidature Staff",
                description=(
                    f"Bienvenue {user.mention} !\n\n"
                    f"Merci de remplir ce formulaire pour postuler au staff.\n"
                    f"Réponds aux questions ci-dessous :\n\n"
                    f"**1.** Quel est ton âge ?\n"
                    f"**2.** Depuis combien de temps es-tu sur le serveur ?\n"
                    f"**3.** Quelle est ton expérience en modération ?\n"
                    f"**4.** Quelles sont tes disponibilités (heures/jours) ?\n"
                    f"**5.** Pourquoi veux-tu rejoindre le staff ?\n"
                    f"**6.** Que peux-tu apporter au serveur ?\n\n"
                    f"📝 Écris tes réponses dans ce salon."
                ),
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="🆘 Demande d'aide",
                description=(
                    f"Bienvenue {user.mention} !\n\n"
                    f"Décris ton problème en répondant à ces questions :\n\n"
                    f"**1.** Quel est ton problème ?\n"
                    f"**2.** Depuis quand rencontres-tu ce problème ?\n"
                    f"**3.** Quelles étapes pour reproduire le bug ?\n"
                    f"**4.** As-tu un message d'erreur ? (copie-le)\n"
                    f"**5.** Autres détails ou captures d'écran ?\n\n"
                    f"📝 Écris tes réponses dans ce salon."
                ),
                color=discord.Color.green()
            )

        embed.set_footer(text=f"Ticket #{ticket_num} | Seuls les admins peuvent fermer ce ticket")
        embed.timestamp = datetime.now()

        # Bouton de fermeture — VISIBLE mais réservé aux admins
        close_view = TicketCloseView()
        await ticket_channel.send(embed=embed, view=close_view)

        # Ping admin
        admin_mentions = [role.mention for role in guild.roles if (role.permissions.administrator or role.permissions.manage_guild) and not role.is_default()]
        if admin_mentions:
            await ticket_channel.send(f"🔔 {admin_mentions[0]} — Nouveau ticket de {user.mention} !", delete_after=15)

        await interaction.followup.send(f"✅ Ton ticket a été créé : {ticket_channel.mention}", ephemeral=True)


class TicketCloseView(discord.ui.View):
    """Bouton de fermeture — persistant."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # SEULS les admins peuvent fermer via le bouton
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent fermer un ticket.",
                ephemeral=True
            )
            return

        await self.do_close(interaction)

    async def do_close(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        data = load_tickets()
        ticket_id = str(channel.id)

        if ticket_id not in data["tickets"]:
            await interaction.followup.send("❌ Ce salon n'est pas un ticket.", ephemeral=True)
            return

        ticket = data["tickets"][ticket_id]

        # Collecter la transcription
        messages = []
        async for msg in channel.history(limit=200, oldest_first=True):
            if not msg.author.bot or msg.content:
                messages.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author.name}: {msg.content}")
        transcript = "\n".join(messages)

        # Marquer fermé
        data["tickets"][ticket_id]["status"] = "closed"
        save_tickets(data)

        # Embed de fermeture
        close_embed = discord.Embed(
            title="🔒 Ticket fermé",
            description=f"Ticket fermé par {interaction.user.mention}.\nSuppression dans 5 secondes...",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=close_embed)

        # Envoyer transcription en DM à l'auteur du ticket
        try:
            original_user = interaction.guild.get_member(int(ticket["user_id"]))
            if original_user:
                transcript_text = transcript[:1800] if transcript else "Aucun message"
                dm_embed = discord.Embed(
                    title="🎫 Transcription de ton ticket",
                    description="```" + transcript_text + "```",
                    color=discord.Color.blurple()
                )
                await original_user.send(embed=dm_embed)
        except:
            pass

        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket fermé par {interaction.user.name}")
        except Exception as e:
            print(f"Erreur suppression ticket: {e}")


@bot.tree.command(name="ticket-setup", description="Crée le panneau de tickets dans un salon. (Admin)")
@app_commands.describe(channel="Le salon où afficher le panneau de tickets.")
async def ticket_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return

    data = load_tickets()
    data["panel_channel"] = str(channel.id)
    save_tickets(data)

    embed = discord.Embed(
        title="🎫 Système de Tickets",
        description=(
            "Bienvenue sur le système de tickets !\n\n"
            "Clique sur un des boutons ci-dessous :\n\n"
            "📋 **Postuler pour le Staff** — Rejoindre l'équipe\n"
            "🆘 **Demande d'aide** — Obtenir de l'aide\n\n"
            "Un salon privé sera créé pour toi uniquement."
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="⚠️ 1 ticket à la fois par membre")

    view = TicketPanelView()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Panneau créé dans {channel.mention} !", ephemeral=True)


@bot.tree.command(name="ticket-close", description="Ferme et supprime le ticket actuel. (Admin uniquement)")
async def ticket_close_cmd(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Seuls les administrateurs peuvent fermer un ticket.", ephemeral=True)
        return

    data = load_tickets()
    ticket_id = str(interaction.channel.id)

    if ticket_id not in data["tickets"]:
        await interaction.response.send_message("❌ Ce salon n'est pas un ticket.", ephemeral=True)
        return

    ticket = data["tickets"][ticket_id]

    # Collecter transcription
    messages = []
    async for msg in interaction.channel.history(limit=200, oldest_first=True):
        if not msg.author.bot or msg.content:
            messages.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author.name}: {msg.content}")
    transcript = "\n".join(messages)

    data["tickets"][ticket_id]["status"] = "closed"
    save_tickets(data)

    close_embed = discord.Embed(
        title="🔒 Ticket fermé",
        description=f"Fermé par {interaction.user.mention}.\nSuppression dans 5 secondes...",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=close_embed)

    # DM transcription à l'auteur
    try:
        original_user = interaction.guild.get_member(int(ticket["user_id"]))
        if original_user:
            transcript_text = transcript[:1800] if transcript else "Aucun message"
            dm_embed = discord.Embed(
                title="🎫 Transcription de ton ticket",
                description="```" + transcript_text + "```",
                color=discord.Color.blurple()
            )
            await original_user.send(embed=dm_embed)
    except:
        pass

    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user.name}")
    except Exception as e:
        print(f"Erreur suppression: {e}")


@bot.tree.command(name="ticket-add", description="Ajoute un membre au ticket. (Admin)")
@app_commands.describe(user="Le membre à ajouter.")
async def ticket_add(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return

    data = load_tickets()
    ticket_id = str(interaction.channel.id)

    if ticket_id not in data["tickets"]:
        await interaction.response.send_message("❌ Ce salon n'est pas un ticket.", ephemeral=True)
        return

    try:
        await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, read_messages=True)
        await interaction.response.send_message(f"✅ {user.mention} ajouté au ticket.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)


# ═══════════════════════════════════════
# ERROR HANDLING + LAUNCH
# ═══════════════════════════════════════

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    try:
        if isinstance(error, app_commands.MissingPermissions):
            missing = ", ".join(error.missing_permissions)
            msg = f"❌ Permission manquante: **{missing}**. Tu n'as pas les droits pour ça."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ Cooldown ! Réessaie dans **{error.retry_after:.1f}s**."
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            msg = f"❌ Le bot n'a pas la permission: **{missing}**."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ Cette commande ne fonctionne pas en DM."
        else:
            msg = f"❌ Erreur inattendue: {str(error)[:200]}"
            print(f"Slash CMD Error: {error}")
        
        # Répondre selon l'état de l'interaction
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)
    except Exception as e:
        print(f"Impossible de répondre à l'erreur: {e}")

keep_alive()

if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ Token Discord manquant ! Définis DISCORD_BOT_TOKEN.")
        exit(1)
    bot.run(token)
