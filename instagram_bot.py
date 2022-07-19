import os
import random
import re
import string
import sys
import time
import imgkit
from instabot import Bot

BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")
sys.path.append(BASE_DIR)
from functions_ import message_parser, fetchCentersData, notify_accepted_str, notification, options, crop_image, \
    domain2, domain

BASE_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")


def fetch_unread_messages(bot):
    while True:
        messages_json = bot.get_messages()
        # print(messages_json)
        if messages_json['inbox']['unseen_count'] > 0:
            print(f"Total unread messages: {messages_json['inbox']['unseen_count']}")
            for message_info in messages_json['inbox']['threads']:
                if message_info['read_state'] == 1:
                    textmessage = ""
                    usersdata = message_info['users']
                    last_message_data = message_info['last_permanent_item']
                    userid = str(last_message_data['user_id'])
                    if last_message_data['item_type'] == "text":
                        textmessage = last_message_data['text']
                    elif last_message_data['item_type'] == "link":
                        textmessage = last_message_data['link']['text']
                    if textmessage != "":
                        print(f"user {usersdata[0]['username']}: {textmessage}")
                        messagestring = "".join(re.sub(r"[-()\"#/;:©<>_“”$^&…{}`'‘’%~|.!?,]", " ", str(textmessage)))
                        if "usage" not in messagestring.lower():
                            data, notify = message_parser(messagestring=messagestring)
                            print(data)
                            tablehead = {}
                            tablehead.update(data)
                            if "state_id" in data or "pincode" in data:
                                tables = fetchCentersData(maindict=data, discordbot=True)
                                slot_str, age_str, dose_str, url = notify_accepted_str(userdata=data)

                                if notify:
                                    data.update({"name": usersdata[0]['username']})
                                    data = notification(rawdata=data, whatsapp=True)

                                if "error" not in tables:
                                    tables, dataitems = tables

                                    tablehead.pop("age")
                                    tablehead.pop("dose")
                                    tablehead.pop("ntfy")
                                    tablehead.pop("state_id") if "state_id" in tablehead else ""
                                    tablehead.pop("district_id") if "district_id" in tablehead else ""

                                    for k, v in dataitems.items():
                                        if type(v) == list:
                                            v = ", ".join(v)
                                        tablehead.update({k: v})
                                    headertablestring = '<table border="1" class="table table-responsive table-striped ' \
                                                        'table-bordered" style="margin-bottom: 10px;"><thead><tr >' \
                                                        + ''.join(
                                        [f"<th>{k.replace('_', ' ').capitalize()}</th>" for k in
                                         tablehead]) + '</tr></thead><tbody><tr>' \
                                                        + ''.join([f"<td>{v}</td>" for v in tablehead.values()]) \
                                                        + '</tr></tbody></table>'
                                    footertablestring = f'<table border="1" class="table table-responsive table-striped table-bordered" ' \
                                                        f'style="border-bottom-width: 20px;border-bottom-color: black;"><thead><tr ' \
                                                        f'><th>Showing 1 out of {str(len(tables))} pages. For more information visit: ' \
                                                        f'https://covistan.com</th></tr></thead></table> '
                                    imgname = ''.join(
                                        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                                        for _
                                        in
                                        range(18))
                                    imgaddress = f'{BASE_DIR}/temp_images/{imgname}.jpg'
                                    cssdir = f"{os.path.dirname(BASE_DIR)}/static"
                                    css = [f"{cssdir}/css/bootstrap.min.css", f"{cssdir}/css/style.css",
                                           f"{cssdir}/admin_section/css/admin.css"]
                                    imgkit.from_string(headertablestring + tables[0] + footertablestring,
                                                       output_path=imgaddress,
                                                       options=options, css=css)

                                    crop_image(imgfile=imgaddress)
                                    bot.send_photo(user_ids=userid, filepath=imgaddress,
                                                   thread_id=message_info['thread_id'])

                                    print("image sent")
                                    if notify:
                                        image_caption = f"We'll notify you shortly for {slot_str} {age_str} and {dose_str}.\n" \
                                                        f"Click this link to unsubscribe https://{domain2}/{data['code']}\n" \
                                                        f"Click here for more information {url}\n" \
                                                        f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in"
                                    else:
                                        image_caption = f"Total {slot_str} {age_str} and {dose_str}\n" \
                                                        f"Click here for more information {url}\n" \
                                                        f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in"

                                    bot.send_message(text=image_caption, user_ids=userid,
                                                     thread_id=message_info['thread_id'])
                                    os.remove(imgaddress)

                                else:
                                    time.sleep(2)
                                    if notify:
                                        nomatch_caption = f"{tables['error']}\n" \
                                                          f"We'll notify you shortly for {slot_str} {age_str} and {dose_str}.\n" \
                                                          f"Click this link to unsubscribe https://{domain2}/{data['code']}\n" \
                                                          f"Click here for more information {url}\n" \
                                                          f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in"
                                    else:
                                        nomatch_caption = f"{tables['error']}\n" \
                                                          f"Click here for more information {url}\n" \
                                                          f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in"

                                    for line in nomatch_caption.replace("https://", "").split('\n'):
                                        bot.send_message(text=line, user_ids=userid)
                            else:
                                time.sleep(2)
                                nomatch_caption = f"No Matching State or District found with name: {messagestring}.\n" \
                                                  f"Visit our website for more information https://{domain}\n" \
                                                  f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in\n" \
                                                  f"Enter 'usage' to get usage information"

                                for line in nomatch_caption.replace("https://", "").split('\n'):
                                    bot.send_message(text=line, user_ids=userid)
                        else:
                            caption = f"Enter 'place name age=18/45 dose=1/2'\nAdd 'notify' for hourly notification."

                            for line in caption.replace("https://", "").split('\n'):
                                bot.send_message(text=line, user_ids=userid)
        else:
            print(f"No unread messages")
        if messages_json['pending_requests_total'] > 0:
            bot.approve_pending_thread_requests()
        else:
            print("sleeping")
            time.sleep(60)
        # return fetch_unread_messages(bot=bot)


def mainfunction(proxy=None):
    if proxy is None:
        bot = Bot(save_logfile=False)
    else:
        print("using proxy: {}".format(proxy))
        bot = Bot(save_logfile=False, proxy=proxy)
    print("Login Successfull")
    time.sleep(1)
    bot.login(username="INSTA_USERNAME", password="INSTA_PASSWORD")  # Login !!Important

    fetch_unread_messages(bot=bot)


# proxies = open("{}/proxies.txt".format(BASE_DIR)).read().split("\n")  # List of proxies by https://proxy.webshare.io/
if __name__ == '__main__':
    mainfunction()
