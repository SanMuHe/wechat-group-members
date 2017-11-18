import argparse
import json

from wechat import WeChat

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('group_name',  help='name of the WeChat roup')
    args = parser.parse_args()

    if args.group_name == '':
        print('group_name cannot be empty.')
        return

    wechat = WeChat()

    members = list(wechat.findGroupMembers(args.group_name))

    if len(members) == 0:
        print('Cannot find any members from gorup [{0}]'.format(args.group_name))
        return

    for member in members:
        print(json.dumps(member))

if __name__ == '__main__':
    main()
