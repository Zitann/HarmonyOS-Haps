# /// script
# dependencies = [
#   "requests",
# ]
# ///
import sys

from common import send_broadcast


def main():
    msg = " ".join(sys.argv[1:]) or "测试广播消息"
    if send_broadcast(msg):
        print(f"广播成功: {msg}")
    else:
        print("广播失败或未配置，请检查上方提示")


if __name__ == "__main__":
    main()
