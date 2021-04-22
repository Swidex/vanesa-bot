# bot.py
import os, discord, datetime, random, asyncio, urllib.request, urllib.error, urllib.parse, ssl, json, math
from dotenv import load_dotenv
from discord.ext import tasks, commands
import numpy as np
from file_mgr import *
from discord import utils
from constants import *

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
lottery = [0,0,[]]

# INTERNAL FUNCTIONS

@bot.event
async def on_ready():
    """load data when connected to discord."""
    print(f'{bot.user} has connected to Discord!')
    await load()
    await loop.start()

@tasks.loop(hours=4)
async def loop():
    """quad-hourly functions"""
    await save()
    await lottery_check()

async def save():
    """saves arrays to file"""
    print("Saving...")
    await save_scores('users',users)
    await save_scores('points',points)
    await save_scores('timer',timer)
    await save_scores('inventory',inventory)
    await save_scores('owned_by',owned_by)
    await save_scores('albion_integration',albion_integration)
    await save_scores('lottery',lottery)
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
    global lottery
    users = list(await load_scores('users'))
    points = list(await load_scores('points'))
    timer = list(await load_scores('timer'))
    inventory = list(await load_scores('inventory'))
    owned_by = list(await load_scores('owned_by'))
    albion_integration = list(await load_scores('albion_integration'))
    lottery = list(await load_scores('lottery'))
    print("Complete!")

async def continue_lot(channel):
    """reset lot with no winner"""
    reset_lottery(lottery[1])
    embed = discord.Embed(
        title="Lottery",
        color=bot.user.color,
        description="The lottery pool has concluded!\nThere were no winners this time! All tickets have been added to the pool!"
    )
    embed.add_field(name="Current Pool", value=str(lottery[1]))
    time_after_reset = (datetime.datetime.now() - lottery[0]).total_seconds()
    embed.add_field(name="Time Remaining", value=str(datetime.timedelta(seconds=(259200-time_after_reset))).split(".")[0])
    curr_players = ""
    for player in lottery[2]:
        user = await bot.fetch_user(player[0])
        curr_players += str(user) + " " + str(player[1]) + "x\n"
    if curr_players == "":
        curr_players = "No one"
    embed.add_field(name="Current Participants", value=str(curr_players))
    await channel.send(embed=embed)

async def choose_winner(channel):
    """choose winner of lot"""
    player_pool = []
    for player in lottery[2]:
        for _ in range(player[1]):
            player_pool.append(player[0])
    for _ in range(int(len(player_pool)*.1)):
        player_pool.append(0)
    roll = round(random.random()*(len(player_pool)-1))
    if player_pool[roll] == 0:
        await continue_lot(ctx)
    else:
        winner = await bot.fetch_user(player_pool[roll])
        embed = discord.Embed(
            title="Lottery",
            color=winner.color,
            description="The lottery pool has concluded!\nThe winner was " + str(winner) + "!"
        )
        embed.set_thumbnail(url=winner.avatar_url)
        index = 0
        for player in lottery[2]:
            if player[0] == winner.id:
                winner_index = index
            index += 0
        embed.add_field(name="Prize", value=str(lottery[1]))
        points[find_index(player_pool[roll])] += lottery[1]
        embed.add_field(name="Odds", value=str(lottery[2][winner_index][1])+"/"+str(len(player_pool)))
        reset_lottery(STARTING_POOL)
        await channel.send(embed=embed)

def reset_lottery(amt):
    """func to reset lottery pool"""
    lottery[0] = datetime.datetime.now()
    lottery[1] = amt
    try:
        for player in lottery[2]:
            points[find_index(player[0])] += player[1]*TICKET_PRICE
    except IndexError:
        pass
    lottery[2] = []
    print("Reset Lottery")

async def lottery_check(channel=None):
    """every 72 hours, play out lottery"""
    if channel == None:
        channel = bot.get_channel(DEFAULT_CHANNEL)
    time_after_reset = (datetime.datetime.now() - lottery[0]).total_seconds()
    if time_after_reset >= 259200:
        if len(lottery[2]) >= 1:
            await choose_winner(channel)
        else:
            await continue_lot(channel)
    else:
        embed = discord.Embed(
            title="Lottery",
            color=bot.user.color,
            description="The lottery pool has not concluded yet!"
        )
        embed.add_field(name="Current Pool", value=str(lottery[1]))
        embed.add_field(name="Time Remaining", value=str(datetime.timedelta(seconds=(259200-time_after_reset))).split(".")[0])
        curr_players = ""
        for player in lottery[2]:
            user = await bot.fetch_user(player[0])
            curr_players += str(user) + " " + str(player[1]) + "x\n"
        if curr_players == "":
            curr_players = "No one"
        embed.add_field(name="Current Participants", value=str(curr_players))
        await channel.send(embed=embed)

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

def remove_from_inventory(target):
    """func to go through every inventory and remove target from them"""
    for players in inventory:
        try:
            players = players.tolist()
        except AttributeError:
            pass
        try:
            players.remove(target.id)
        except ValueError:
            pass

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

async def is_admin(ctx):
    """return whether author is admin"""
    if str(ctx.message.author) in ADMINS:
        return True
    else:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_PRIV)
        return False

#DISCORD COMMANDS

async def check_for_reaction(ctx, message, reaction):
    await message.add_reaction(reaction)
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=10.0, check=(user == ctx.author and str(reaction.emoji) == reaction))
    except asyncio.TimeoutError:
        return False
    else:
        return True

@bot.command(pass_context=True)
async def ticket(ctx, amt=None):
    """buy amt of tickets"""
    print(str(amt))
    if amt==None:
        amt = 1
    try:
        amt = int(amt)
        if amt*TICKET_PRICE > points[find_index(ctx.message.author.id)]:
            await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_POINTS)
        else:
            if ctx.message.author.id not in lottery[2]:
                lottery[2].append([ctx.message.author.id,0])
            counter = 0
            for player in lottery[2]:
                if ctx.message.author.id == player[0]:
                    index = counter
            lottery[2][index][1] += amt
            points[ctx.message.author.id] -= amt*TICKET_PRICE
            lottery[1] += amt*TICKET_PRICE
            message = await ctx.channel.send(f"{ctx.message.author.mention} successfully bought " + str(amt) + " tickets for " + str(amt*TICKET_PRICE) + " " + POINT_NAME + "!" + "\n React with ❌ to undo!")
            reacted = await check_for_reaction(ctx,message,"❌")
            if reacted:
                player[1] -= amt
                points[ctx.message.author.id] += amt*TICKET_PRICE
                lottery[1] -= amt*TICKET_PRICE
                await message.delete()
                await ctx.channel.send(f"{ctx.message.author.mention}, canceled ticket purchase.")
    except ValueError:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)

@bot.command(pass_context=True)
async def daily(ctx):
    """discord command to claim daily income"""
    index = find_index(ctx.message.author.id)
    embed = discord.Embed(
        title="**Daily Rewards " + POINT_NAME + "**",
        color=ctx.message.author.color
    )
    claim_time = ((timer[index] + datetime.timedelta(hours = DAILY_TIMER)) - datetime.datetime.now()).total_seconds() / 60
    if timer[index] == datetime.datetime(1,1,1,0,0) or claim_time <= 0:
        points[index] += int(DAILY_AMT)
        timer[index] = datetime.datetime.now()
        embed.description = f"{ctx.message.author.name} claimed " + str(DAILY_AMT) + " " + POINT_NAME + ", and now has " + str(round(points[index])) + " " + POINT_NAME + "."
    else:
        if (claim_time / 60) <= 3600:
            claim_time = str(round(claim_time / 60)) + " Hours"
        else:
            claim_time = str(round(claim_time)) + " Minutes"
        embed.description = f"{ctx.message.author.name}, you have already claimed your daily amount."
        embed.add_field(name="Next Claim:",value="~" + claim_time)
    try:
        fame_diff = await reward_points(index)
        embed.description += "\n\nYou gained an additional " + str(int(fame_diff)) + " PvP Fame since last update!"
        extra_points = math.floor(int(fame_diff)/20000)
        if int(extra_points) > 0:
            embed.description += "\nFrom this, you will gain " + str(int(extra_points*200)) + " " + POINT_NAME + "!"
            albion_integration[index][1] = int(albion_integration[index][1]) + int(extra_points)*20000
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
            await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_POINTS)
        elif int(arg) > 0:
            roll = round(random.random()*100)
            embed = discord.Embed(
                title=f"{ctx.message.author.name} rolled a " + str(roll) + "!",
                color=ctx.message.author.color
            )
            if roll >= 66:
                embed.description = f"{ctx.message.author.name} earned an additional "
            if roll < 66:
                embed.description = f"{ctx.message.author.name} lost "
                amt = int(arg)
                if roll >= 50:
                    amt /= 2
                points[index] -= int(amt)
            elif roll < 75:
                amt = int(float(arg) * 2) - float(arg)
                points[index] += amt
            elif roll < 90:
                amt = int(float(arg) * 2.5) - float(arg)
                points[index] += amt
            elif roll < 100:
                amt = int(float(arg) * 3) - float(arg)
                points[index] += amt
            elif roll == 100:
                amt = int(float(arg) * 4.0) - float(arg)
                points[index] += amt
            embed.description += str(int(amt)) + " " + POINT_NAME + ", and now has " + str(int(points[index])) + " " + POINT_NAME + "."
            await ctx.channel.send(embed=embed)
        else:
            await ctx.channel.send(f"{ctx.message.author.mention}, you must bet more than 0 " + POINT_NAME + ".")
    except (AttributeError, ValueError):
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)

@bot.command(pass_context=True)
async def duel(ctx, target=None, amt=None):
    """discord command for dueling players"""
    global users
    global points
    index = find_index(ctx.message.author.id)
    if amt==None or target==None:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)
    else:
        if amt.lower() == "all":
            amt = points[find_index(ctx.message.author.id)]
        if int(amt) > points[index]:
            await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_POINTS)
        elif int(amt) > 0:
            target = await bot.fetch_user(target[3:len(target)-1])
            def check(reaction, user):
                return user == target and str(reaction.emoji) == '✅'
            message = await ctx.channel.send(f"{target.mention}, do you accept the duel for " + amt + " " + POINT_NAME + "?")
            await message.add_reaction("✅")
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await ctx.channel.send(f"{ctx.message.author.mention}, you duel request timed out.")
            else:
                await message.delete()
                if int(amt) > points[find_index(target.id)]:
                    await ctx.channel.send(f"{target.mention}" + INSUFFICIENT_POINTS )
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
                        embed.description = target.name + " loses " + amt + " " + POINT_NAME + " and " + ctx.message.author.name + " loses " + amt + " " + POINT_NAME + "!"
                        points[target_index] -= int(amt)
                        points[target_index] -= int(amt)
                    else:
                        embed.title=ctx.message.author.name + " wins!"
                        embed.color = ctx.message.author.color
                        embed.description = ctx.message.author.name + " gains " + amt + " " + POINT_NAME + " and " + target.name + " loses " + amt + " " + POINT_NAME + "!"
                        points[target_index] -= int(amt)
                        points[author_index] += int(amt)
                    embed.add_field(name=f"{ctx.message.author.name}'s Roll", value=roll_author)
                    embed.add_field(name=f"{target.name}'s Roll", value=roll_target)
                    await ctx.channel.send(embed=embed)
        else:
            await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)

@bot.command(pass_context=True)
async def tails(ctx, amt=None):
    """discord command for playing heads or tails"""
    if amt.lower() == "all":
            amt = points[find_index(ctx.message.author.id)]
    if amt == None or int(amt) <= 0:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)
    elif int(amt) > points[find_index(ctx.message.author.id)]:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_POINTS)
    else:
        await heads_or_tails(ctx,1,amt)

@bot.command(pass_context=True)
async def heads(ctx, amt=None):
    """discord command for playing heads or tails"""
    if amt.lower() == "all":
            amt = points[find_index(ctx.message.author.id)]
    if amt == None or int(amt) <= 0:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)
    elif int(amt) > points[find_index(ctx.message.author.id)]:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_POINTS)
    else:
        await heads_or_tails(ctx,0,amt)

@bot.command(pass_context=True)
async def give(ctx, target, amt):
    """discord command to give points to target"""
    global users
    global points
    index = find_index(ctx.message.author.id)
    if int(amt) > points[index]:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_POINTS)
    elif int(amt) > 0:
        target = await bot.fetch_user(target[3:len(target)-1])
        points[find_index(target.id)] += int(amt)
        points[find_index(ctx.message.author.id)] -= int(amt)
        await ctx.channel.send(f"{ctx.message.author.mention} gave " + amt + " " + POINT_NAME + " to " + target.name)
    else:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)

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
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)
    elif int(bid) > points[find_index(ctx.message.author.id)]:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INSUFFICIENT_POINTS)
    else:
        user = await bot.fetch_user(target[3:len(target)-1])
        if owned_by[find_index(user.id)][0] == ctx.message.author.id:
            await ctx.channel.send(f"{ctx.message.author.mention}, you already own this user!")
        elif int(bid) > int(owned_by[find_index(user.id)][1]):
            remove_from_inventory(user)
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
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)
    else:
        user = await bot.fetch_user(target[3:len(target)-1])
        if user.id == ctx.message.author.id:
            await ctx.channel.send(f"{ctx.message.author.mention}, you cannot sell yourself!")
        else:
            remove_from_inventory(user)
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
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✅'
    if link==None:
        await ctx.channel.send(f"{ctx.message.author.mention}" + INVALID_ARGS)
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
            message = await ctx.channel.send(f"{ctx.message.author.mention}, is this you? (y/n)")
            await message.add_reaction("✅")
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await ctx.channel.send(f"{ctx.message.author.mention} canceled linking process.")
            else:
                albion_integration[find_index(ctx.message.author.id)][0] = int(link)
                albion_integration[find_index(ctx.message.author.id)][1] = int(data['KillFame'])
                await ctx.channel.send("Linked Albion and Discord account.")
        except urllib.error.HTTPError:
            await ctx.channel.send("Albion user not found.")

@bot.command(pass_context=True)
async def unlink(ctx):
    """discord command to unlink albion player"""
    albion_integration[find_index(ctx.message.author.id)][0] = 0
    albion_integration[find_index(ctx.message.author.id)][1] = 0
    await ctx.channel.send(f"{ctx.message.author.mention}, unlinked Albion account with discord.")

@bot.command(pass_context=True)
async def lot(ctx):
    """discord command to check lot"""
    await lottery_check(ctx.channel)

#ADMIN COMMANDS

@bot.command(pass_context=True)
async def reset_timer(ctx, target):
    """discord command for resetting timer"""
    perms = await is_admin(ctx)
    if perms:
        target = await bot.fetch_user(target[3:len(target)-1])
        timer[find_index(target.id)] = datetime.datetime.now() - datetime.timedelta(hours = DAILY_TIMER)
        await ctx.channel.send(f"Reset {target.mention}'s daily timer.")

@bot.command(pass_context=True)
async def force_save(ctx):
    """discord command for saving"""
    perms = await is_admin(ctx)
    if perms:
        await ctx.channel.send("Saving...")
        await save()
        await ctx.channel.send("Complete!")

@bot.command(pass_context=True)
async def stimulus(ctx):
    """discord command for giving stimmies"""
    perms = await is_admin(ctx)
    if perms:
        index = 0
        for _ in users:
            points[index] += 200
            timer[index] = datetime.datetime.now()
            index += 1
        await ctx.channel.send("Stimulus package sent!")

@bot.command(pass_context=True)
async def force_add(ctx, target, amt):
    """discord command for giving stimmies"""
    perms = await is_admin(ctx)
    if perms:
        target = await bot.fetch_user(target[3:len(target)-1])
        points[find_index(target.id)] += int(amt)
        await ctx.channel.send(f"{ctx.message.author.mention} added " + amt + " " + POINT_NAME + " to " + target.name)

@bot.command(pass_context=True)
async def force_remove(ctx, target, amt):
    """discord command for giving stimmies"""
    perms = await is_admin(ctx)
    if perms:
        target = await bot.fetch_user(target[3:len(target)-1])
        points[find_index(target.id)] -= int(amt)
        await ctx.channel.send(f"{ctx.message.author.mention} removed " + amt + " " + POINT_NAME + " from " + target.name)

@bot.command(pass_context=True)
async def force_set(ctx, target, amt):
    """discord command for giving stimmies"""
    perms = await is_admin(ctx)
    if perms:
        target = await bot.fetch_user(target[3:len(target)-1])
        points[find_index(target.id)] = int(amt)
        await ctx.channel.send(f"{ctx.message.author.mention} set "+ target.name + "'s to " + amt + " " + POINT_NAME)

@bot.command(pass_context=True)
async def force_unlink(ctx, target):
    """discord command for giving stimmies"""
    perms = await is_admin(ctx)
    if perms:
        target = await bot.fetch_user(target[3:len(target)-1])
        albion_integration[find_index(target.id)][0] = 0
        albion_integration[find_index(target.id)][1] = 0
        await ctx.channel.send(f"{ctx.message.author.mention} unlinked "+ target.name + "'s Albion account")

@bot.command(pass_context=True)
async def force_fame(ctx, target, amt):
    """discord command debug"""
    perms = await is_admin(ctx)
    if perms:
        target = await bot.fetch_user(target[3:len(target)-1])
        albion_integration[find_index(target.id)][1] = int(amt)
        await ctx.channel.send("Complete.")

@bot.command(pass_context=True)
async def force_end(ctx):
    """discord command debug"""
    perms = await is_admin(ctx)
    if perms:
        lottery[0] = datetime.datetime.now() - datetime.timedelta(hours=72)
        await lot(ctx)

@bot.command(pass_context=True)
async def force_reset(ctx):
    """discord command debug"""
    perms = await is_admin(ctx)
    if perms:
        reset_lottery(STARTING_POOL)
        await lot(ctx)

bot.run(DISCORD_TOKEN)