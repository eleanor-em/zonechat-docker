# ZoneChat - a discord bot for zone based voice chat in Roblox.
# version date: 16/02/21

# Discord.py API reference
# https://discordpy.readthedocs.io/en/latest/api.html
# bot tips https://github.com/AnIdiotsGuide/discordjs-bot-guide/blob/master/frequently-asked-questions.md

import discord
import os
import asyncio
import shelve
from aiohttp import web
from discord.ext import commands
from ruamel.yaml import YAML
yaml = YAML()

discord_roblox = shelve.open('/data/users.dat')
PREFIX = '!'
INTENTS = discord.Intents.default()
INTENTS.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS, case_insensitive=True)

# global config
config = None

# test bot responsiveness
@bot.command(
  brief = 'test bot responsiveness',
  help = 'returns the bot latency in seconds'
)
async def ping(ctx):
    await ctx.send(f'pong! {round(bot.latency, 4)}s')

# bot startup tasks
@bot.event
async def on_ready():
  global config

  print(f'Logged in as: {bot.user}')
  print(f'With ID: {bot.user.id}\n')

  with open('/data/config.yaml', 'r') as fp:
    config = yaml.load(fp)
    
    # complain about not knowing guild and log_channel IDs
    if config is None:
      config = {}
      dunno_guild_id()
      dunno_log_channel_id()
      return

  grab_guild()
  grab_log_channel()

  with open('/data/config.yaml', 'w') as fp:
    yaml.dump(config, fp)
    
# complaint messages

def dunno_guild_id():
  print('guild_id unknown: please say !setup in the log channel of your discord server')

def faulty_guild_id():
  print('guild_id faulty: bot cannot access guild')
  print('please say !setup in the log channel of your discord server')
  print('make sure your bot is added to your server')

def dunno_log_channel_id():
  print('log_channel_id unknown: please say !setup in the log channel of your discord server')

def faulty_log_channel_id():
  print('log_channel_id faulty: bot cannot access your log_channel')
  print('please say !setup in the log channel of your discord server')

# grab and save the guild and channel id into the config.yaml
@bot.command(
  brief = 'Tells the bot where it is',
  help = 'Run this in your intended log channel for your bot. The bot will record the IDs of the log channel and the server.'
)
@commands.is_owner()
async def setup(ctx):
  global config
  config['guild_id'] = ctx.guild.id
  config['log_channel_id'] = ctx.channel.id

  with open('/data/config.yaml', 'w') as fp:
    yaml.dump(config, fp)

  print('Setup successful.\nguild_id and log_channel_id updated in config.yaml')

  await ctx.send("Yay! Thanks for setting me up.\n Log messages will appear in this channel.\n If you'd like to set a different channel as the log channel, say !setup in that channel.")

# discord user can use !register <roblox_name>
# to add their (roblox_name -> discord_id) association
@bot.command(
  brief = 'register your roblox name',
  help = 'say !register <roblox_name> to associate that roblox name with your ID'
)
async def register(ctx, *args):
  if len(args) != 1:
    await ctx.send('This command needs 1 argument. Say !register <roblox_name>')
    return

  roblox_name = args[0]

  if roblox_name in discord_roblox and discord_roblox[roblox_name] != ctx.author.id:
    original_user = ctx.guild.get_member(discord_roblox[roblox_name])
    await ctx.send(f'{original_user} has already registered {roblox_name}\nThey must !unregister for you to register this roblox name.')
  else:
    discord_roblox[roblox_name] = ctx.message.author.id
    await ctx.send(f'Thanks for registering your Roblox Username! `{roblox_name}`')


@bot.command(
  brief = 'unregister all of your roblox names',
  help = 'removes every roblox name assigned to this discord users ID'
)
async def unregister(ctx):
  deleted = 0
  for roblox_name, discord_id in discord_roblox.items():
    if discord_id == ctx.author.id:
      del discord_roblox[roblox_name]
      deleted += 1
  await ctx.send(f'Found and deleted all {deleted} entries with your discord ID')


@bot.command(
  brief = 'list all of the registered users',
  help = 'lists all roblox usernames registered in the bot\'s database'
)
async def ls(ctx):
  for roblox_name, discord_id in discord_roblox.items():
    log_channel = grab_log_channel()
    await log_channel.send(f'{discord_id}: {roblox_name}')


# Make a voice channel for a zone in the zones category
async def make_zone_voice_channel(guild, zone_name):
  for category in guild.categories:
    if category.name.lower() == 'zones':
      zone_category = category
      break
  else:
    zone_category = await guild.create_category(name='zones')
  
  return await guild.create_voice_channel(name=zone_name, category=zone_category)

# move discord user corresponding to roblox_name
# to the voice channel called zone_name
async def move(roblox_name, zone_name):
  global config

  guild = grab_guild()
  if guild is None: return

  # find the voice channel by name
  for channel in guild.voice_channels:
    if channel.name == zone_name:
      zone_channel = channel
      break
  else:
    # it doesn't exist, so make the zone_channel
    zone_channel = await make_zone_voice_channel(guild, zone_name)
    log_channel = grab_log_channel()
    await log_channel.send(f'Voice channel created for {zone_name}')

  # yoink discord ID from database according to roblox name
  user_id = discord_roblox.get(roblox_name, default=None)

  # Don't know this roblox name
  if user_id is None:
    log_channel = grab_log_channel()
    await log_channel.send(f"Discord ID of {roblox_name} unknown. The discord user who owns that account must say `!register {roblox_name}` to use zone chat.")
    return

  # grab user and move them to the right voice channel
  user = guild.get_member(user_id)

  if user.voice is None:
    print(f"{user.name} ({roblox_name}) -> {zone_name} FAILED (not connected)")
  else:
    try:
      print(f"{user.name} ({roblox_name}) -> {zone_name}")
      await user.move_to(zone_channel)
      print(voice_channel_status(guild.voice_channels))
    except:
      print(f"{user.name} ({roblox_name}) -> {zone_name} FAILED (unknown reason)")
    

def grab_guild():
  if 'guild_id' in config:
    try:
      guild = bot.get_guild(config['guild_id'])
      if guild is None:
        faulty_guild_id()
      else:
        return guild
    except BaseException as e:
      print(e)
      faulty_guild_id()
      return
  else:
    dunno_guild_id()

def grab_log_channel():
  if 'log_channel_id' in config:
    try:
      log_channel = bot.get_channel(config['log_channel_id'])
      if log_channel is None:
        faulty_log_channel_id()
      else:
        return log_channel
    except BaseException:
      faulty_log_channel_id()
      return
  else:
    dunno_log_channel_id()
    
# Send a notification to the log_channel that someone has joined the roblox world
async def on_roblox_join(roblox_name):
  log_channel = grab_log_channel()
  if log_channel is None: return

  if roblox_name in discord_roblox:
    guild = grab_guild()
    if guild is None: return
    member = guild.get_member(discord_roblox[roblox_name])
    if member is not None:
      roblox_name += f' ({member.name})'
  
  await log_channel.send(f'{roblox_name} has joined your roblox world')

# print the current voice channels available in guild, and their members
# may be subject to permissions (see Intents.members)
def voice_channel_status(voice_channels):
  return "\n".join(f"{channel}: {[member.name for member in channel.members]}" for channel in voice_channels)

# move everyone in any voice channel to the voice channel called zone_name
async def gather(zone_name='General'):
  
  guild = grab_guild()


  # find the channel called zone_name (the first such one)
  for channel in guild.voice_channels:
    if channel.name.lower() == zone_name.lower():
      zone_channel = channel
      break
  else:
    # couldn't find it.
    log_channel = grab_log_channel()

    zone_channel = await make_zone_voice_channel(guild, zone_name)
    await log_channel.send(f'Voice channel created for {zone_name}')
  
  # Go through each channel and move all the members
  print(f"Everyone -> '{zone_name}'")
  for channel in guild.voice_channels:
    if channel == zone_channel:
      continue
    
    for member in channel.members:
      await member.move_to(zone_channel)
  
  print(voice_channel_status(guild.voice_channels))



# Thanks https://gist.github.com/Peppermint777/c8465f9ce8b579a8ca3e78845309b832
# and https://stackoverflow.com/questions/52336409/discord-py-rewrite-basic-aiohttp-webserver-in-a-cog
# webserver stuff (roblox and uptimerobot interaction)
class HttpHandler(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  async def webserver(self):
    # handle GET requests (from uptimerobot to stay awake)
    async def get_handler(request):
      return web.Response(text="I'm awake!")

    # handle POST requests (from roblox to move users)
    async def post_handler(request):
      command = await request.json()
      if 'roblox_name' in command and 'zone_name' in command:
        await move(command["roblox_name"], command["zone_name"])
      elif 'roblox_name' in command:
        await on_roblox_join(command['roblox_name'])
      elif 'zone_name' in command:
        await gather(command['zone_name'])

      # Other POST requests are ignored

      return web.Response(text="Thanks")

    # don't touch this
    app = web.Application()
    app.router.add_get('/', get_handler)
    app.router.add_post('/', post_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    self.site = web.TCPSite(runner, '0.0.0.0', 5000)
    await self.bot.wait_until_ready()
    await self.site.start()

  # literally no idea what this does
  def __unload(self):
      asyncio.ensure_future(self.site.stop())

# add the http handling to the bot as cog
def add_http_handling(bot):
    http_handler = HttpHandler(bot)
    bot.add_cog(http_handler)
    bot.loop.create_task(http_handler.webserver())

# start it all up
secret = os.environ.get('DISCORD_BOT_SECRET')
print(f'Using secret token: {secret}')
add_http_handling(bot)
bot.run(secret)
