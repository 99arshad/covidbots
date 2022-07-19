import os
import random
import re
import smtplib
import string
import sys
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import imgkit
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")
sys.path.append(BASE_DIR)
from functions_ import message_parser, options, crop_image, fetchCentersData, notify_accepted_str, notification, chrome, \
    domain, domain2

url = "https://web.whatsapp.com/"


class WhatsAppElements:
    search = (By.CSS_SELECTOR, "#side > div.SgIJV > div > label > div > div._2_1wd.copyable-text.selectable-text")


class WhatsApp:
    browser = None
    timeout = 10

    def __init__(self, wait):
        print("Starting Whatsapp bot")
        try:
            if chrome:
                self.browser = webdriver.Chrome(executable_path=f"{BASE_DIR}/driver/chromedriver.exe")  # change path
            else:
                opts = FirefoxOptions()
                opts.add_argument("--headless")
                # fp = webdriver.FirefoxProfile(f"{BASE_DIR}/_trial_temp/")
                self.browser = webdriver.Firefox(firefox_options=opts)  # change path

            self.browser.get("https://web.whatsapp.com/")  # to open the WhatsApp web
            if chrome:
                print("Waiting for scaning code")
                WebDriverWait(self.browser, wait).until(EC.presence_of_element_located(
                    (By.XPATH, '//canvas[@aria-label = "Scan me!"]')))  # wait till search element appears
            else:
                time.sleep(4)
                print("Taking Screenshot")
                self.browser.save_screenshot(f"{BASE_DIR}/ssimage.png")
                print("Image created")

                fromaddr = "#@gmail.com"
                toaddr = "#@gmail.com"
                msg = MIMEMultipart()
                msg['From'] = "#@gmail.com"
                msg['To'] = "#@gmail.com"
                msg['Subject'] = "Whatsapp image"
                body = "QR code"
                msg.attach(MIMEText(body, 'plain'))
                filename = "ssimage.png"
                attachment = open(f'{BASE_DIR}/ssimage.png', "rb")
                p = MIMEBase('application', 'octet-stream')
                p.set_payload(attachment.read())
                encoders.encode_base64(p)
                p.add_header('Content-Disposition', "attachment; filename= %s" % filename)
                msg.attach(p)
                s = smtplib.SMTP('smtp.gmail.com', 587)
                s.starttls()
                s.login(fromaddr, "#")
                text = msg.as_string()
                s.sendmail(fromaddr, toaddr, text)
                s.quit()
                print("Mail sent!")
            print("Waiting to enter code")
            WebDriverWait(self.browser, wait).until(EC.presence_of_element_located((By.XPATH, '//div[@aria-label = "Chat list"]')))
            # wait till search element appears
        except Exception as error:
            print(f"Error occured: {str(error)}")

    def goto_main(self):
        try:
            self.browser.refresh()
            Alert(self.browser).accept()
        except Exception as e:
            print(e)
        WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located(WhatsAppElements.search))

    def run_script(self):
        print("starting BOT")
        # initial = 10
        # self.browser.execute_script("document.getElementById('pane-side').scrollTop={}".format(initial))
        #self.browser.get(url)
        start = time.time()
        while True:
            # self.goto_main()
            soup = BeautifulSoup(self.browser.page_source, "html.parser")
            temp = 0
            for j in soup.find_all("div", {"data-testid":"cell-frame-container"}):
                if j.find("span", class_="_23LrM"):
                    username = j.find("span", class_="_3q9s6").text
                    temp += 1
                    self.send_message_by_title(target_user=username)
            if temp != 0:
                try:

                    self.browser.get(url)

                except:
                    pass
            time.sleep(2)
            print("sleeping")
            if time.time() - start > 600:
                start = time.time()
                self.goto_main()
        # initial += 10

    def get_last_message_for(self, name):
        messages = list()
        search = self.browser.find_element(*WhatsAppElements.search)
        search.send_keys(name + Keys.ENTER)
        time.sleep(3)
        soup = BeautifulSoup(self.browser.page_source, "html.parser")
        for i in soup.find_all("div", class_="message-in"):
            message = i.find("span", class_="selectable-text")
            if message:
                message2 = message.find("span")
                if message2:
                    messages.append(message2.text)
        messages = list(filter(None, messages))
        return messages

    def send_to_unknown_number(self, phone_number, message):
        url = "https://web.whatsapp.com/send?phone=" + phone_number + "&text=" + message + "&app_absent=1"
        self.browser.get(url)
        time.sleep(5)
        enter_action = ActionChains(self.browser)
        enter_action.send_keys(Keys.ENTER)
        enter_action.perform()

    def send_message_by_title(self, target_user):
        x_arg = '//span[contains(@title,"' + target_user + '")]'
        group_title = WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located((By.XPATH, x_arg)))
        group_title.click()
        elements = BeautifulSoup(self.browser.page_source, 'html.parser')
        try:
            last_unread_message = elements.find_all("div", {"class": "message-in"})[-1]. \
                find("span", class_="selectable-text").text
            messagestring = "".join(re.sub(r"[-()\"#/;:©<>_“”$^&…{}`'‘’%~|.!?,]", " ", str(last_unread_message)))
            if "usage" not in messagestring.lower():
                data, notify = message_parser(messagestring=messagestring)
                # input_box = self.browser.find_element_by_class_name('_2A8P4')
                tablehead = {}
                tablehead.update(data)
                if "state_id" in data or "pincode" in data:
                    tables = fetchCentersData(maindict=data, discordbot=True)
                    slot_str, age_str, dose_str, url = notify_accepted_str(userdata=data)

                    if notify:
                        data.update({"phone": target_user})
                        data = notification(rawdata=data, whatsapp=True)

                    if "error" not in tables:
                        table, dataitems = tables
                        showing = dataitems['showing']
                        total = dataitems['total']
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
                        headertablestring = '<table border="1" class="table table-responsive table-striped ' \
                                            'table-bordered" style="margin-bottom: 10px;"><thead><tr >' \
                                            + ''.join([f"<th>{k.replace('_', ' ').capitalize()}</th>" for k in
                                                       tablehead]) + '</tr></thead><tbody><tr>' \
                                            + ''.join([f"<td>{v}</td>" for v in tablehead.values()]) \
                                            + '</tr></tbody></table>'
                        footertablestring = f'<table border="1" class="table table-responsive table-striped table-bordered" ' \
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
                        imgkit.from_string(headertablestring + table + footertablestring, output_path=imgaddress,
                                           options=options, css=css)

                        crop_image(imgfile=imgaddress)
                        attachment_section = self.browser.find_element_by_xpath('//div[@title = "Attach"]')
                        attachment_section.click()
                        image_box = self.browser.find_element_by_xpath(
                            '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]')
                        image_box.send_keys(imgaddress)
                        time.sleep(2)
                        self.browser.find_element_by_class_name('_1JAUF').click()
                        if notify:
                            image_caption = f"We'll notify you shortly for *{slot_str} {age_str}* and *{dose_str}*.\n\n" \
                                            f"_Click this link to unsubscribe https://{domain2}/{data['code']}_\n" \
                                            f"_Click here for more information {url}_\n" \
                                            f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in\n"
                        else:
                            image_caption = f"Total *{slot_str} {age_str}* and *{dose_str}*\n\n" \
                                            f"_Click here for more information {url}_\n" \
                                            f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in\n"

                        for line in image_caption.replace("https://", "").split('\n'):
                            ActionChains(self.browser).send_keys(line).perform()
                            ActionChains(self.browser).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(
                                Keys.SHIFT).key_up(
                                Keys.ENTER).perform()
                        ActionChains(self.browser).send_keys(Keys.RETURN).perform()
                        # send_button = self.browser.find_element_by_xpath('//span[@data-icon="send"]')
                        # send_button.click()
                        os.remove(imgaddress)

                    else:
                        time.sleep(2)
                        if notify:
                            nomatch_caption = f"*{tables['error']}*\n" \
                                              f"_We'll notify you shortly for {slot_str} {age_str} and {dose_str}._\n\n" \
                                              f"_Click this link to unsubscribe https://{domain2}/{data['code']}_\n" \
                                              f"_Click here for more information {url}_\n" \
                                              f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in\n"
                        else:
                            nomatch_caption = f"*{tables['error']}*\n\n" \
                                              f"_Click here for more information {url}_\n" \
                                              f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in\n"

                        for line in nomatch_caption.replace("https://", "").split('\n'):
                            ActionChains(self.browser).send_keys(line).perform()
                            ActionChains(self.browser).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(Keys.SHIFT). \
                                key_up(Keys.ENTER).perform()
                        ActionChains(self.browser).send_keys(Keys.RETURN).perform()
                else:
                    time.sleep(2)
                    nomatch_caption = f"*No Matching State or District found with name: {messagestring}.*\n" \
                                      f"_Visit our website for more information https://{domain}_\n" \
                                      f"For slot booking Visit CoWin: https://selfregistration.cowin.gov.in\n" \
                                      f"Enter 'usage' to get usage information"

                    for line in nomatch_caption.replace("https://", "").split('\n'):
                        ActionChains(self.browser).send_keys(line).perform()
                        ActionChains(self.browser).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(Keys.SHIFT).key_up(
                            Keys.ENTER).perform()
                    ActionChains(self.browser).send_keys(Keys.RETURN).perform()
            else:
                caption = f"Enter 'place name age=18/45 dose=1/2'\nAdd 'notify' for hourly notification:"

                for line in caption.split('\n'):
                    ActionChains(self.browser).send_keys(line).perform()
                    ActionChains(self.browser).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(Keys.SHIFT).key_up(
                        Keys.ENTER).perform()
                ActionChains(self.browser).send_keys(Keys.RETURN).perform()

        except Exception as error:
            print(error)


WhatsApp(600).run_script()
