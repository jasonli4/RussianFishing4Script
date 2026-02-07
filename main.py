"""Main CLI for Russian Fishing 4 Script.

This module provides the command-line interface and main execution logic
for automating fishing in Russian Fishing 4. It handles configuration,
argument parsing, window management, and fishing automation.

.. moduleauthor:: Derek Lee <dereklee0310@gmail.com>
"""

import argparse
import logging
import logging.config
import shlex
import sys
from pathlib import Path

import rich.logging  # noqa: F401
import rich_argparse
from rich import box, print
from rich.table import Table
from yacs.config import CfgNode as CN

from rf4s import config, utils
from rf4s.app import (
    BotApp,
    CalculateApp,
    CraftApp,
    FrictionBrakeApp,
    HarvestApp,
    MoveApp,
)

VERSION = "0.9.0"
MINIMUM_COMPATIBLE_CONFIG_VERSION = "0.8.0"
LOGO = """
██████╗ ███████╗██╗  ██╗███████╗
██╔══██╗██╔════╝██║  ██║██╔════╝
██████╔╝█████╗  ███████║███████╗
██╔══██╗██╔══╝  ╚════██║╚════██║
██║  ██║██║          ██║███████║
╚═╝  ╚═╝╚═╝          ╚═╝╚══════╝"""

# https://patorjk.com/software/taag/#p=testall&f=3D-ASCII&t=RF4S%0A, ANSI Shadow

FEATURES = (
    {"name": "钓鱼机器人", "command": "bot"},
    {"name": "制作物品", "command": "craft"},
    {"name": "自动前行", "command": "move"},
    {"name": "收集饵料", "command": "harvest"},
    {"name": "自动摩擦制动", "command": "frictionbrake"},
    {"name": "计算钓组属性", "command": "calculate"},
)

BOT_BOOLEAN_ARGUMENTS = (
    ("t", "tag", "只保留标记的鱼"),
    ("c", "coffee", "搏鱼时体力低时喝咖啡"),
    ("a", "alcohol", "存鱼前喝酒"),
    ("r", "refill", "饥饿或舒适度低时喝茶吃胡萝卜"),
    ("H", "harvest", "抛竿前收集饵料"),
    ("L", "lure", "随机更换为收藏的路亚，模式：路亚"),
    ("m", "mouse", "抛竿前随机移动鼠标"),
    ("P", "pause", "偶尔在抛竿前暂停脚本"),
    ("RC", "random-cast", "随机进行额外的抛竿"),
    ("SC", "skip-cast", "跳过第一次抛竿"),
    ("l", "lift", "搏鱼时持续提竿"),
    ("e", "electro", "启用Electro Raptor系列卷线器的电动模式"),
    ("FB", "friction-brake", "自动调节摩擦制动"),
    ("GR", "gear-ratio", "收线超时后切换齿轮比或模式"),
    ("b", "bite", "鱼咬钩时保存截图到screenshots/"),
    ("s", "screenshot", "钓到鱼后保存截图到screenshots/"),
    ("d", "data", "在/logs中保存钓鱼数据"),
    ("E", "email", "脚本停止后发送邮件通知"),
    ("M", "miaotixing", "脚本停止后发送喵提醒通知"),
    ("D", "discord", "脚本停止后发送Discord通知"),
    ("TG", "telegram", "脚本停止后发送Telegram通知"),
    ("S", "shutdown", "脚本停止后关闭电脑"),
    ("SO", "signout", "退出登录而非关闭游戏"),
    ("BL", "broken-lure", "用收藏的路亚替换损坏的路亚"),
    ("SR", "spod-rod", "重新抛撒打窝竿"),
    ("DM", "dry-mix", "启用干散饵补充，模式：底钓"),
    ("GB", "groundbait", "启用打窝饵补充，模式：底钓"),
    ("PVA", "pva", "启用PVA补充，模式：底钓"),
    (
        "NA",
        "no-animation",
        "禁用等待星鱼礼物动画，在游戏设置中将 “捕获界面样式” 改为 “简洁”，即可使用此参数",
    ),
)

EPILOG = """
文档：https://github.com/dereklee0310/RussianFishing4Script/tree/main/docs/en
"""

# When running as an executable, use sys.executable to find the config.yaml.
# This file is not included during compilation and could not be resolved automatically
# by Nuitka.
INNER_ROOT = Path(__file__).resolve().parents[0]
if utils.is_compiled():
    OUTER_ROOT = Path(sys.executable).parent
else:
    OUTER_ROOT = INNER_ROOT


class Formatter(
    rich_argparse.RawTextRichHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    # argparse.RawTextHelpFormatter, argparse.RawDescriptionHelpFormatter
    pass


def setup_logging() -> logging.Logger:
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        # "filters": {}
        "formatters": {
            # RichHandler do the job for us, so we don't need to incldue time & level
            "iso-8601-simple": {
                "format": "%(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
            "iso-8601-detailed": {
                "format": "%(asctime)s [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "handlers": {
            "stdout": {
                "level": "INFO",
                "formatter": "iso-8601-simple",
                "()": "rich.logging.RichHandler",
                "rich_tracebacks": True,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "iso-8601-detailed",
                "filename": "logs/.log",
                "maxBytes": 10000,
                "backupCount": 0,
            },
        },
        "loggers": {"root": {"level": "INFO", "handlers": ["stdout", "file"]}},
    }
    logging.config.dictConfig(config=logging_config)
    return logging.getLogger(__name__)


(OUTER_ROOT / "screenshots").mkdir(parents=True, exist_ok=True)
(OUTER_ROOT / "logs").mkdir(parents=True, exist_ok=True)
logger = setup_logging()


def setup_parser(cfg: CN) -> tuple[argparse.ArgumentParser, tuple]:
    """Configure the argument parser with all supported command-line options.

    :return: Configured ArgumentParser instance with all options and flags.
    :rtype: ArgumentParser
    """
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("opts", nargs="*", help="overwrite configuration")

    main_parser = argparse.ArgumentParser(epilog=EPILOG, formatter_class=Formatter)
    main_parser.add_argument(
        "-V", "--version", action="version", version=f"RF4S {VERSION}"
    )

    feature_parsers = main_parser.add_subparsers(title="features", dest="feature")

    bot_parser = feature_parsers.add_parser(
        "bot",
        help="start fishing bot",
        parents=[parent_parser],
        formatter_class=Formatter,
    )
    bot_parser.add_argument(
        "-V", "--version", action="version", version=f"RF4S-bot {VERSION}"
    )

    for argument in BOT_BOOLEAN_ARGUMENTS:
        flag1 = f"-{argument[0]}"
        flag2 = f"--{argument[1]}"
        help_message = argument[2]
        bot_parser.add_argument(flag1, flag2, action="store_true", help=help_message)

    profile_strategy = bot_parser.add_mutually_exclusive_group()

    def pid(_pid: str) -> int:
        return int(_pid)  # ValueError will be handled

    profile_strategy.add_argument(
        "-p",
        "--pid",
        type=pid,
        choices=range(len(cfg.PROFILE)),
        help="specify the id of the profile to use",
        metavar=f"{{0-{len(cfg.PROFILE) - 1}}}",
    )

    def pname(_pname: str) -> str:
        if _pname not in cfg.PROFILE:
            raise ValueError  # ValueError will be handled
        return _pname

    profile_strategy.add_argument(
        "-N",
        "--pname",
        type=pname,
        help="specify the name of the profile to use",
        metavar="{profile name}",
    )

    def num_fish(_num_fish: str) -> int:
        return int(_num_fish)  # ValueError will be handled

    bot_parser.add_argument(
        "-n",
        "--fishes-in-keepnet",
        default=0,  # Flag is not used
        # const=0, # Flag is used but no argument given
        type=num_fish,
        choices=range(cfg.BOT.KEEPNET.CAPACITY),
        help="specify the number of fishes in your keepnet, (default: %(default)s)",
        metavar=f"{{0-{cfg.BOT.KEEPNET.CAPACITY - 1}}}",
    )
    bot_parser.add_argument(
        "-T",
        "--trolling",
        nargs="?",
        const="forward",
        default=None,
        type=str,
        choices=["forward", "left", "right"],
        help=(
            "enable trolling mode and specify the direction\n"
            "(default: %(default)s, no argument: %(const)s)"
        ),
    )
    bot_parser.add_argument(
        "-R",
        "--rainbow",
        nargs="?",
        const=5,
        default=None,
        type=int,
        choices=[0, 5],
        help=(
            "enable rainbow line mode and specify the meter to lift the rod\n"
            "(default: %(default)s, no argument: %(const)s)"
        ),
    )

    bot_parser.add_argument(
        "-BT",
        "--boat-ticket",
        nargs="?",
        const=5,
        default=0,
        type=int,
        choices=[0, 1, 2, 3, 5],
        help=(
            "enable boat ticket renewal and specify the duration\n"
            "(default: %(default)s, no argument: %(const)s)"
        ),
    )

    craft_parser = feature_parsers.add_parser(
        "craft", help="craft items", parents=[parent_parser], formatter_class=Formatter
    )
    craft_parser.add_argument(
        "-V", "--version", action="version", version=f"RF4S-craft {VERSION}"
    )
    craft_parser.add_argument(
        "-d",
        "--discard",
        action="store_true",
        help="discard all the crafted items (for groundbaits)",
    )
    craft_parser.add_argument(
        "-i",
        "--ignore",
        action="store_true",
        help="ignore unselected material slots",
    )
    craft_parser.add_argument(
        "-n",
        "--craft-limit",
        type=int,
        default=-1,
        help="specify the number of items to craft, (default: %(default)s)",
        metavar="{number of items}",
    )

    move_parser = feature_parsers.add_parser(
        "move",
        help="toggle moving forward",
        parents=[parent_parser],
        formatter_class=Formatter,
    )
    move_parser.add_argument(
        "-V", "--version", action="version", version=f"RF4S-move {VERSION}"
    )
    move_parser.add_argument(
        "-s",
        "--shift",
        action="store_true",
        help="Hold down the Shift key while moving",
    )

    harvest_parser = feature_parsers.add_parser(
        "harvest",
        help="harvest baits",
        parents=[parent_parser],
        formatter_class=Formatter,
    )
    harvest_parser.add_argument(
        "-V", "--version", action="version", version=f"RF4S-harvest {VERSION}"
    )
    harvest_parser.add_argument(
        "-r",
        "--refill",
        action="store_true",
        help="refill hunger and comfort by consuming tea and carrot",
    )

    friction_brake_parser = feature_parsers.add_parser(
        "frictionbrake",
        help="automate friction brake",
        aliases=["fb"],
        parents=[parent_parser],
        formatter_class=Formatter,
    )
    friction_brake_parser.add_argument(
        "-V", "--version", action="version", version=f"RF4S-frictionbrake {VERSION}"
    )

    calculate_paser = feature_parsers.add_parser(
        "calculate",
        help="calculate tackle's stats",
        aliases=["cal"],
        parents=[parent_parser],
        formatter_class=Formatter,
    )
    calculate_paser.add_argument(
        "-V", "--version", action="version", version=f"RF4S-calculate {VERSION}"
    )

    return main_parser, (
        bot_parser,
        craft_parser,
        move_parser,
        harvest_parser,
        friction_brake_parser,
        calculate_paser,
    )


def display_features() -> None:
    """显示可用功能表供用户选择。

    显示带有功能ID和名称的格式化表格。
    """
    table = Table(
        "功能列表",
        title="选择一个功能开始 🚀",
        show_header=False,
        box=box.HEAVY,
        min_width=36,
    )

    for i, feature in enumerate(FEATURES):
        table.add_row(f"{i:>2}. {feature['name']}")
    print(table)


def get_fid(parser: argparse.ArgumentParser) -> int:
    """提示用户输入功能ID并验证输入。

    持续提示直到输入有效的功能ID或用户选择退出。
    """
    utils.print_usage_box("输入功能ID，h查看帮助信息，q退出。")

    while True:
        user_input = input(">>> ")
        if user_input.isdigit() and 0 <= int(user_input) < len(FEATURES):
            break
        if user_input == "q":
            print("再见。")
            sys.exit()
        if user_input == "h":
            parser.print_help()
            continue
        utils.print_error("无效输入，请重试。")
    return int(user_input)


def get_launch_options(parser: argparse.ArgumentParser) -> str:
    utils.print_usage_box(
        "输入启动选项，回车跳过，h查看帮助信息，q退出。"
    )
    while True:
        user_input = input(">>> ")
        if user_input == "q":
            print("再见。")
            sys.exit()
        if user_input == "h":
            parser.print_help()
            continue
        break
    return user_input


def get_language():
    utils.print_usage_box("您的游戏语言是什么？[(1) en (2) ru (3) q (退出)]")
    while True:
        user_input = input(">>> ")
        if user_input.isdigit() and user_input in ("1", "2"):
            break
        if user_input == "q":
            print("再见。")
            sys.exit()
        utils.print_error("无效输入，请重试。")
    return '"en"' if user_input == "1" else '"ru"'


def get_click_lock():
    utils.print_usage_box(
        "Windows鼠标点击锁定是否已启用？[(1) 是 (2) 否 (3) q (退出)]"
    )
    while True:
        user_input = input(">>> ")
        if user_input.isdigit() and user_input in ("1", "2"):
            break
        if user_input == "q":
            print("再见。")
            sys.exit()
        utils.print_error("无效输入，请重试。")
    return "true" if user_input == "1" else "false"


def setup_cfg():
    config_path = OUTER_ROOT / "config.yaml"
    if not config_path.exists():
        language = get_language()
        click_lock = get_click_lock()

        with open(Path(INNER_ROOT / "rf4s/config/config.yaml"), "r") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if line.startswith("LANGUAGE:"):
                    lines[i] = f"LANGUAGE: {language}\n"
                if line.startswith("  CLICK_LOCK"):
                    lines[i] = f"  CLICK_LOCK: {click_lock}\n"

        with open(config_path, "w") as file:  # shutil.copy
            file.writelines(lines)

    cfg = config.load_cfg()
    if cfg.VERSION < MINIMUM_COMPATIBLE_CONFIG_VERSION:
        logger.critical(
            "配置文件版本不兼容，某些设置已被删除或弃用\n"
            "您可以删除它以让机器人创建新的配置文件\n"
            "或者查看CHANGELOG来修改config.yaml"
        )
        utils.safe_exit()
    return cfg


def main() -> None:
    cfg = setup_cfg()
    parser, subparsers = setup_parser(cfg)
    args = parser.parse_args()  # First parse to get {command} {flags}
    utils.print_logo_box(LOGO)  # Print logo here so the help message will not show it

    # If user run the program without specifying a command or by double-clicking,
    # prompt user to input the feature and launch options. This handle both Python
    # interpreter and Nuitka executable use cases.
    # If a command is parsed, we assume that the user has already typed the
    # launch options and don't prompt them to type it.
    if args.feature is None:
        display_features()
        fid = get_fid(parser)
        # Merge selected feature and launch options
        sys.argv = [sys.argv[0]] + [FEATURES[fid]["command"]] + sys.argv[1:]
        sys.argv += shlex.split(get_launch_options(subparsers[fid]))
        args = parser.parse_args()

    start, end = sys.argv[:2], sys.argv[2:]
    match args.feature:
        case "bot":
            sys.argv = start + shlex.split(cfg.BOT.LAUNCH_OPTIONS) + end
            App = BotApp
        case "craft":
            sys.argv = start + shlex.split(cfg.CRAFT.LAUNCH_OPTIONS) + end
            App = CraftApp
        case "move":
            sys.argv = start + shlex.split(cfg.MOVE.LAUNCH_OPTIONS) + end
            App = MoveApp
        case "harvest":
            sys.argv = start + shlex.split(cfg.HARVEST.LAUNCH_OPTIONS) + end
            App = HarvestApp
        case "frictionbrake" | "fb":
            sys.argv = start + shlex.split(cfg.FRICTION_BRAKE.LAUNCH_OPTIONS) + end
            App = FrictionBrakeApp
        case "calculate" | "cal":
            App = CalculateApp
        case _:
            raise NotImplementedError("You should not reach here.")
    App(cfg, parser.parse_args(), parser).start()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(e, exc_info=True)
        utils.safe_exit()  # TODO
