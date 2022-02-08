'''
Copyright 2021 Elex

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import os, sys, datetime, random, json

import discord
import asyncio
import aiohttp

from quart import Quart, request
from dateutil.parser import parse



import db

# Load config file as a dictionary
config = {}
with open('config.json') as json_file:
    config = json.load(json_file)

dir = db.dir

# Load list of Jon strips.
JonDir = os.path.join(dir, 'strips', 'jon')
JonStrips = [f for f in os.listdir(JonDir) if os.path.isfile(os.path.join(JonDir, f))]

#Add discord client to event loop
loop = asyncio.get_event_loop()
client = discord.Client(loop=loop)

cmd_prefixes = ["g.", "-nermal ", "-garfield ", "-n ", "-g "]

db.initialize_database()

# Load IDs of channels with automatic strip posting enabled into a list
autochannels = db.load_daily_channels()


async def get_gocomics_url(date):
    # Load GoComics page for specified date
    url = 'https://www.gocomics.com/garfield/' + date.strftime("%Y/%m/%d")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            # If page loads find image URL in page
            if r.status == 200:
                text = await r.text()
                loc = text.find('https://assets.amuniversal.com/')
                img_url = text[loc:loc+63] # URL is always 63 characters long.
                return img_url+".gif" # Add file extension to URL


def random_date(start, end):
    """Generate a random datetime between `start` and `end`"""
    return start + datetime.timedelta(
        # Get a random amount of seconds between `start` and `end`
        seconds=random.randint(0, int((end - start).total_seconds())),
    )


def parse_command(message):
    # Parse message and return separated command and arguments
    message_content = message.content.lower()
    for prefix in cmd_prefixes:
        if message_content.startswith(prefix.lower()):
            owner = (message.author.id == int(config['owner_user_id']))
            command_string = message_content.replace(prefix, "")
            words = command_string.split(" ")
            cmd = words.pop(0)
            return cmd, words, command_string, owner

    return None, None, None, False


async def send_strip(channel, date, color=True):
    if date < datetime.date(1978, 6, 19):
        await channel.send("Garfield didn't exist back then.")
        return

    # Old code, strips.garfield.com is down now.
    # comic_url = "http://strips.garfield.com/iimages1200/" + str(date.year) +"/ga" + date.strftime("%y%m%d") + ".gif"
    #if color is False:
    #    comic_url = "http://strips.garfield.com/bwiimages1200/" + str(date.year) + "/ga" + date.strftime("%y%m%d") + ".gif"

    comic_url = await get_gocomics_url(date)

    comicEmbed = discord.Embed(title="Garfield by Jim Davis", description=date.strftime("%A, %B %d, %Y"), color=0xFCAA14)
    comicEmbed.set_image(url=comic_url)
    msg = await channel.send(embed=comicEmbed)
    return msg


async def send_jon(channel, filename):
    if os.path.isfile(os.path.join(JonDir, filename)):
        date = datetime.datetime.strptime(filename, '%Y-%m-%d.gif')
        file = discord.File(os.path.join(JonDir, filename), filename=filename)
        comicEmbed = discord.Embed(title="Jon by Jim Davis", description=date.strftime("%A, %B %d, %Y"), color=0xFCAA14)
        comicEmbed.set_image(url="attachment://" + filename)
        comicEmbed.set_footer(text="Thank you Quinton Reviews for scanning and restoring Jon.")
        await channel.send(file=file, embed=comicEmbed)
        return
    else:
        await channel.send("Sorry, that strip doesn't exist or isn't available.")


async def post_dailies():
    global autochannels
    autochannels = []
    autochannels = db.load_daily_channels()
    date = datetime.date.today() + datetime.timedelta(days=1)
    for id in autochannels:
        channel = client.get_channel(int(id))
        try:
            msg = await send_strip(channel, date, True)
            # If the comic channel is a news channel, publish the message to followers.
            if channel.is_news():
                await msg.publish()
        except:
            continue



async def update_presence():
    roll = random.randint(1, 3)
    if roll == 1:
        await client.change_presence(activity=discord.Game(name="Garfield Kart"))
    elif roll == 2:
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Garfield and Friends"))
    elif roll == 3:
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="The Garfield Show"))
    else:
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Lasagna Cat"))


@client.event
async def on_connect():
    print("Connected to Discord")


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await update_presence()


@client.event
async def on_message(message):
    # Ignore messages from self, or other bots.
    if message.author == client.user or message.author.bot is True:
        return
    color = True
    cmd, args, cmd_string, owner = parse_command(message)
    if cmd is not None:

        try:
            if args[0] == "bw":
                color = False
        except:
            pass

        if cmd == "shutdown" and owner is True:
            await message.channel.send('See ya!')
            await asyncio.sleep(1)
            await client.close()

        elif cmd == "stats" and owner is True:
            variable = len(client.guilds)
            stats = ""
            stats += "I am currently in **%s** servers.\n" % (variable)
            stats += "```"
            for i in client.guilds:
                stats += i.name + "\n"
            stats += "```"
            await message.channel.send(stats)

        elif cmd == "auto":
            if message.author.guild_permissions.manage_channels is True:
                if db.check_daily_channel(message.guild.id) != message.channel.id:
                    autochannels.append(str(message.channel.id))
                    db.update_daily_channel(message.guild.id, message.channel.id)
                    await message.channel.send('Ok, I will send daily strips in this channel from now on.')
                else:
                    autochannels.remove(str(message.channel.id))
                    db.remove_daily_channel(message.guild.id)
                    await message.channel.send("I'll stop sending strips in this channel.")
            else:
                await message.channel.send("You don't have permission to do that.")

        elif cmd in ["today", "now", "current", "present"]:
            date = datetime.date.today()
            await send_strip(message.channel, date, color)

        elif cmd in ["yesterday", "previous"]:
            date = datetime.date.today() + datetime.timedelta(days=-1)
            await send_strip(message.channel, date, color)

        elif cmd == "random":
            date = random_date(datetime.date(1978, 6, 19), datetime.date.today())
            await send_strip(message.channel, date, color)

        elif cmd == "jon":
            try:
                if args[0]:
                    if args[0] == "random":
                        filename = random.choice(JonStrips)
                        await send_jon(message.channel, filename)
                    else:
                        try:
                            date = parse(cmd_string.replace('jon', "")).date()
                            filename = date.strftime("%Y-%m-%d.gif")
                            await send_jon(message.channel, filename)

                        except ValueError:
                            await message.channel.send("I can't understand that date.")
            except IndexError:
                await message.channel.send("Show strips from Jim Davis's pre-Garfield strip 'Jon'\n```-nermal jon [date]\n-nermal jon random```")

        elif cmd == "help":
            file = open("help.txt")
            line = file.read()
            file.close
            await message.channel.send(line)

        elif cmd == "info":
            infoEmbed = discord.Embed(title="Nermal", description="The world's cutest Discord bot.", color=0xFCAA14)
            infoEmbed.add_field(name="Developer:", value="Elex#0465")
            #infoEmbed.add_field(name="Website:", value="https://nermal.xyz", inline=True)
            infoEmbed.add_field(name="Support server:", value="https://discord.gg/uxn9De6")
            infoEmbed.set_thumbnail(url="https://nermal.xyz/nermal.png")
            await message.channel.send(embed=infoEmbed)

        else:
            try:
                if cmd_string.endswith('bw'):
                    color = False
                    cmd_string = cmd_string.replace('bw', "")

                date = parse(cmd_string).date()

                await send_strip(message.channel, date, color)

            except ValueError:
                print('bad date')
                await message.channel.send("I can't understand that date.")


app = Quart(__name__)


@app.route('/triggerdaily')
async def http_trigger_daily():
    await post_dailies()
    await update_presence()
    return "Success"


# Start the bot

client.loop.create_task(client.start(config['discord_token']))
app.run(host='localhost', port=8080, use_reloader=False, loop=loop)
