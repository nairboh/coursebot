import os
import json
import time
from slackclient import SlackClient
from uwaterlooapi import UWaterlooAPI

BOT_ID = os.environ.get("BOT_ID")
BOT_NAME = "cb"

AT_BOT_NAME = "*@" + BOT_NAME + "*"

AT_BOT = "<@" + BOT_ID + ">"
EXAMPLE_COMMAND = "do"

SLACK_CLIENT = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
UW_CLIENT = UWaterlooAPI(api_key=os.environ.get('UW_TOKEN'))

def parse_course_command(s):
    string_length = len(s)
    alpha_pos = 1

    while alpha_pos < string_length and s[alpha_pos].isalpha():
        alpha_pos += 1

    numer_pos = alpha_pos
    while numer_pos < string_length and not s[numer_pos].isdigit():
        numer_pos += 1

    return (s[:alpha_pos], s[numer_pos:])

def get_course_info(course):
    subject = course[0]
    catalog_num = course[1]

    valid_query = subject and catalog_num

    if valid_query:
        return UW_CLIENT.course(subject, catalog_num), valid_query

    return None, valid_query

def get_formatted_json(s):
    subject = s['subject']
    catalog_num = s['catalog_number']
    title = s['title']
    url = s['url']

    return (("<" + url + "|*" + subject + catalog_num + " - " + title + "*>") \
           if url and subject and catalog_num and title else "")

def handle_command(command, channel):
    response = "Invalid query. Note that a sample invocation would be " \
               + AT_BOT_NAME + " CS247"

    course_info = get_course_info(parse_course_command(command))
    course_json = course_info[0]
    valid_query = course_info[1]

    attachment_resp = None

    if valid_query:
        if course_json:
            response = get_formatted_json(course_json)
            attachment_resp = json.dumps([
                {
                    "fallback" : "Error retrieving course description",
                    "text" : course_json["description"],
                    "color" : "good"
                },
                ({
                    "fields": [{
                        "title": "Prereqs",
                        "value": course_json["prerequisites"]
                    }],
                    "color" : "warning"
                } if course_json["prerequisites"] else None),
                ({
                    "fields": [{
                        "title": "Antireqs",
                        "value": course_json["antirequisites"]
                    }],
                    "color" : "danger"
                } if course_json["antirequisites"] else None)
            ])
        else:
            response = "Sorry, I have no data on this course."

    SLACK_CLIENT.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True,
                          attachments=attachment_resp)

def parse_slack_output(slack_rtm_output):
    output_list = slack_rtm_output
    if output_list:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel']
    return None, None

if __name__ == "__main__":
    SLEEP_DELAY = 1

    if SLACK_CLIENT.rtm_connect():
        print "Coursebot connected and running!"

        while True:
            COMMAND, CHANNEL = parse_slack_output(SLACK_CLIENT.rtm_read())

            if COMMAND and CHANNEL:
                handle_command(COMMAND, CHANNEL)

            time.sleep(SLEEP_DELAY)
    else:
        print "Connection failed. Check Slack token or bot ID!"
