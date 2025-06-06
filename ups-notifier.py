import tomllib
import subprocess
import time
import sys
import telegram
import asyncio
import socket


def parse_config(path):
    with open(path, 'rb') as f:
        config = tomllib.load(f)
    return config


def parse_infos(result):
    infos = {}
    lines = result.splitlines()
    for line in lines:
        if line.strip() and not line.startswith('#') and ':' in line:
            key, value = line.split(':', 1)
            infos[key.strip()] = value.strip()
    return infos


def get_ups_info(ups_name):
    subprocess_command = ['upsc', ups_name]
    result = subprocess.run(subprocess_command, check=True,
                            capture_output=True, text=True)

    return parse_infos(result.stdout)


def force_ipv4_socket():
    socket.getaddrinfo = lambda *args, **kwargs: [
        addr for addr in socket._socket.getaddrinfo(*args, **kwargs)
        if addr[0] == socket.AF_INET  # Only keep IPv4 addresses
    ]


def notify(msg, chat_id, token):
    bot = telegram.Bot(token=token)

    msg = telegram.helpers.escape_markdown(msg, version=2)

    m_formatted = f"""
\u26A0\uFE0F *UPS notification* \u26A0\uFE0F \\
{msg}
"""

    asyncio.run(bot.send_message(
        chat_id=chat_id,
        text=m_formatted,
        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
    ))


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.toml'
    print(f"Using config file: {config_path}")
    conf = parse_config(config_path)

    old_ups_status = None

    t_chat_id = conf['telegram']['chat_id']
    t_token = conf['telegram']['token']

    # For telegram to work, we need to force the socket to use ipv4
    force_ipv4_socket()

    print("UPS Notifier started...")
    while True:
        try:
            ups_name = conf['ups']['name']
            infos = get_ups_info(ups_name)
            # print(infos)

            ups_status = infos.get('ups.status')
            if old_ups_status is None:
                old_ups_status = ups_status

            if ups_status != old_ups_status:
                if ups_status == 'OL':
                    print(f"UPS {ups_name} is online.")
                    notify(f"UPS {ups_name} is online.", t_chat_id, t_token)
                elif ups_status == 'OB':
                    print(f"UPS {ups_name} is on battery.")
                    notify(f"UPS {ups_name} is on battery.",
                           t_chat_id, t_token)
                elif ups_status == 'OB LB':
                    print(f"UPS {ups_name} is in low battery mode.")
                    notify(f"UPS {ups_name} is in low battery mode.",
                           t_chat_id, t_token)
                else:
                    print(f"UPS {ups_name} status changed to: {ups_status}")
                    notify(f"UPS {ups_name} status changed to: {ups_status}",
                           t_chat_id, t_token)

                old_ups_status = ups_status

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(4)


if __name__ == '__main__':
    main()
