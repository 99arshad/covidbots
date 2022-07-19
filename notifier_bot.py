import os
import random
import string
import sys
from datetime import datetime, timedelta
from sys import platform as _platform
import boto3
import discord
import imgkit
import mysql.connector
import praw
import telegram
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fake_headers import Headers
from pytz import timezone

headers = Headers(headers=True)
BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")
sys.path.append(BASE_DIR)

from functions_ import options, fetchCentersData, centers_to_html_table, centers_to_reddit_table, \
    centers_to_email_table, centers_to_sms_table, notify_accepted_str, crop_image, \
    domain

if _platform == "linux" or _platform == "linux2":
    def dbconnector():
        return mysql.connector.connect(
            host='localhost',
            user='centersdatabase',
            password="centersuser",
            port=3306,
            database='centersdatabase',
            charset='utf8mb4'

        )
else:
    def dbconnector():
        return mysql.connector.connect(
            host='localhost',
            user='root',
            port=3306,
            database='centersdatabase',
        )


class USER:
    def __init__(self):
        PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")
        load_dotenv("{}/cvsdirectory/awskeys.env".format(PYTHON_DIR))
        self.mydb = dbconnector()
        self.connection = self.mydb.cursor(dictionary=True)

        self.clientemail = boto3.client('ses', aws_access_key_id=str(os.getenv('AWSAccessKeyId')),
                                        aws_secret_access_key=str(os.getenv('AWSSecretKey')), region_name='us-east-1')
        self.clientsms = boto3.client("sns",
                                      aws_access_key_id=str(os.getenv('AWSAccessKeyId')),
                                      aws_secret_access_key=str(os.getenv('AWSSecretKey')), region_name='us-east-1')
        self.reddit_bot = praw.Reddit(
            username='REDDIT_USERNAME',  # The username of your bot
            password='REDDIT_PASSWORD',  # The password to your bots account
            client_id='REDDIT_CLIENTID',  # Your bots client ID
            client_secret='REDDIT_SECRET',  # Your bots client secret
            user_agent='Covistan')  # A short, unique description.

        self.telegram_bot = telegram.Bot(token="TELEGRAM_TOKEN")

    def update_timestamp(self, code):
        try:
            current_timestamp = int(datetime.now(timezone("Asia/Kolkata")).timestamp())
            self.connection.execute('UPDATE userdatabase SET timestamp = %s WHERE code = %s ',
                                    (current_timestamp, code,))
            self.mydb.commit()
        except Exception as exception_error:
            return print(exception_error)

    def closeall(self):
        self.mydb.close()

    def get_all_users(self):
        yesterday_timestamp = int((datetime.now(timezone("Asia/Kolkata")) + timedelta(days=-1)).timestamp())
        self.connection.execute('SELECT * FROM userdatabase WHERE  status= "on"')
        all_users = self.connection.fetchall()
        if len(all_users) > 0:
            return all_users
        return None

    def send_notification(self, userdata, centers_data, session_data):
        if userdata['type'] == "sms":
            print(f"Sending sms to {userdata['phone']}")
            self.sendmessage(userdata, centers_data)
        if userdata['type'] == "email":
            print(f"Sending email to {userdata['email']}")
            self.mail(userdata, centers_data, session_data)
        if userdata['type'] == "reddit":
            print(f"Sending reddit message to {userdata['name']}")
            self.redditnotify(userdata, centers_data, session_data)
        if userdata['type'] == "telegram":
            print(f"Sending telegram message to {userdata['chat_id']}")
            self.telenotify(userdata, centers_data, session_data)
        if userdata['type'] == "discord":
            print(f"Sending discord message to {userdata['chat_id']}")
            self.discordnotify(userdata, centers_data, session_data)

    def mail(self, userdata, centers_data, session_data, sender_email="noreply@bookmeth.com"):
        SENDER = f"Vaccination alert <{sender_email}>"
        RECIPIENT = userdata['email']

        CHARSET = "UTF-8"

        code_url = f"https://{domain}/rm/{userdata['code']}"
        slot_str, age_str, dose_str, url = notify_accepted_str(userdata)

        BODY_HTML = str(open(f"{BASE_DIR}/email_template.html").read()).replace("weblink", url).replace(
            "unsubscribe_link",
            code_url)
        name = ""
        if userdata['name'] != "":
            name = f"To {userdata['name']}"
        BODY_HTML = BODY_HTML.replace("reciever_name", name)
        BODY_HTML = BODY_HTML.replace('__title__', f"Notified for {slot_str} {age_str} and {dose_str}")

        table_html = centers_to_email_table(centerslist=centers_data, dates=session_data)
        BODY_HTML = BODY_HTML.replace("table_dataframe", table_html)

        SUBJECT = f"Notified for {slot_str} {age_str} and {dose_str}"
        try:
            response = self.clientemail.send_email(
                Destination={
                    'ToAddresses': [
                        RECIPIENT,
                    ],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': BODY_HTML,
                        },
                    },
                    'Subject': {
                        'Charset': CHARSET,
                        'Data': SUBJECT,
                    },
                },
                Source=SENDER,

                # ConfigurationSetName="ConfigSet",
            )
        # Display an error if something goes wrong.
        except ClientError as e:
            print("error", e.response['Error']['Message'])
        else:
            print("Email sent! Message ID:"),
            print(response['MessageId'])

    def redditnotify(self, userdata, centers_data, session_data):
        code_url = f"https://{domain}/rm/{userdata['code']}"
        slot_str, age_str, dose_str, url = notify_accepted_str(userdata)

        subject = f"Notified for {slot_str} {age_str} and {dose_str}"

        table_reddit = centers_to_reddit_table(centerslist=centers_data, dates=session_data)

        table_reddit = f"{subject}:\n\n{table_reddit}\nFor more information.Visit {url}." \
                       f"\nClick this link to unsubscribe.{code_url}"
        # self.reddit_bot.redditor(userdata['name']).message(subject=subject, message=table_reddit)

    def discordnotify(self, userdata, centers_data, session_data):

        tables = centers_to_html_table(centerslist=centers_data, dates=session_data)
        code_url = f"https://{domain}/rm/{userdata['code']}"
        slot_str, age_str, dose_str, url = notify_accepted_str(userdata)
        client = discord.Client()

        @client.event
        async def on_ready():
            await client.wait_until_ready()
            user = await client.fetch_user(user_id=userdata['chat_id'])
            for table in tables[:2]:
                imgname = ''.join(
                    random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in
                    range(18))
                imgaddress = f'{BASE_DIR}/temp_images/{imgname}.jpg'
                cssdir = f"{os.path.dirname(BASE_DIR)}/static"
                css = [f"{cssdir}/css/bootstrap.min.css", f"{cssdir}/css/style.css",
                       f"{cssdir}/admin_section/css/admin.css"]
                imgkit.from_string(table, imgaddress, options=options, css=css)
                crop_image(imgfile=imgaddress)
                await user.send(file=discord.File(imgaddress))
                os.remove(imgaddress)
            await user.send(f'Click this URL : {url} for more information.')
            await user.send(f'Click this URL : {code_url} to unsubscribe.')
            await user.send(f"Notified for {slot_str} {age_str} and {dose_str}")
            await client.logout()

        if not client.is_closed():
            client.run('DISCORD_TOKEN')
        # fobject=open(f"{BASE_DIR}/temp_txt.txt","w")
        # fobject.write(str(userdata)+"\n"+str(tables))
        # fobject.close()
        # os.popen(f"{python_initial} {BASE_DIR}/discord_temp.py").read()

    def sendmessage(self, userdata, centers_data):
        localtime = (datetime.now(timezone("Asia/Kolkata")))

        emailtime = localtime.strftime("%I:%M %p")

        code_url = f"https://{domain}/rm/{userdata['code']}"

        slot_str, age_str, dose_str, url = notify_accepted_str(userdata)
        tablestring = centers_to_sms_table(centerslist=centers_data)
        message = f'Notified for {slot_str} {age_str} and {dose_str}.\r{tablestring}Updated at: {emailtime} IST.\n\n' \
                  f'Click this link for more information:{url}\n\nClick this link to unsubscibe.{code_url}'
        print(message)
        response = self.clientsms.publish(
            PhoneNumber=userdata['phone'],
            Message=message,
            Subject=f"Notified for {slot_str} {age_str} and {dose_str}",
            MessageStructure='string'

        )
        return print(response)

    def telenotify(self, userdata, centers_data, session_data):
        code_url = f"https://{domain}/rm/{userdata['code']}"
        tables = centers_to_html_table(centerslist=centers_data, dates=session_data)
        for table in tables:
            imgname = ''.join(
                random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(18))
            imgaddress = f'{BASE_DIR}/temp_images/{imgname}.jpg'
            cssdir = f"{os.path.dirname(BASE_DIR)}/static"
            css = [f"{cssdir}/css/bootstrap.min.css", f"{cssdir}/css/style.css",
                   f"{cssdir}/admin_section/css/admin.css"]

            imgkit.from_string(table, imgaddress, options=options, css=css)
            crop_image(imgfile=imgaddress)
            self.telegram_bot.send_photo(chat_id=userdata['chat_id'], photo=open(imgaddress, 'rb'))
            os.remove(imgaddress)
        slot_str, age_str, dose_str, url = notify_accepted_str(userdata)

        self.telegram_bot.send_message(chat_id=userdata['chat_id'],
                                       text=f'<a href="{url}">Click Here</a> for more information.',
                                       parse_mode='HTML')
        self.telegram_bot.send_message(chat_id=userdata['chat_id'],
                                       text=f'<a href="{code_url}">Click Here</a> to unsubscribe.',
                                       parse_mode='HTML')

        self.telegram_bot.send_message(chat_id=userdata['chat_id'], text=f"Notified for {slot_str} {age_str} and "
                                                                         f"{dose_str}")

        return print("Notification Send!")


if __name__ == '__main__':
    notifier = USER()
    usersdata = notifier.get_all_users()
    usersdata.reverse()
    for user_data in usersdata:
        notify_info = fetchCentersData(maindict=user_data, notify=True)
        if 'error' not in notify_info:
            centersdata, sessiondata = notify_info
            try:
                notifier.send_notification(user_data, centersdata, sessiondata)
            except RuntimeError as error:
                print(error)
            notifier.update_timestamp(code=user_data['code'])
        else:
            print(notify_info)

    notifier.closeall()

print("All Notifications send")
