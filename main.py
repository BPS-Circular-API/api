from discord.ext import commands  # Imports required Modules
import discord, requests, sqlite3

intents = discord.Intents.all()
intents.members = True
client = commands.Bot(command_prefix=commands.when_mentioned_or("+"), intents=intents, help_command=None) # Setting prefix


@client.event
async def on_ready():  # Stuff the bot does when it starts
    await client.change_presence(activity=discord.Game(f'+help'))  # Set Presence
    # DiscordComponents(client, change_discord_methods=True)
    global bot_version  # Sets the bot_version global variable
    bot_version = "Beta 0.0.1"

    global embed_footer  # Sets the default Embed footer
    embed_footer = f"BPS Bot • {bot_version}"

    global embed_color  # Sets the default Embed color
    embed_color = 0x1a1aff

    global embed_header  # Sets the default Embed Header (Author)
    embed_header = "BPS Bot"

    global owner_ids
    owner_ids = [837584356988944396, 828970752647626812]
    #                   #Raj               #rayan

    global prefix  # Changing this does not change the prefix, but this prefix shows in embeds, etc.
    prefix = "+"

    global ptero_apikey
    ptero_apikey = "o8rLOrYd0ROImTYQMwhPWNW9PskTq9w2CRnyAkXjnzBBuqMe"

    print("Connected to Discord!")  # Print this when the bot starts

def prepare_db():
    db = sqlite3.connect("./data/data.db")
    c = db.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS announcement (server_id TEXT PRIMARY KEY, channel_id TEXT)")
    db.commit()

    return db, c

db, c = prepare_db()

def get_info(table, selection=["*"]):
    selection = ','.join(selection)
    c.execute(f"SELECT {selection} FROM {table}")
    return c.fetchall()

@client.event
async def on_member_join(member:discord.Member):
    #checking if the member is in announcement-enabled guild
    server = get_info("announcement")
    if str(member.guild.id) not in [x[0] for x in server]:
        return
    
    server = [x for x in server if x[0] == str(member.guild.id)][0]
    await client.get_channel(server[1]).send("UR EMBED")



@client.event  # When user does an invalid command
async def on_command_error(ctx, error):
    if not isinstance(error, commands.CheckFailure):
        await ctx.reply("**Error!** The command may not exist, The Syntax may be wrong or there was an Internal Error. Use `+help` to view all available commands.",delete_after=10.0)
        await ctx.message.add_reaction(":cross_bot:")
        print(f"Sent Invalid-Command message to {ctx.author.name}#{ctx.author.discriminator}")


"""
async def checkcommandchannel(ctx):  # Check if the channel in which a command is executed in is a command-channel
    channel = ctx.channel.id
[3:32 PM]
    if channel != cmd_channel:
        if ctx.author.id in staff_ids:
            await ctx.reply(
                f"Ugh fine. I guess I'll let you use bot commands here, since you're a staff member- :rolling_eyes: ")
            return False
        else:
            await ctx.reply(f"Please execute commands only in <#{cmd_channel}>", delete_after=10.0)
            await ctx.message.add_reaction(":cross_bot:")
            return True
    else: return False
"""


@client.event
async def on_message(ctx):  # On message, Checks every message for...
    if not ctx.author.bot:  # checks if author is a bot.
        if " ping " in f" {ctx.content} ":
            await ctx.message.send("pong")
    await client.process_commands(ctx)



@client.command(aliases=['memory', 'mem', 'cpu', 'ram', 'lag', 'ping'])  # Bot Stats Command
async def stats(ctx):
    #if await checkcommandchannel(ctx): return  # Checks if command was executed in the Command Channel
    placeholder = await status("bot")
    # Stats Embed
    stats = discord.Embed(title='System Resource Usage', description='See CPU and memory usage of the system.',url="https://moonball.io", color=embed_color)
    stats.set_author(name=embed_header)
    stats.add_field(name=':latency_bot: Latency', value=f'{round(client.latency * 1000)}ms',inline=False)
    stats.add_field(name=':cpu_bot: CPU Usage', value=f'{placeholder["cpuUsage"]}%', inline=False)
    stats.add_field(name=':ram_bot: Memory Usage', value=f'{placeholder["memUsage"]}', inline=False)
    stats.add_field(name=':uptime_bot: Uptime', value=f'{placeholder["uptime"]}', inline=False)
    stats.set_footer(text=embed_footer)
    await ctx.reply(embed=stats)
    print(f'Sent bot Stats to message of {ctx.author.name}#{ctx.author.discriminator}')  # Logs to Console





#
#
#   Backend
#
#
def form_dict(stats):  # Takes raw data from the ptero API and converts it into usable variables
    placeholders = {}
    ph_keys = ["state", "memUsage", "cpuUsage", "spaceOccupied", "uptime"]
    ph_values = [stats["attributes"]["current_state"],
                 str(round(stats["attributes"]["resources"]["memory_bytes"] / 1073741824, 2)) + " GB",
                 str(round(stats["attributes"]["resources"]["cpu_absolute"], 2)),
                 str(round(stats["attributes"]["resources"]["disk_bytes"] / 1073741824, 2)) + " GB",
                 str(round(stats["attributes"]["resources"]["uptime"] / 3600000, 2)) + " hour(s)"]
    for ind, ph_key in enumerate(ph_keys): placeholders[ph_key] = ph_values[ind]
    return placeholders


async def status(servername):
    ptero_panel = "panel.moonball.io"  # Put your Ptero Panel's URL here

    server_guide = {'fe5a4fe1': 'proxy', 'e91b165c': 'auth', 'd0f6701c': 'lobby', '5d0ac930': 'survival',  # Change this part, Add your server name and the ptero identifier (example in https://panel.moonball.io/server/5426b68e "5426b68e" is the ID)
                    '3a0eaf97': 'skyblock', '6e5ed2ac': 'duels', 'edeeff53': 'bedwars', '5426b68e': 'bot'}
    headers = {"Authorization": f"Bearer {ptero_apikey}", "Accept": "application/json", "Content-Type": "application/json"}
    if servername == "all":
        servers = {}
        for server_id in list(server_guide.keys()):
            url = f"https://{ptero_panel}/api/client/servers/{server_id}/resources"
            servers[server_guide[server_id]] = form_dict(requests.request('GET', url, headers=headers).json())
        return servers
    if servername not in list(server_guide.values()): return "Invalid server name"
    return form_dict(requests.request('GET', f"https://{ptero_panel}/api/client/servers/{[x[0] for x in server_guide.items() if x[1] == servername][0]}/resources", headers=headers).json())


async def server_status():
    guides = [ # Change this part, Add your server name and the ptero identifier (example in https://panel.moonball.io/server/5426b68e "5426b68e" is the ID)
        ["fe5a4fe1", "proxy"],
        ["e91b165c", "auth"],
        ["d0f6701c", "lobby"],
        ["5d0ac930", "survival"],
        ["3a0eaf97", "skyblock"],
        ["6e5ed2ac", "duels"],
        ["edeeff53", "bedwars"],
        ["5426b68e", "bot"]
    ]

    global server_status  # Sets global variables for the server status
    server_status = {}
    for i in range(len(guides)):
        server_status[guides[i][1]] = await stats(guides[i][1])



client.run('')  # Put your bot token here


