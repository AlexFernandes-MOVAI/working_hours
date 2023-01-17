#!/usr/bin/python3

import argparse
import os
import subprocess
from datetime import *
from typing import Union

from dateutil.parser import *
from dateutil.relativedelta import *
from termcolor import colored

""" Sort type of action

    Arg: list of string from journalctl

    Return: string

        IN, OUT, UNKNOWN (detail)

"""
def sort_action(login_action):
    is_OUT = False
    is_IN = False
    cur_user = os.getlogin()

    if login_action[0] == 'Lid':
        if login_action[1] == 'opened.':
            is_IN = True
        elif login_action[1] == 'closed.':
            is_OUT = True
    elif login_action[0] == 'Suspending...':
        is_OUT = True
    elif login_action[0] == 'Operation':
        if login_action[1] == 'Sleep' and login_action[2] == 'finished':
            is_OUT = True
    elif login_action[0] == 'New'  and login_action[1] == 'session':
        if cur_user in " ".join(login_action):
            is_IN = True

    if is_IN:
        return "IN"
    elif is_OUT:
        return "OUT"
    else:
        # print(f"UNKNOWN ({login_action})")
        return "UNKNOWN"



""" Generate a dict reporting all events received each days sorted by IN and OUT

    Args:
    - days_to_report

    Return:
    {
        "shortdate1": {
            "ins": [ "first_in", "last_in" ],
            "outs": [ "first_out", "last_out" ]
        },
        "shortdate2": {
            "ins": [ "first_in", "last_in" ],
            "outs": [ "first_out", "last_out" ]
        }
    }
"""
def gen_in_outs(days_to_report):
    ins_outs = {}

    cmd_systemd_login_list=f"journalctl --since '{days_to_report} days ago' -u systemd-logind.service --no-pager -o short-iso"

    try:
        cmd_ret = subprocess.run(
            f"{cmd_systemd_login_list}",
            shell=True,
            executable="/bin/bash",
            check=True,
            capture_output=True
        )
        msg = f"cmd return: {cmd_ret.returncode}\n"
        # if cmd_ret.stdout:
        #     msg += f"stdout: {cmd_ret.stdout.decode().strip()}"
        #     print(msg)

    except subprocess.CalledProcessError as e:
        msg = f"cmd return: {e.returncode}\n"
        if e.stdout:
            msg += f"stdout: {e.stdout.decode().strip()}"
        if e.stderr:
            msg += f"stdout: {e.stderr.decode().strip()}"
        print(msg)

    login_list = cmd_ret.stdout.decode().splitlines()

    start_ts = login_list[0].split()[0].replace('-', '').replace(':', '')
    start_day_date = parse(start_ts, fuzzy=True).replace(tzinfo=None)
    start_day_short = start_day_date.strftime('%a-%d-%m-%y')
    start_day_pretty = start_day_date.strftime('%a-%d-%m-%y %H:%M:%S')

    print(f"\nStart of report: {start_day_pretty}")

    for line in login_list:
        cur_date_ts = line.split()[0].replace('-', '').replace(':', '')
        try:
            cur_date = parse(cur_date_ts, fuzzy=True).replace(tzinfo=None)
        except ValueError:
            continue

        cur_date_short = cur_date.strftime('%a-%d-%m-%y')
        login_action = line.split()[3:]

        # if cur_date < start_day_date + timedelta(days=1):
        #     print(f"Same day")
        # else:
        #     start_day_date = cur_date
        #     print("Next day")

        if cur_date_short not in ins_outs:
            ins_outs.update( {
                f"{cur_date_short}": {
                    "IN": [],
                    "OUT": [],
                    "UNKNOWN": [],
                }
            } )

        str_action = sort_action(login_action)
        ins_outs[cur_date_short][str_action].append(cur_date)

        # print(f"{cur_date_short} : Report action {str_action} - ({cur_date})")

    # print(ins_outs)
    return ins_outs


"""
    get_hours from td.seconds
"""
def get_hours(td):
    return td.seconds//3600


"""
    compute_hours
"""
def compute_hours(report):
    print("\nCompute hours report:\n")
    hours_report = {}
    extra_hours_count = 0
    for day in report:
        # print(f"Compute hours of {day}: {report[day]}")
        try:
            first_in = report[day]["IN"][0]
            last_out = report[day]["OUT"][-1]
            worked_hours = get_hours(last_out - first_in)

            first_in_short = first_in.strftime('%H:%M:%S')
            last_out_short = last_out.strftime('%H:%M:%S')
            day_wh_str= f"{worked_hours}h : {first_in_short} - {last_out_short}"
        except IndexError:
            day_wh_str= f"{worked_hours}h : ERROR:\n\t{day}: {report[day]}"

        weekno = first_in.weekday()
        extra_worked_hours = 0
        if weekno < 5:
            is_weekday = True
            extra_worked_hours = worked_hours - 8.5
            day_wh_str += f" : {extra_worked_hours}"
            print(colored(f"{day}: {day_wh_str}", 'blue'))
        else:
            print(colored(f"{day}: {day_wh_str}", 'grey'))

        extra_hours_count += extra_worked_hours

        hours_report.update(
            {
                f"{day}": f"{extra_worked_hours}"
            }
        )

    if extra_hours_count:
        print(colored(f"\nExtras : {extra_hours_count}\n", 'red'))

    # _print_dict(hours_report)
    return hours_report

def _print_list(items: Union[list, str], tabs=0):
    for item in items:
        if type(item) == list:
            _print_list(item, tabs + 1)
        elif type(item) == dict:
            _print_dict(item, tabs)
        else:
            print("\t" * tabs, item, sep="")


def _print_dict(items: dict, tabs=0):
    for key in items:
        val = items[key]
        if type(val) == list:
            print("\t" * tabs, "%s:" % key, sep="")
            _print_list(val, tabs + 1)
        elif type(val) == dict:
            print("\t" * tabs, "%s:" % key, sep="")
            _print_dict(val, tabs + 1)
        else:
            print("\t" * tabs, "%s: " % key, val, sep="")

def main():

    parser = argparse.ArgumentParser(
        prog = 'Systemd login tracker',
        description = 'Gives a report of the login in and out since X days')

    parser.add_argument('days')

    args = parser.parse_args()

    days_to_report = args.days
    print(f"Report for the last {days_to_report} days")

    raw_report = gen_in_outs(days_to_report)

    interpreted_report = compute_hours(raw_report)




if __name__ == "__main__":
    main()