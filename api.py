#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
from WuLpisApiClass import WuLpisApi
import datetime
import time


def file_parser(filepath, separator="="):
    data = {}
    for line in open(filepath, "r"):
        line = line.rstrip('\n').split(separator)
        data[line[0]] = line[1]
    return data

def run_action(user, passwd, cmd_args, sessiondir):
    api = WuLpisApi(user, passwd, cmd_args, sessiondir)
    method = getattr(api, cmd_args.action, None)
    if callable(method):
        method()
        return api.getResults()

def wait_for_open_time(open_time):
    print("Current time is: %s" % datetime.datetime.now())
    print("Registration open time: %s" % open_time)
    print('...')
    target_time = time.mktime(datetime.datetime.strptime(open_time, "%d.%m.%Y %H:%M").timetuple())
    current_time = time.time()
    wait_time = 0
    while current_time < target_time:
        time.sleep(1)
        wait_time += 1
        if (wait_time/10 == 1):
            print("Current time is: %s" % datetime.datetime.now())
            print("Registration open time: %s" % open_time)
            print('...')
            wait_time = 0
        current_time = time.time()
    print("Registration is now open: %s\n" % datetime.datetime.now())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--action', help="Which action in the programm should run", required=True)
    parser.add_argument('-c', '--credfile', help='Path to the credentials file with username and password')
    parser.add_argument('-p', '--password')
    parser.add_argument('-u', '--username')
    parser.add_argument('-s', '--sessiondir', help='Dir where the sessions should be stored')
    parser.add_argument('-pp', '--planobject',
                        help="Study plan object in which the correspondending course can be found (Studienplanpunkt")
    parser.add_argument('-lv', '--course', help="Course ID for which the registration should be done")
    parser.add_argument('-lv2', '--course2', help="Fallback (second) Course ID")
    args = parser.parse_args()

    username = file_parser(args.credfile)["username"] if args.credfile else args.username
    password = file_parser(args.credfile)["password"] if args.credfile else args.password

    while(1):
        results = run_action(username, password, args, args.sessiondir)
        print('================================================================================')
        # print(json.dumps(results, sort_keys=True, indent=4))
        if results['status'] == 'error':
            reg_open_time = time.mktime(datetime.datetime.strptime(results['course']['registration_open'], "%d.%m.%Y %H:%M").timetuple())
            # reg_open_time = reg_open_time - datetime.timedelta(seconds=10)
            reg_close_time = time.mktime(datetime.datetime.strptime(results['course']['registration_close'], "%d.%m.%Y %H:%M").timetuple())
            current_time = time.time()
            if reg_open_time < current_time < reg_close_time:
                print("Registration is open! Retrying...\n")
            elif current_time < reg_open_time:
                print("Registration is not opened yet! Waiting...\n")
                # wait_for_open_time('25.08.2021 00:22')
                wait_for_open_time(results['course']['registration_open'])
            elif current_time > reg_close_time:
                print("Registration is closed already! Aborting.\n")
                break
        elif results['status'] == 'success':
            print("Registration successful! Closing.\n")
            break

