import os
import random
import re
import string
import sys

import imgkit
from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,

)

BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")
sys.path.append(BASE_DIR)

from functions_ import total_states_districts, options, get_data_from_url, notification, fetchCentersData, \
    notify_accepted_str, crop_image, domain2

START, CHOOSING, TYPE_CHOOSING, LOCATION_CHOOSING, PINCODE_CHOOSING, STATE_CHOOSING, \
DISTRICT_CHOOSING, SELECT_AGE, SELECT_DOSE, TYPING_REPLY, TYPING_CHOICE, EXIT_COMMAND = range(12)
total_states_and_districts = total_states_districts()


def start(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()
    update.message.reply_text(
        "Select for what you wish to do.",
        reply_markup=ReplyKeyboardMarkup([['Show Available Slots', 'Get Notified'], ['Exit']], one_time_keyboard=True),
    )

    return CHOOSING


def stateorpin(update: Update, context: CallbackContext) -> int:
    choicetype = update.message.text
    context.user_data['type'] = choicetype
    if choicetype == "Get Notified" or choicetype == "Show Available Slots":
        update.message.reply_text(f'Select Type!',
                                  reply_markup=ReplyKeyboardMarkup([["Pincode", "State", "Location"], ["Go Back"]],
                                                                   one_time_keyboard=True),
                                  )
        return TYPE_CHOOSING
    elif choicetype == "Exit":
        update.message.reply_text(
            "See you again. :)", reply_markup=ReplyKeyboardRemove())
        update.message.reply_text(f'/start to start the conversation',
                                  reply_markup=ReplyKeyboardRemove(), )

        context.user_data.clear()
        return ConversationHandler.END

    update.message.reply_text(
        "Enter from options available.",
        reply_markup=ReplyKeyboardMarkup([['Show Available Slots', 'Get Notified'], ['Exit']], one_time_keyboard=True),
    )

    return CHOOSING


def displaychoice(update: Update, context: CallbackContext) -> int:
    choice = update.message.text
    if choice == "Go Back":
        update.message.reply_text(
            "Select for what you wish to do.",
            reply_markup=ReplyKeyboardMarkup([['Show Available Slots', 'Get Notified'], ['Exit']],
                                             one_time_keyboard=True),
        )

        return CHOOSING
    context.user_data['choice'] = choice.lower()
    if choice == "State":
        states = [[v['state_name']] for k, v in total_states_and_districts.items()]
        states.append(['Go Back'])
        update.message.reply_text(f'Select State!',
                                  reply_markup=ReplyKeyboardMarkup(states,
                                                                   one_time_keyboard=True),
                                  )
        return STATE_CHOOSING
    elif choice == "Pincode":
        update.message.reply_text(f'Enter Your pincode',
                                  reply_markup=ReplyKeyboardMarkup([['Go Back']], one_time_keyboard=True), )

        return PINCODE_CHOOSING
    elif choice == "Location":
        update.message.reply_text(f'Allow your location',
                                  reply_markup=ReplyKeyboardMarkup(
                                      [[KeyboardButton(text="Send Live Location", request_location=True)], ['Go Back']],
                                      one_time_keyboard=True))

        return LOCATION_CHOOSING

    else:
        update.message.reply_text(f'Invalid Type. Try again',
                                  reply_markup=ReplyKeyboardMarkup([["Pincode", "State", "Location"], ["Go Back"]],
                                                                   one_time_keyboard=True),
                                  )
        return TYPE_CHOOSING


def state_choosing(update: Update, context: CallbackContext) -> int:
    state = update.message.text
    if state == "Go Back":
        update.message.reply_text(f'Select Type!',
                                  reply_markup=ReplyKeyboardMarkup([["Pincode", "State", "Location"], ["Go Back"]],
                                                                   one_time_keyboard=True),
                                  )
        return TYPE_CHOOSING
    context.user_data['state_name'] = state
    for state_id, state_data in total_states_and_districts.items():
        if state == state_data['state_name']:
            context.user_data['state_id'] = state_id
            url = f"https://api.cowin.gov.in/api/v2/admin/location/districts/{state_id}"
            response_json = get_data_from_url(url=url)
            if "error" in response_json:
                states = [[v['state_name']] for k, v in total_states_and_districts.items()]
                states.append(['Go Back'])
                update.message.reply_text(f'{response_json["error"]}!Try again.',
                                          reply_markup=ReplyKeyboardMarkup(states,
                                                                           one_time_keyboard=True),
                                          )
                return STATE_CHOOSING

            districts_data = response_json["districts"]
            districts_list = [[district["district_name"]] for district in districts_data]
            districts_list.insert(0, ["Get all districts"])
            districts_list.append(["Go Back"])
            update.message.reply_text(f'Select District!',
                                      reply_markup=ReplyKeyboardMarkup(districts_list, one_time_keyboard=True))
            return DISTRICT_CHOOSING
    states = [[v['state_name']] for k, v in total_states_and_districts.items()]
    states.append(['Go Back'])
    update.message.reply_text(f'Invalid State name. Please Select a valid State name!',
                              reply_markup=ReplyKeyboardMarkup(states,
                                                               one_time_keyboard=True),
                              )
    return STATE_CHOOSING


def pincode_choosing(update: Update, context: CallbackContext) -> int:
    pincode = update.message.text
    if pincode == "Go Back":
        update.message.reply_text(f'Select Type!',
                                  reply_markup=ReplyKeyboardMarkup([["Pincode", "State", "Location"], ["Go Back"]],
                                                                   one_time_keyboard=True),
                                  )
        return TYPE_CHOOSING
    try:
        pincode = int(pincode)
        if len(str(pincode)) == 6:
            context.user_data['pincode'] = pincode
            update.message.reply_text(f'Select Age!',
                                      reply_markup=ReplyKeyboardMarkup(
                                          [["Age 18+", "Age 45+", 'Both'], ["Go Back"]],
                                          one_time_keyboard=True),
                                      )
            return SELECT_AGE
    except Exception as error:
        print(error)
    update.message.reply_text(f'Invalid Pincode. Please Enter a valid Pincode!',
                              reply_markup=ReplyKeyboardMarkup([['Go Back']], one_time_keyboard=True), )

    return PINCODE_CHOOSING


def location_choosing(update: Update, context: CallbackContext) -> int:
    location = update.message.location
    if location is None:
        text = update.message.text
        if text == "Go Back":
            update.message.reply_text(f'Select Type!',
                                      reply_markup=ReplyKeyboardMarkup([["Pincode", "State", "Location"], ["Go Back"]],
                                                                       one_time_keyboard=True),
                                      )
            return TYPE_CHOOSING

    try:
        context.user_data.update(location.to_dict())
        update.message.reply_text(f'Select Age!',
                                  reply_markup=ReplyKeyboardMarkup(
                                      [["Age 18+", "Age 45+", 'Both'], ["Go Back"]],
                                      one_time_keyboard=True),
                                  )

        return SELECT_AGE
    except Exception as error:
        print(error)
    update.message.reply_text(f'Invalid location. Please try again or choose different method.!',
                              reply_markup=ReplyKeyboardMarkup(
                                  [[KeyboardButton(text="Send live location", request_location=True)], ['Go Back']],
                                  one_time_keyboard=True))

    return LOCATION_CHOOSING


def district_choosing(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text == "Go Back":
        states = [[v['state_name']] for k, v in total_states_and_districts.items()]
        states.append(['Go Back'])
        update.message.reply_text(f'Select State!',
                                  reply_markup=ReplyKeyboardMarkup(states,
                                                                   one_time_keyboard=True),
                                  )
        return STATE_CHOOSING

    if text != "Get all districts":
        if context.user_data['state_id'] in total_states_and_districts:
            for district_data in total_states_and_districts[context.user_data['state_id']]['districts']:
                if text == district_data['district_name']:
                    context.user_data['district_id'] = str(district_data['district_id'])
                    context.user_data['district_name'] = text

    else:
        context.user_data['district_name'] = "*"
        context.user_data['district_id'] = "*"

    if 'district_id' in context.user_data:
        update.message.reply_text(f'Select Age!',
                                  reply_markup=ReplyKeyboardMarkup(
                                      [["Age 18+", "Age 45+", 'Both'], ["Go Back"]],
                                      one_time_keyboard=True),
                                  )
        return SELECT_AGE
    else:
        state_id = context.user_data['state_id']
        url = f"https://api.cowin.gov.in/api/v2/admin/location/districts/{state_id}"
        response_json = get_data_from_url(url=url)
        if "error" in response_json:
            states = [[v['state_name']] for k, v in total_states_and_districts.items()]
            states.append(['Go Back'])
            update.message.reply_text(f'{response_json["error"]}!Try again.',
                                      reply_markup=ReplyKeyboardMarkup(states,
                                                                       one_time_keyboard=True),
                                      )
            return STATE_CHOOSING
        districts_data = response_json["districts"]
        districts_list = [[district["district_name"]] for district in districts_data]
        districts_list.insert(0, ["Get all districts"])
        districts_list.append(["Go Back"])
        update.message.reply_text(f'Invalid District. Please Select a valid District!',
                                  reply_markup=ReplyKeyboardMarkup(districts_list, one_time_keyboard=True))
        return DISTRICT_CHOOSING


def select_age(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text == "Go Back":
        if context.user_data['choice'] == "state":
            state_id = context.user_data['state_id']
            url = f"https://api.cowin.gov.in/api/v2/admin/location/districts/{state_id}"
            response_json = get_data_from_url(url=url)
            if "error" in response_json:
                update.message.reply_text(
                    f"{response_json['error']}",
                    reply_markup=ReplyKeyboardRemove(),
                )
                context.user_data.clear()
                return ConversationHandler.END
            districts_data = response_json["districts"]
            districts_list = [[district["district_name"]] for district in districts_data]
            districts_list.insert(0, ["Get all districts"])
            districts_list.append(["Go Back"])
            update.message.reply_text(f'Select District!',
                                      reply_markup=ReplyKeyboardMarkup(districts_list, one_time_keyboard=True))
            return DISTRICT_CHOOSING
        else:
            update.message.reply_text(f'Enter Your pincode')

            return PINCODE_CHOOSING
    if text != "Both":
        age = re.findall(r'\d+', text)
        if len(age) == 1:
            age = int(age[-1])
    else:
        age = "Both"
    if age == 18 or age == 45 or age == "Both":
        if age == "Both":
            context.user_data['age'] = "*"
        else:
            context.user_data['age'] = age

        update.message.reply_text(f'Select Dose Type!',
                                  reply_markup=ReplyKeyboardMarkup(
                                      [["Dose 1", "Dose 2", "Both"], ["Go Back"]],
                                      one_time_keyboard=True),
                                  )
        return SELECT_DOSE
    update.message.reply_text(f'Select Valid Age! 18 OR 45',
                              reply_markup=ReplyKeyboardMarkup(
                                  [["Age 18+", "Age 45+", 'Both'], ["Go Back"]],
                                  one_time_keyboard=True),
                              )
    return SELECT_AGE


def select_dose(update: Update, context: CallbackContext):
    context.user_data['chat_id'] = update.message.chat_id

    text = update.message.text
    if text == "Go Back":
        update.message.reply_text(f'Select Age!',
                                  reply_markup=ReplyKeyboardMarkup(
                                      [["Age 18+", "Age 45+", 'Both'], ["Go Back"]],
                                      one_time_keyboard=True),
                                  )
        return SELECT_AGE
    if text == "Dose 1" or text == "Dose 2" or text == "Both":
        if text == "Dose 1":
            context.user_data['dose'] = 1
        elif text == "Dose 2":
            context.user_data['dose'] = 2
        else:
            context.user_data['dose'] = "*"

        user_data = context.user_data
        if user_data['choice'] == "pincode":
            user_data.update({"ntfy": "pn"})
        elif user_data['choice'] == "location":
            user_data.update({"ntfy": "ln"})
        else:
            if user_data['district_name'] == "*":
                user_data.update({"ntfy": "st"})
            else:
                user_data.update({"ntfy": "ds"})
        update.message.reply_text(text="Retrieving information. Please wait a while.")
        print(user_data)
        slot_str, age_str, dose_str, url = notify_accepted_str(userdata=user_data)
        tables = fetchCentersData(maindict=user_data, telebot=True)
        try:
            if "error" not in tables:
                table, dataitems = tables
                showing = dataitems['showing']
                total = dataitems['total']
                tablehead = {}
                tablehead.update(user_data)
                tablehead.pop("choice") if "choice" in tablehead else ""
                tablehead.pop("type") if "type" in tablehead else ""
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
                update.message.reply_photo(photo=open(imgaddress, 'rb'))
                os.remove(imgaddress)

                update.message.reply_html(f'<a href="{url}">Click Here</a> for more information.',
                                          reply_markup=ReplyKeyboardRemove()
                                          )

            else:
                update.message.reply_text(f'{tables["error"]}',
                                          reply_markup=ReplyKeyboardRemove(), )

            if user_data['type'] == 'Get Notified':
                user_data.pop("type")
                user_data.pop("choice")
                user_data = notification(rawdata=user_data, telebot=True)

                update.message.reply_text(
                    f"We'll notify you shortly for {slot_str} {age_str} and {dose_str}",
                    reply_markup=ReplyKeyboardRemove(),
                )
                update.message.reply_html(
                    f'<a href="https://{domain2}/{user_data["code"]}">Click Here</a> to unsubscribe.',
                    reply_markup=ReplyKeyboardRemove()
                )
                update.message.reply_text(f'/start to start the conversation',
                                          reply_markup=ReplyKeyboardRemove(), )
                user_data.clear()
                return ConversationHandler.END
            elif user_data['type'] == "Show Available Slots":
                update.message.reply_text(
                    f"Until next time!",
                    reply_markup=ReplyKeyboardRemove(),
                )
                update.message.reply_text(f'/start to start the conversation',
                                          reply_markup=ReplyKeyboardRemove(), )

                user_data.clear()
                return ConversationHandler.END
            else:
                update.message.reply_text(
                    "Enter Valid option.",
                    reply_markup=ReplyKeyboardMarkup([['Show Available Slots', 'Get Notified'], ['Exit']],
                                                     one_time_keyboard=True),
                )

                return CHOOSING
        except Exception as error:
            update.message.reply_text(f'Error: {error}',
                                      reply_markup=ReplyKeyboardRemove(), )
            update.message.reply_text(f'/start to start the conversation',
                                      reply_markup=ReplyKeyboardRemove(), )
            user_data.clear()
            return ConversationHandler.END

    update.message.reply_text(f'Select Valid Dose Type!',
                              reply_markup=ReplyKeyboardMarkup(
                                  [["Dose 1", "Dose 2", "Both"], ["Go Back"]],
                                  one_time_keyboard=True),
                              )
    return SELECT_DOSE


def main():
    print("Starting Telegram Bot")
    updater = Updater("TELEGRAM_TOKEN")
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START: [
                MessageHandler(
                    Filters.regex('^startt$'), start
                ),
            ],

            CHOOSING: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^typechoosing$')), stateorpin
                ),
            ],

            TYPE_CHOOSING: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^state|pincode|location$')), displaychoice
                )
            ],

            PINCODE_CHOOSING: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^pincode$')), pincode_choosing
                )
            ],
            LOCATION_CHOOSING: [
                MessageHandler((Filters.text | Filters.command | Filters.location), location_choosing
                               )
            ],

            STATE_CHOOSING: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^statename$')), state_choosing
                )
            ],
            DISTRICT_CHOOSING: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^districtname$')), district_choosing
                )
            ],
            SELECT_AGE: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^age$')), select_age
                )
            ],
            SELECT_DOSE: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^dosetype$')), select_dose
                )
            ],
        },
        fallbacks=[MessageHandler(Filters.text & ~(Filters.command | Filters.regex('^exit$')), START)],
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()
