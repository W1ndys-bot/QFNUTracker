import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import sys
from urllib.parse import urljoin

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.switch import get_all_group_switches
from app.api import send_group_msg


def fetch_content(url, last_content):
    try:
        response = requests.get(url)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        found_content = soup.find("ul", {"class": "n_listxx1"})
        current_content = found_content.encode("utf-8") if found_content else None

        if last_content is None:
            return current_content, None

        if current_content != last_content:
            return current_content, current_content
        return last_content, None
    except requests.RequestException as e:
        logging.error(f"获取{url}网页内容失败: {e}")
        return last_content, None


async def monitor_announcements(
    websocket, url, last_content, site_name, last_check_time
):
    current_time = datetime.now()

    # 检查当前时间的分钟数是否是5的倍数，表示每五分钟检查一次
    if current_time.minute % 5 != 0:
        return last_content, last_check_time

    # 检查是否在同一分钟内已经检查过
    if last_check_time and last_check_time.minute == current_time.minute:
        return last_content, last_check_time

    last_check_time = current_time
    last_content, updated_content = fetch_content(url, last_content)
    logging.info(f"执行{site_name}监控")
    if updated_content:
        logging.info(f"检测到{site_name}公告有更新")
        soup = BeautifulSoup(updated_content, "html.parser")
        announcements = soup.find_all("li")
        if announcements:
            announcement = announcements[0]
            title = announcement.find("a").text.strip()
            link = urljoin(
                url, announcement.find("a")["href"]
            )  # 使用urljoin来正确拼接URL
            summary = announcement.find("p").text.strip()
            all_switches = get_all_group_switches()
            for group_id, switches in all_switches.items():
                if switches.get(f"{site_name}监控"):
                    logging.info(
                        f"检测到{site_name}公告有更新，向群 {group_id} 发送公告"
                    )
                    await send_group_msg(
                        websocket,
                        group_id,
                        f"{site_name}公告有新内容啦：\n\n标题：{title}\n\n摘要：{summary}\n\n链接：{link}\n\n技术支持：\nhttps://w1ndys.top\nhttps://github.com/W1ndys-bot/QFNUTracker",
                    )
    return last_content, last_check_time