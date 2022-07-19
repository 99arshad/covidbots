import os
import random
import re
import string
import sys

import discord
import imgkit
from discord.ext import commands
from fake_headers import Headers

BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")
sys.path.append(BASE_DIR)
from functions_ import total_states_districts, fetchCentersData, notification, options, notify_accepted_str, message_parser, crop_image, domain, domain2

headers = Headers(headers=True)
json_total_states_districts = total_states_districts()

examplequeries = '''\nExample Query:\n\tAvailable slots:\n\t\tEnter "$place name age=18/45 dose=1/2"\n\tFor hourly notification:\n\t\tAdd "notify"'''

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="$", description="The description")


@bot.command()
async def usage(ctx):
    strings = examplequeries

    await ctx.send(f"```{strings}```")


@bot.event
async def on_command_error(context, error):
    pass


@bot.event
async def on_ready():
    print("Starting Covistan Discord Bot")


@bot.listen()
async def on_message(message):
    if str(message.content).startswith("$"):
        if not str(message.content).startswith("$usage"):
            messagestring = "".join(re.sub(r"[-()\"#/;:©<>_“”$^&…{}`'‘’%~|.!?,]", " ", str(message.content)))
            data, notify = message_parser(messagestring=messagestring)

            if "state_id" in data or "pincode" in data:
                tables = fetchCentersData(maindict=data, discordbot=True)
                slot_str, age_str, dose_str, url = notify_accepted_str(userdata=data)
                embedVar = discord.Embed(title=f"Click here for more information", url=url, color=0x00ff00)
                if notify:
                    chat_id = message.author.id
                    name = str(message.author).split("#")[0]
                    data.update({"chat_id": chat_id, "name": name})
                    data = notification(rawdata=data, discordbot=True)

                    embedVar.description = f"Click [here](https://{domain2}/{data['code']}) to unsubscribe.\nFor slot booking Visit [CoWin](https://selfregistration.cowin.gov.in/)"
                    embedVar.set_author(name=f"We'll notify you shortly for {slot_str} {age_str} and {dose_str}")

                else:
                    embedVar.description = "For slot booking Visit [CoWin](https://selfregistration.cowin.gov.in/)"
                    embedVar.set_author(name=f"Total {slot_str} {age_str} and {dose_str} ")

                if "error" not in tables:

                    if "pincode" in data:
                        embedVar.add_field(name="Pincode", value=str(data['pincode']), inline=True)

                    elif "state_name" in data:
                        embedVar.add_field(name="State", value=data['state_name'], inline=True)
                        if 'district_name' in data:
                            embedVar.add_field(name="District", value=data['district_name'], inline=True)

                    table, dataitems = tables
                    showing=dataitems['showing']
                    total=dataitems['total']
                    tablehead = {}
                    tablehead.update(data)
                    tablehead.pop("age") if "age" in tablehead else ""
                    tablehead.pop("dose") if "dose" in tablehead else ""
                    tablehead.pop("ntfy") if "ntfy" in tablehead else ""
                    tablehead.pop("state_id") if "state_id" in tablehead else ""
                    tablehead.pop("district_id") if "district_id" in tablehead else ""
                    dataitems.pop("showing") if "showing" in dataitems else ""
                    dataitems.pop("total") if "total" in dataitems else ""
                    for k, v in dataitems.items():
                        if type(v) == list:
                            v = ", ".join(v)
                        tablehead.update({k: v})
                        embedVar.add_field(name=k, value=v, inline=True)
                    headertablestring = '<table border="1" class="table table-responsive table-striped ' \
                                        'table-bordered" style="margin-bottom: 10px;"><thead><tr >' \
                                        + ''.join([f"<th>{k.replace('_', ' ').capitalize()}</th>" for k in
                                                   tablehead]) + '</tr></thead><tbody><tr>' \
                                        + ''.join([f"<td>{v}</td>" for v in tablehead.values()]) \
                                        + '</tr></tbody></table>'
                    footertablestring=f'<table border="1" class="table table-responsive table-striped table-bordered" ' \
                                      f'style="border-bottom-width: 20px;border-bottom-color: black;"><thead><tr ' \
                                      f'><th>Showing {showing} out of {total} centers. For more information visit: ' \
                                      f'https://covistan.com</th></tr></thead></table> '
                    imgname = ''.join(
                        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in
                        range(18))
                    imgaddress = f'{BASE_DIR}/temp_images/{imgname}.jpg'
                    cssdir = f"{os.path.dirname(BASE_DIR)}/static"
                    css = [f"{cssdir}/css/bootstrap.min.css", f"{cssdir}/css/style.css",
                           f"{cssdir}/admin_section/css/admin.css"]
                    imgkit.from_string(headertablestring + table+footertablestring, output_path=imgaddress, options=options, css=css)

                    crop_image(imgfile=imgaddress)
                    embedVar.set_image(url=f"attachment://{imgname}.jpg")
                    File = discord.File(imgaddress, filename=f"{imgname}.jpg")
                    await message.channel.send(file=File, embed=embedVar)
                    os.remove(imgaddress)

                else:
                    embedVar.set_author(name=f"{tables['error']}")
                    await message.channel.send(embed=embedVar)
            else:
                embedVar = discord.Embed(title=f"Visit our website for more information", url=f"https://{domain}",
                                         color=0x00ff00)
                embedVar.set_author(name=f"No Matching State or District found with name: {messagestring}")
                embedVar.description = "For slot booking Visit [CoWin](https://selfregistration.cowin.gov.in/)"
                await message.channel.send(embed=embedVar)
            await message.channel.send(f"Enter '$usage' to get usage information")
