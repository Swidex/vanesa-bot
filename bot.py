# bot.py
import os, discord, datetime, random, asyncio, urllib.request, urllib.error, urllib.parse, ssl, json, math
from dotenv import load_dotenv
from discord.ext import tasks, commands
import numpy as np
from file_mgr import *
from discord import utils

gcontext = ssl.SSLContext()
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix="!", help_command=None)
ssl._create_default_https_context = ssl._create_unverified_context

users = []
points = []
timer = []
inventory = []
owned_by = []
albion_integration = []
POINT_NAME = ":peach:"
DAILY_TIMER = 12
DAILY_AMT = 200
HEADERS = {
        'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'
    }

@tasks.loop(minutes=30)
async def save():
    """saves arrays to file"""
    print("Saving...")
    await save_scores('users',users)
    await save_scores('points',points)
    await save_scores('timer',timer)
    await save_scores('inventory',inventory)
    await save_scores('owned_by',owned_by)
    await save_scores('albion_integration',albion_integration)
    print("Complete!")

async def load():
    """loads arrays from file"""
    print("Loading...")
    global users
    global points
    global timer
    global owned_by
    global inventory
    global albion_integration
    users = list(await load_scores('users'))
    points = list(await load_scores('points'))
    timer = list(await load_scores('timer'))
    inventory = list(await load_scores('inventory'))
    owned_by = list(await load_scores('owned_by'))
    albion_integration = list(await load_scores('albion_integration'))
    print("Complete!")

@bot.event
async def on_ready():
    """load data when connected to discord."""
    print(f'{bot.user} has connected to Discord!')
    await load()
    await save.start()

def new_user(target):
    """append new user to arrays"""
    global users
    global points
    global timer
    global inventory
    global owned_by
    global albion_integration
    users.append(int(target))
    points.append(0)
    timer.append(datetime.datetime(1,1,1,0,0))
    inventory.append([int(target)])
    owned_by.append([int(target),200])
    albion_integration.append([0,0])

def find_index(target):
    """func to find index of given target"""
    global users
    index = 0
    for user in users:
        if target == user:
            return index
        index += 1
    new_user(target)
    return index

async def heads_or_tails(ctx, choice, amt):
    """interface for heads or tails game"""
    choice_dict = {0:"Heads",1:"Tails"}
    flip_embed = discord.Embed(
        color=ctx.message.author.color,
        title="**Flipping Coin...**",
        author=ctx.message.author
    )
    flip_embed.set_image(url="https://i.pinimg.com/originals/52/91/f5/5291f56897d748b1ca0a10c90023588d.gif")
    roll = round(random.random())
    post_embed = discord.Embed(
        color=ctx.message.author.color,
        title="**" + choice_dict.get(roll) +"!**",
        author=ctx.message.author
    )
    image_dict = {0:"https://i.imgur.com/0zwAecv.png",1:"https://i.imgur.com/HolhEG5.png"}
    post_embed.set_image(url=image_dict.get(roll))
    if roll == choice:
        post_embed.description = f"{ctx.message.author.name} won an additional " + str(amt) + " " + POINT_NAME + "!"
        points[find_index(ctx.message.author.id)] += int(amt)
    else:
        post_embed.description = f"{ctx.message.author.name} lost " + str(amt) + " " + POINT_NAME + "!"
        points[find_index(ctx.message.author.id)] -= int(amt)
    msg = await ctx.channel.send(embed=flip_embed)
    await asyncio.sleep(2)
    await msg.edit(embed=post_embed)

async def get_albion_data(player_id):
    """retrieve albion stats"""
    url = "https://gameinfo.albiononline.com/api/gameinfo/players/" + str(player_id)
    request=urllib.request.Request(url,None,HEADERS)
    with urllib.request.urlopen(request, context=gcontext) as url:
        data = json.loads(url.read().decode())
    return data

async def reward_points(index):
    """reward points based on how often"""
    curr_fame = await get_albion_data(albion_integration[index][0])
    diff = int(curr_fame['KillFame']) - int(albion_integration[index][1])
    return int(diff)

@bot.command(pass_context=True)
async def daily(ctx):
    """discord command to claim daily income"""
    index = find_index(ctx.message.author.id)
    embed = discord.Embed(
        title="**Daily Rewards " + POINT_NAME + "**",
        color=ctx.message.author.color
    )
    claim_time = (datetime.datetime.now() - (timer[index] + datetime.timedelta(hours = DAILY_TIMER))) / 60
    print(claim_time)
    if timer[index] == datetime.datetime(1,1,1,0,0) or claim_time >= int(DAILY_AMT*60):
        points[index] += int(DAILY_AMT)
        timer[index] = datetime.datetime.now()
        embed.description = f"{ctx.message.author.name} claimed " + str(DAILY_AMT) + " " + POINT_NAME + ", and now has " + str(round(points[index])) + " " + POINT_NAME + "."
    else:
        if (claim_time.seconds / 60) <= 3600:
            claim_time = str(round(claim_time.seconds / 3600)) + " Hours"
        else:
            claim_time = str(round(claim_time.seconds)) + " Minutes"
        embed.description = f"{ctx.message.author.name}, you have already claimed your daily amount."
        embed.add_field(name="Next Claim:",value="~" + claim_time)
    try:
        fame_diff = await reward_points(index)
        embed.description += "\n\nYou gained an additional " + str(int(fame_diff)) + " PvP Fame since last update!"
        extra_points = math.floor(int(fame_diff)/20000)
        if int(extra_points) > 0:
            embed.description += "\nFrom this, you will gain " + str(int(extra_points*200)) + " " + POINT_NAME + "!"
            albion_integration[index][1] += extra_points*20000
            points[index] += int(extra_points*200)
        else:
            embed.description += "\nYou do not meet the threshold to gain more " + POINT_NAME + "."
    except urllib.error.HTTPError:
        pass
    await ctx.channel.send(embed=embed)

@bot.command(pass_context=True)
async def gamble(ctx, arg=None):
    """command for gambling money"""
    index = find_index(ctx.message.author.id)
    try:
        if arg.lower() == "all":
            arg = points[find_index(ctx.message.author.id)]
        if int(arg) > points[index]:
            await ctx.channel.send(f"{ctx.message.author.mention}, you have insufficient " + POINT_NAME + " for this gamble.")
        elif int(arg) > 0:
            roll = round(random.random()*100)
            embed = discord.Embed(
                title=f"{ctx.message.author.name} rolled a " + str(roll) + "!",
                color=ctx.message.author.color
            )
            if roll >= 50:
                embed.description = f"{ctx.message.author.name} earned an additional "
            if roll < 50:
                embed.description = f"{ctx.message.author.name} lost "
                amt = int(arg)
                points[index] -= int(arg)
            elif roll < 66:
                amt = int(float(arg) * 1.5) - float(arg)
                points[index] += amt
            elif roll < 75:
                amt = int(float(arg) * 2) - float(arg)
                points[index] += amt
            elif roll < 90:
                amt = int(float(arg) * 2.33) - float(arg)
                points[index] += amt
            elif roll < 100:
                amt = int(float(arg) * 2.66) - float(arg)
                points[index] += amt
            elif roll == 100:
                amt = int(float(arg) * 3.0) - float(arg)
                points[index] += amt
            embed.description += str(int(amt)) + " " + POINT_NAME + ", and now has " + str(int(points[index])) + " " + POINT_NAME + "."
            await ctx.channel.send(embed=embed)
        else:
            await ctx.channel.send(f"{ctx.message.author.mention}, you must bet more than 0 " + POINT_NAME + ".")
    except ValueError:
        await ctx.channel.send("Invalid argument, please provide a valid amount.")

@bot.command(pass_context=True)
async def duel(ctx, target=None, amt=None):
    """discord command for dueling players"""
    global users
    global points
    if amt.lower() == "all":
            amt = points[find_index(ctx.message.author.id)]
    index = find_index(ctx.message.author.id)
    if amt==None or target==None:
        await ctx.channel.send(f"{ctx.message.author.mention}, please provide more arguments.")
    elif int(amt) > points[index]:
        await ctx.channel.send(f"{ctx.message.author.mention}, you have insufficient " + POINT_NAME + " to duel.")
    elif int(amt) > 0:
        target = await bot.fetch_user(target[3:len(target)-1])
        await ctx.channel.send(f"{target.mention}, do you accept the duel for " + amt + " " + POINT_NAME + " (y/n)?")
        timeout = 0
        while timeout < 10:
            msg = await bot.wait_for('message')
            if msg.content.lower() == 'y' and msg.author == target:
                if int(amt) > points[find_index(target.id)]:
                    await ctx.channel.send(f"{target.mention}, you have insufficient " + POINT_NAME + " to accept the duel.")
                    break
                else:
                    roll_target = round(random.random()*100)
                    roll_author = round(random.random()*100)
                    target_index = find_index(target.id)
                    author_index = find_index(ctx.message.author.id)
                    embed = discord.Embed()
                    if roll_target > roll_author:
                        embed.title=target.name + " wins!"
                        embed.color = target.color
                        embed.description = target.name + " gains " + amt + " " + POINT_NAME + " and " + ctx.message.author.name + " loses " + amt + " " + POINT_NAME + "!"
                        points[target_index] += int(amt)
                        points[author_index] -= int(amt)
                    elif roll_target == roll_author:
                        embed.title= "Oh no... You both rolled the same. You both lose the bet."
                        embed.color = bot.user.color
                        embed.description = target.name + "loses " + amt + " " + POINT_NAME + " and " + ctx.message.author.name + " loses " + amt + " " + POINT_NAME + "!"
                        points[target_index] -= int(amt)
                        points[target_index] -= int(amt)
                    else:
                        embed.title=ctx.message.author.name + " wins!"
                        embed.color = ctx.message.author.color
                        embed.description = ctx.message.author.name + " gains " + amt + " " + POINT_NAME + " and " + target.name + " loses " + amt + " " + POINT_NAME + "!"
                        points[target_index] -= int(amt)
                        points[author_index] += int(amt)
                    await ctx.channel.send(embed=embed)
                    break
            elif msg.content.lower() =='n' and msg.author == target:
                await ctx.channel.send(f"{ctx.message.author.mention}, {target.mention} denied your duel request.")
                break
            timeout += 1
        if timeout >= 10:
            await ctx.channel.send(f"{ctx.message.author.mention}, your duel challenge has timed out.")
    else:
        await ctx.channel.send(f"{ctx.message.author.mention}, you must bet more than 0 " + POINT_NAME + " to duel.")

@bot.command(pass_context=True)
async def tails(ctx, amt=None):
    """discord command for playing heads or tails"""
    if amt.lower() == "all":
            amt = points[find_index(ctx.message.author.id)]
    if amt == None or int(amt) <= 0:
        await ctx.channel.send(f"{ctx.message.author.mention}, please bet a valid amount.")
    elif int(amt) > points[find_index(ctx.message.author.id)]:
        await ctx.channel.send(f"{ctx.message.author.mention}, you have insufficient " + POINT_NAME + " for this game.")
    else:
        await heads_or_tails(ctx,1,amt)

@bot.command(pass_context=True)
async def heads(ctx, amt=None):
    """discord command for playing heads or tails"""
    if amt.lower() == "all":
            amt = points[find_index(ctx.message.author.id)]
    if amt == None or int(amt) <= 0:
        await ctx.channel.send(f"{ctx.message.author.mention}, please bet a valid amount.")
    elif int(amt) > points[find_index(ctx.message.author.id)]:
        await ctx.channel.send(f"{ctx.message.author.mention}, you have insufficient " + POINT_NAME + " for this game.")
    else:
        await heads_or_tails(ctx,0,amt)

@bot.command(pass_context=True)
async def manual_save(ctx):
    """discord command for saving"""
    if ctx.message.author.name == 'Swidex':
        await save()

@bot.command(pass_context=True)
async def stimulus(ctx):
    """discord command for giving stimmies"""
    if str(ctx.message.author) == 'Swidex#2907':
        index = 0
        for _ in users:
            points[index] += 200
            timer[index] = datetime.datetime.now()
            index += 1
        await ctx.channel.send("Stimulus package sent!")
    else:
        await ctx.channel.send("You have insufficient priveleges for this command.")

@bot.command(pass_context=True)
async def admin_give(ctx, target, amt):
    """discord command for giving stimmies"""
    if str(ctx.message.author) == 'Swidex#2907':
        target = await bot.fetch_user(target[3:len(target)-1])
        points[find_index(target.id)] += int(amt)
        await ctx.channel.send(f"{ctx.message.author.mention} gave " + amt + " " + POINT_NAME + " to " + target.name)
    else:
        await ctx.channel.send("You have insufficient priveleges for this command.")

@bot.command(pass_context=True)
async def set_fame(ctx, target, amt):
    """discord command debug"""
    if str(ctx.message.author) == 'Swidex#2907':
        target = await bot.fetch_user(target[3:len(target)-1])
        albion_integration[find_index(target.id)][1] = int(amt)
        await ctx.channel.send("Complete.")
    else:
        await ctx.channel.send("You have insufficient priveleges for this command.")

@bot.command(pass_context=True)
async def give(ctx, target, amt):
    """discord command to give points to target"""
    global users
    global points
    index = find_index(ctx.message.author.id)
    if int(amt) > points[index]:
        await ctx.channel.send(f"{ctx.message.author.mention}, you have insufficient " + POINT_NAME + " to give.")
    elif int(amt) > 0:
        target = await bot.fetch_user(target[3:len(target)-1])
        points[find_index(target.id)] += int(amt)
        points[find_index(ctx.message.author.id)] -= int(amt)
        await ctx.channel.send(f"{ctx.message.author.mention} gave " + amt + " " + POINT_NAME + " to " + target.name)
    else:
        await ctx.channel.send(f"{ctx.message.author.mention}, you must give more than 0 " + POINT_NAME + ".")

@bot.command(pass_context=True)
async def profile(ctx, target=None):
    """discord command for checking who you own and who your owned by"""
    if target == None:
        target = ctx.message.author
    else:
        target = await bot.fetch_user(target[3:len(target)-1])
    index = find_index(target.id)
    owner = await bot.fetch_user(int(owned_by[index][0]))
    embed = discord.Embed(
        color=target.color,
        description=str(int(points[find_index(target.id)])) + " " + POINT_NAME,
        title=f"**{target.name}'s Profile**"
    )
    embed.set_thumbnail(url=target.avatar_url)
    try:
        data = await get_albion_data(albion_integration[index][0])
        embed.add_field(name="Guild",value=data['GuildName'])
        embed.add_field(name="PvP Fame",value=data['KillFame'])
        embed.add_field(name="PvE Fame",value=data['LifetimeStatistics']['PvE']['Total'])
        embed.add_field(name="Gathering Fame",value=data['LifetimeStatistics']['Gathering']['All']['Total'])
        embed.add_field(name="Crafting Fame",value=data['LifetimeStatistics']['Crafting']['Total'])
    except urllib.error.HTTPError:
        pass
    embed.add_field(name="**Owner**", value=f"{owner.mention} for *" + str(owned_by[index][1]) + "* " + POINT_NAME)
    amt = 0
    inv = ""
    try:
        for x in inventory[index]:
            amt += 1
            inv += str(await bot.fetch_user(int(x))) + "\n"
        if amt == 0:
            inv += "No One"
    except IndexError:
        pass
    embed.add_field(name="**Inventory**", value=inv)
    await ctx.channel.send(embed=embed)

@bot.command(pass_context=True)
async def buy(ctx, target=None, bid=None):
    """discord command to buy user"""
    global users
    global inventory
    global owned_by
    global points
    if target == None or bid==None:
        await ctx.channel.send(f"{ctx.message.author.mention}, please provide more arguments for the command (i.e !buy <person> <bid>)")
    elif int(bid) > points[find_index(ctx.message.author.id)]:
        await ctx.channel.send(f"{ctx.message.author.mention}, you have insufficient " + POINT_NAME + " to make the bid.")
    else:
        user = await bot.fetch_user(target[3:len(target)-1])
        if owned_by[find_index(user.id)][0] == ctx.message.author.id:
            await ctx.channel.send(f"{ctx.message.author.mention}, you already own this user!")
        elif int(bid) > int(owned_by[find_index(user.id)][1]):
            for players in inventory:
                try:
                    players = players.tolist()
                except AttributeError:
                    pass
                try:
                    players.remove(user.id)
                except ValueError:
                    pass
            try:
                inventory[find_index(ctx.message.author.id)] = inventory[find_index(ctx.message.author.id)].tolist()
            except AttributeError:
                pass
            inventory[find_index(ctx.message.author.id)].append(user.id)
            owned_by[find_index(user.id)][0] = ctx.message.author.id
            owned_by[find_index(user.id)][1] = bid
            points[find_index(ctx.message.author.id)] -= int(bid)
            await ctx.channel.send(f"{ctx.message.author.mention} successfully bought " + f"{user.mention} for " + bid + " " + POINT_NAME + "!")
        else:
            await ctx.channel.send(f"{ctx.message.author.mention}, the given bid is too low to buy. Please bet more than " + str(owned_by[find_index(user.id)][1]) + " " + POINT_NAME + " to successfully buy.")

@bot.command(pass_context=True)
async def sell(ctx, target=None):
    """discord command to sell user"""
    if target == None:
        await ctx.channel.send(f"{ctx.message.author.mention}, please provide more arguments for the command (i.e !buy <person> <bid>)")
    else:
        user = await bot.fetch_user(target[3:len(target)-1])
        if user.id == ctx.message.author.id:
            await ctx.channel.send(f"{ctx.message.author.mention}, you cannot sell yourself!")
        else:
            for players in inventory:
                try:
                    players = players.tolist()
                except AttributeError:
                    pass
                try:
                    players.remove(user.id)
                except ValueError:
                    pass
            try:
                inventory[find_index(user.id)] = inventory[find_index(user.id)].tolist()
            except AttributeError:
                pass
            inventory[find_index(user.id)].append(user.id)
            owned_by[find_index(user.id)][0] = user.id
            returned_money = int(owned_by[find_index(user.id)][1])
            points[find_index(ctx.message.author.id)] += (returned_money*.75)
            owned_by[find_index(user.id)][1] = 200
            await ctx.channel.send(f"{ctx.message.author.mention}, sold " + f"{user.mention}" + " for " + str(returned_money) + " " + POINT_NAME + "!")

@bot.command(pass_context=True)
async def leaderboard(ctx):
    """discord command to see leaderboard"""
    global points
    global users
    ranked_users = [users for _,users in sorted(zip(points,users),reverse=True)]
    counter = 1
    embed = discord.Embed(
        color=bot.user.color,
        title=":peach: Leaderboard"
    )
    for index in range(9):
        try:
            player = await bot.fetch_user(int(ranked_users[index]))
            embed.add_field(name="**#" + str(counter) + " " + player.name + "**", value=str(int(points[find_index(ranked_users[index])])) + " :peach:\n\n")
            counter += 1
        except IndexError:
            break
    await ctx.channel.send(embed=embed)

@bot.command(pass_context=True)
async def link(ctx, link=None):
    """discord command to link albion player"""
    if link==None:
        await ctx.channel.send(f"{ctx.message.author.mention}, please provide sufficient arguments.")
    else:
        try:
            data = await get_albion_data(link)
            embed = discord.Embed(
                title=data['Name'],
                color=ctx.message.author.color
            )
            embed.add_field(name="Guild",value=data['GuildName'])
            embed.add_field(name="PvP Fame",value=data['KillFame'])
            embed.add_field(name="PvE Fame",value=data['LifetimeStatistics']['PvE']['Total'])
            embed.add_field(name="Gathering Fame",value=data['LifetimeStatistics']['Gathering']['All']['Total'])
            embed.add_field(name="Crafting Fame",value=data['LifetimeStatistics']['Crafting']['Total'])
            await ctx.channel.send(embed=embed)
            await ctx.channel.send(f"{ctx.message.author.mention}, is this you? (y/n)")
            timeout = 0
            while timeout < 10:
                msg = await bot.wait_for('message')
                if msg.content.lower() == 'y' and msg.author == ctx.message.author:
                    albion_integration[find_index(ctx.message.author.id)][0] = link
                    albion_integration[find_index(ctx.message.author.id)][1] = data['KillFame']
                    await ctx.channel.send("Linked Albion and Discord account.")
                    break
                elif msg.content.lower() =='n' and msg.author == ctx.message.author:
                    await ctx.channel.send("Canceled integration with Albion.")
                    break
                timeout += 1
            if timeout >= 10:
                await ctx.channel.send("Albion integration timed out.")
        except urllib.error.HTTPError:
            await ctx.channel.send("Albion user not found.")

@bot.command(pass_context=True)
async def unlink(ctx):
    """discord command to unlink albion player"""
    albion_integration[find_index(ctx.message.author.id)][0] = 0
    albion_integration[find_index(ctx.message.author.id)][1] = 0
    await ctx.channel.send(f"{ctx.message.author.mention}, unlinked Albion account with discord.")

@bot.command(pass_context=True)
async def reset_time(ctx, target):
    """discord command for resetting timer"""
    if str(ctx.message.author) == 'Swidex#2907':
        target = await bot.fetch_user(target[3:len(target)-1])
        timer[find_index(target.id)] = datetime.datetime.now() - datetime.timedelta(hours = DAILY_TIMER)
        await ctx.channel.send(f"Reset {target.mention}'s daily timer.")
    else:
        await ctx.channel.send("You have insufficient priveleges for this command.")

bot.run(DISCORD_TOKEN)