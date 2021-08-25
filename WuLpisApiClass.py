#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import requests
# import dill
# import sys
# import base64
import datetime
import re
import os
# import hashlib
import pickle
# import unicodedata
from lxml import html
# from datetime import timedelta
# from dateutil import parser
from bs4 import BeautifulSoup
from bs4 import Comment

import mechanize
# import threading
import time
import json


class WuLpisApi():

    URL = "https://lpis.wu.ac.at/lpis"

    def __init__(self, username=None, password=None, args=None, sessiondir=None):
        self.username = username
        self.password = password
        self.matr_nr = username[1:]
        self.args = args
        self.data = {}
        self.number_reg = {}
        self.status = {}
        self.course = {}
        self.browser = mechanize.Browser()

        if sessiondir:
            self.sessionfile = sessiondir + username
        else:
            self.sessionfile = "sessions/" + username

        self.browser.set_handle_robots(False)   # ignore robots
        self.browser.set_handle_refresh(False)  # can sometimes hang without this
        self.browser.set_handle_equiv(True)
        self.browser.set_handle_redirect(True)
        self.browser.set_handle_referer(True)
        self.browser.set_debug_http(False)
        self.browser.set_debug_responses(False)
        self.browser.set_debug_redirects(True)
        self.browser.addheaders = [
            ('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'),
            ('Accept', '*/*')
        ]
        self.login()

    def login(self):
        print("init time: %s" % datetime.datetime.now())
        self.data = {}

        #if not self.load_session():
        # print "logging in ..."

        r = self.browser.open(self.URL)
        self.browser.select_form('login')

        tree = html.fromstring(re.sub(r"<!--(.|\s|\n)*?-->", "", r.read()))  # removes comments from html
        input_username = list(set(tree.xpath("//input[@accesskey='u']/@name")))[0]
        input_password = list(set(tree.xpath("//input[@accesskey='p']/@name")))[0]

        self.browser[input_username] = self.username
        self.browser[input_password] = self.password
        r = self.browser.submit()

        # get scraped LPIS url
        # looks like: https://lpis.wu.ac.at/kdcs/bach-s##/#####/
        url = r.geturl()
        self.URL_scraped = url[:url.rindex('/') + 1]

        self.data = self.URL_scraped
        #self.save_session()

        soup = BeautifulSoup(r.read(), "html.parser")
        for a in soup.find_all('a', href=True, text=True):
            if (a.string == 'Nummerneingabe'):
                self.number_reg = { 'name': str(a.string),
                                    'title': str(a.get('title')),
                                    'slag': str(a.get('href')) }

        return (self.data, self.number_reg)

    def getResults(self):
        status = self.status
        if "last_logged_in" in status:
            status["last_logged_in"] = self.status["last_logged_in"].strftime("%Y-%m-%d %H:%M:%S")
        return { "data": self.data,
                 "course": self.course,
                 "status": self.status }

    def number_registration(self):
        print("Single registration using number in the electronic course catalog ...")
        nrURL = self.data + self.number_reg['slag']
        print(nrURL)

        res = self.browser.open(nrURL)

        self.browser.select_form('ea_verid')
        tree = html.fromstring(re.sub(r"<!--(.|\s|\n)*?-->", "", res.read()))  # removes comments from html
        input_lv_number = list(set(tree.xpath('//*[@id="ea_verid"]/input[@name="verid"]/@name')))[0]
        self.browser[input_lv_number] = self.args.course

        course_signup = self.browser.submit()

        course = BeautifulSoup(course_signup.read(), "html.parser")
        logged_as = course.select_one('table:nth-child(1) > tr:nth-child(2) > td > b').get_text()
        print("\nLogged as: {}".format(logged_as))

        lv_course_data = self.lv_data_table(course)
        self.course = lv_course_data
        print("\n---------- Course information ------------")
        print(json.dumps(lv_course_data, sort_keys=False, indent=4, ensure_ascii=False).encode('utf8'))

        msg_area = course.find(text=lambda s: isinstance(s, Comment) and "Message Area" in s)
        print("\n---------- {} ------------".format(msg_area.strip()))
        # print(msg_area.strip())
        green_msg = course.find_all("span", {"style":"font-weight: bold;color: green;"})
        red_msg = course.find_all("span", {"style":"font-weight: bold;color: red;"})
        for msg in green_msg + red_msg:
            if (msg):
                print(msg.get_text())

        if (green_msg):
            # Registration available, go ahead and sign-up for the course
            print("Registration is open, signing up ...")
            # Get the registration form
            register_form = course.select_one('form[id^="verid_"]')
            form_id = register_form.get('id')
            self.browser.select_form(form_id)
            register_page = self.browser.submit()
            register = BeautifulSoup(register_page.read(), "html.parser")
            # print(register.prettify())
            success_alert = register.select_one('div.b3k_alert_success')
            if success_alert:
                print("\n---------- S U C C E S S ------------")
                print("Registration successful!")
                alert_content = register.select_one('div.b3k_alert_content').get_text(strip=True)
                print(alert_content)
                self.status = 'success'
        elif (red_msg):
            already_registered = "Veranstaltung {}".format(self.args.course)
            if any(already_registered in str(msg) for msg in red_msg):
                print("\n---------- S U C C E S S ------------")
                print("The course '{}' is already registered!\n").format(self.args.course)
                self.status = 'success'
            else:
                print("\n---------- E R R O R ------------")
                print("Registration is not possible at the moment ...\n")
                # this type of error can by re-tried again
                self.status = 'error'
        else:
            print("Can't retrieve info about registration ...\n")
            self.status = 'error'
        return self.status

    def lv_data_table(self, bs_page):
        lv_table = bs_page.select_one('table.b3k-data')
        #print(lv_table.prettify())
        lv_headers = []
        for td in lv_table.select('td.thd'):
            rows = td.select('span')
            if (rows):
                lv_headers.append(map(lambda lv: lv.get_text(strip=True), rows))
            else:
                lv_headers.append(td.get_text(strip=True))
        lv_data = []
        for td in lv_table.select('td.tdg'):
            rows = td.select('span')
            if (rows):
                lv_data.append(map(lambda lv: lv.get_text(strip=True), rows))
            else:
                lv_data.append(td.get_text(strip=True))
        lv_result = {}
        for i, lvhi in enumerate(lv_headers):
            if isinstance(lvhi, list):
                for j, lvhj in enumerate(lvhi):
                    lv_result[lvhj] = lv_data[i][j]
            else:
                lv_result[lvhi] = lv_data[i]

        # The html table is a mess, there might be another course parameters hidden inside the table.
        # Let's go through the table again and pull out info from imbalanced structures
        for i, lvdi in enumerate(lv_data):
            if (isinstance(lvdi, list) and len(lvdi) > len(lv_headers[i])):
                min_len = len(lv_headers[i])
                del lvdi[:min_len]
                t_odd = lvdi[0::2]
                t_even = lvdi[1::2]
                lv_result.update(dict(zip(t_odd, t_even)))

        print(lv_result)
        # Parse registration open and close time
        registration = {}
        if u'Anmeldefrist' in lv_result.keys():
            registration['open'], registration['close'] = lv_result['Anmeldefrist'].split(' - ')
        elif u'An- und Abmeldefrist' in lv_result.keys():
            registration['open'], registration['close'] = lv_result['An- und Abmeldefrist'].split(' - ')
        print(registration)

        lv_result.update({'registration_open': registration['open'], 'registration_close': registration['close']})

        return lv_result

    def infos(self):
        print("getting data ...")
        self.data = {}
        self.browser.select_form('ea_stupl')

        form = self.browser.form
        # Select first element in Select Options Dropdown
        item = form.find_control("ASPP").get(None, None, None, 0)
        item.selected = True

        r = self.browser.submit()
        soup = BeautifulSoup(r.read(), "html.parser")

        studies = {}
        for i, entry in enumerate(soup.find('select', {'name': 'ASPP'}).find_all('option')):
            if len(entry.text.split('/')) == 1:
                studies[i] = {}
                studies[i]['id'] = entry['value']
                studies[i]['title'] = entry['title']
                studies[i]['name'] = entry.text
                studies[i]['abschnitte'] = {}
            elif len(entry.text.split('/')) == 2 and entry.text.split('/')[0] == studies[(i - 1) % len(studies)]['name']:
                studies[(i - 1) % len(studies)]['abschnitte'][entry['value']] = {}
                studies[(i - 1) % len(studies)]['abschnitte'][entry['value']]['id'] = entry['value']
                studies[(i - 1) % len(studies)]['abschnitte'][entry['value']]['title'] = entry['title']
                studies[(i - 1) % len(studies)]['abschnitte'][entry['value']]['name'] = entry.text

        self.data['studies'] = studies

        pp = {}
        for i, planpunkt in enumerate(soup.find('table', {"class": "b3k-data"}).find('tbody').find_all('tr')):
            # if planpunkt.find('a', title='Lehrveranstaltungsanmeldung'):
            if planpunkt.select('td:nth-of-type(2)')[0].text:
                key = planpunkt.a['id'][1:]
                pp[key] = {}
                pp[key]["order"] = i + 1
                pp[key]["depth"] = int(re.findall('\\d+', planpunkt.select('td:nth-of-type(1)')[0]['style'])[0]) / 16
                pp[key]["id"] = key
                pp[key]["type"] = planpunkt.select('td:nth-of-type(1) span:nth-of-type(1)')[0].text.strip()
                pp[key]["name"] = planpunkt.select('td:nth-of-type(1) span:nth-of-type(2)')[0].text.strip()

                if planpunkt.select('a[href*="DLVO"]'):
                    pp[key]["lv_url"] = planpunkt.select('a[href*="DLVO"]')[0]['href']
                    pp[key]["lv_status"] = planpunkt.select('a[href*="DLVO"]')[0].text.strip()
                if planpunkt.select('a[href*="GP"]'):
                    pp[key]["prf_url"] = planpunkt.select('a[href*="GP"]')[0]['href']

                if '/' in planpunkt.select('td:nth-of-type(2)')[0].text:
                    pp[key]["attempts"] = planpunkt.select('td:nth-of-type(2) span:nth-of-type(1)')[0].text.strip()
                    pp[key]["attempts_max"] = planpunkt.select('td:nth-of-type(2) span:nth-of-type(2)')[0].text.strip()

                if planpunkt.select('td:nth-of-type(3)')[0].text.strip():
                    pp[key]["result"] = planpunkt.select('td:nth-of-type(3)')[0].text.strip()
                if planpunkt.select('td:nth-of-type(4)')[0].text.strip():
                    pp[key]["date"] = planpunkt.select('td:nth-of-type(4)')[0].text.strip()

                if 'lv_url' in pp[key]:
                    r = self.browser.open(self.URL_scraped + pp[key]["lv_url"])
                    soup = BeautifulSoup(r.read(), "html.parser")
                    pp[key]['lvs'] = {}

                    if soup.find('table', {"class": "b3k-data"}):
                        for lv in soup.find('table', {"class": "b3k-data"}).find('tbody').find_all('tr'):
                            number = lv.select('.ver_id a')[0].text.strip()
                            pp[key]['lvs'][number] = {}
                            pp[key]['lvs'][number]['id'] = number
                            pp[key]['lvs'][number]['semester'] = lv.select('.ver_id span')[0].text.strip()
                            pp[key]['lvs'][number]['prof'] = lv.select('.ver_title div')[0].text.strip()
                            pp[key]['lvs'][number]['name'] = lv.find('td', {"class": "ver_title"}).findAll(
                                text=True, recursive=False)[1].strip()
                            pp[key]['lvs'][number]['status'] = lv.select('td.box div')[0].text.strip()
                            capacity = lv.select('div[class*="capacity_entry"]')[0].text.strip()
                            pp[key]['lvs'][number]['free'] = capacity[:capacity.rindex('/') - 1]
                            pp[key]['lvs'][number]['capacity'] = capacity[capacity.rindex('/') + 2:]

                            if lv.select('td.action form'):
                                internal_id = lv.select('td.action form')[0]['name']
                                pp[key]['lvs'][number]['internal_id'] = internal_id.rsplit('_')[1]
                            date = lv.select('td.action .timestamp span')[0].text.strip()

                            if 'ab' in date:
                                pp[key]['lvs'][number]['date_start'] = date[3:]
                            if 'bis' in date:
                                pp[key]['lvs'][number]['date_end'] = date[4:]

                            if lv.select('td.box.active'):
                                pp[key]['lvs'][number]['registerd_at'] = lv.select(
                                    'td.box.active .timestamp span')[0].text.strip()

                            if lv.select('td.capacity div[title*="Anzahl Warteliste"]'):
                                pp[key]['lvs'][number]['waitlist'] = lv.select(
                                    'td.capacity div[title*="Anzahl Warteliste"]')[0].text.strip()

        self.data['pp'] = pp
        return self.data

    def registration(self):
        self.browser.select_form('ea_stupl')

        form = self.browser.form
        # Select first element in Select Options Dropdown
        item = form.find_control("ASPP").get(None, None, None, 0)
        item.selected = True

        # timeserver = "timeserver.wu.ac.at"
        # print "syncing time with \"%s\"" % timeserver
        # os.system('sudo ntpdate -u %s' % timeserver)
        offset = 1.0  # seconds before start time when the request should be made
        if self.args.planobject and self.args.course:
            pp = "S" + self.args.planobject
            lv = self.args.course
            lv2 = self.args.course2

        self.data = {}
        self.browser.select_form('ea_stupl')
        r = self.browser.submit()
        soup = BeautifulSoup(r.read(), "html.parser")

        url = soup.find('table', {"class": "b3k-data"}).find('a', id=pp).parent.find('a', href=True)["href"]
        r = self.browser.open(self.URL_scraped + url)

        triggertime = 0
        soup = BeautifulSoup(r.read(), "html.parser")
        date = soup.find('table', {"class": "b3k-data"}).find('a',
                                                              text=lv).parent.parent.select('.action .timestamp span')[0].text.strip()
        if 'ab' in date:
            triggertime = time.mktime(datetime.datetime.strptime(date[3:], "%d.%m.%Y %H:%M").timetuple()) - offset
            if triggertime > time.time():
                print("waiting: %.2f seconds (%.2f minutes)" %
                      ((triggertime - time.time()), (triggertime - time.time()) / 60))
                print("waiting till: %s (%s)" % (triggertime, time.strftime(
                    "%d.%m.%Y %H:%M:%S", time.localtime(triggertime))))
                time.sleep(triggertime - time.time())

        print("triggertime: %s" % triggertime)
        print("final open time start: %s" % datetime.datetime.now())

        # Reload page until registration is possible
        while True:
            print("start request %s" % datetime.datetime.now())
            r = self.browser.open(self.URL_scraped + url)
            soup = BeautifulSoup(r.read(), "html.parser")

            if soup.find('table', {"class": "b3k-data"}).find('a', text=lv).parent.parent.select('div.box.possible'):
                break
            else:
                print("parsing done %s" % datetime.datetime.now())
            print("registration is not (yet) possibe, waiting ...")
            print("reloading page and waiting for form to be submittable")

        print("final open time end: %s" % datetime.datetime.now())
        print("registration is possible")

        cap1 = soup.find('table', {"class": "b3k-data"}).find('a',
                                                              text=lv).parent.parent.select('div[class*="capacity_entry"]')[0].text.strip()
        cap2 = soup.find('table', {"class": "b3k-data"}).find('a',
                                                              text=lv2).parent.parent.select('div[class*="capacity_entry"]')[0].text.strip()
        free1 = int(cap1[:cap1.rindex('/') - 1])
        free2 = int(cap2[:cap2.rindex('/') - 1])

        form1 = soup.find('table', {"class": "b3k-data"}).find('a',
                                                               text=lv).parent.parent.select('.action form')[0]["name"].strip()
        form2 = soup.find('table', {"class": "b3k-data"}).find('a',
                                                               text=lv2).parent.parent.select('.action form')[0]["name"].strip()

        print("end time: %s" % datetime.datetime.now())
        print("freie plaetze: lv1: %s, lv2: %s (if defined)" % (free1, free2))
        if free1 > 0:
            self.browser.select_form(form1)
            print("submitting registration form1 (%s)" % form1)
        else:
            self.browser.select_form(form2)
            print("submitting registration form2 (%s)" % form2)

        r = self.browser.submit()

        soup = BeautifulSoup(r.read(), "html.parser")
        if soup.find('div', {"class": 'b3k_alert_content'}):
            print(soup.find('div', {"class": 'b3k_alert_content'}).text.strip())
            lv = soup.find('table', {"class": "b3k-data"}).find('a', text=lv).parent.parent
            print("Frei: " + lv.select('div[class*="capacity_entry"]')[0].text.strip())
            if lv.select('td.capacity div[title*="Anzahl Warteliste"]'):
                print("Warteliste: " + lv.select('td.capacity div[title*="Anzahl Warteliste"] span')[
                      0].text.strip() + " / " + lv.select('td.capacity div[title*="Anzahl Warteliste"] span')[0].text.strip())
                if free1 > 0:
                    self.browser.select_form(form2)
                    print("submitting registration form (%s)" % form)
                    r = self.browser.submit()

        if soup.find('h3'):
            print(soup.find('h3').find('span').text.strip())

    def save_session(self):
        print("trying to save session ...")
        if not os.path.exists(os.path.dirname(self.sessionfile)):
            os.makedirs(os.path.dirname(self.sessionfile))
        with open(self.sessionfile, 'wb') as file:
            # dill.dump(self.browser, file)
            pickle.dump(self.browser, file, pickle.HIGHEST_PROTOCOL)
        print("session saved to file ...")
        return True

    def load_session(self):
        print("trying to load session ...")
        if os.path.isfile(self.sessionfile):
            with open(self.sessionfile, 'rb') as file:
                self.browser = pickle.load(file)
            print("session loaded from file ...")
            return True

