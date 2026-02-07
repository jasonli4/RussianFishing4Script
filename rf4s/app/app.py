"""Base application class for other tools.

Provides core functionality for:
- Configuration management
- Window control
- Result display

.. moduleauthor:: Derek Lee <dereklee0310@gmail.com>
"""

import argparse
import os
import random
import shlex
import signal
import smtplib
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from multiprocessing import Lock
from socket import gaierror
from time import sleep
from typing import Optional

import pyautogui as pag
import requests
from pynput import keyboard
from rich import box, print
from rich.prompt import Prompt
from rich.table import Table
from yacs.config import CfgNode as CN

from rf4s import config, exceptions, utils
from rf4s.app.core import logger
from rf4s.component.friction_brake import FrictionBrake
from rf4s.config import load_cfg
from rf4s.controller.detection import Detection
from rf4s.controller.player import Player
from rf4s.controller.timer import Timer, add_jitter
from rf4s.controller.window import Window
from rf4s.result import BotResult, CraftResult, HarvestResult, Result

BIAS = 1e-6
ANIMATION_DELAY = 0.5
THREAD_CHECK_DELAY = 0.5
LOOP_DELAY = 1
CRAFT_DELAY = 4.0
MAX_FRICTION_BRAKE = 30


class App(ABC):
    """A base application class.

    Attributes:
        cfg (yacs.config.CfgNode): Default + user's configuration file
        window (Window): Window controller
    """

    def __init__(
        self, cfg: CN, args: argparse.Namespace, parser: argparse.ArgumentParser
    ):
        """Initialize a mutable cfg node for further modification."""
        self.cfg = cfg
        self.args = args
        self.parser = parser
        self.result = None  # Dummy result

    @abstractmethod
    def _on_release(self, key: keyboard.KeyCode) -> None:
        pass

    @abstractmethod
    def start(self):
        pass

    def display_result(self) -> None:
        """Display the running result in a table format."""
        result_dict = self.result.as_dict()
        if not result_dict:
            return

        result = Table(title="Running Result", box=box.HEAVY, show_header=False)
        for name, value in self.result.as_dict().items():
            result.add_row(name, str(value))
        print(result)


class BotApp(App):
    """Main application class for Russian Fishing 4 automation.

    This class orchestrates the entire automation process, from parsing command-line
    arguments to configuring the environment and executing the fishing routine.

    Attributes:
        cfg (CfgNode): Configuration node merged from YAML and CLI arguments
        args (Namespace): Parsed command-line arguments
        window (Window): Game window controller instance
        player (Player): Player instance for fishing automation
    """

    def __init__(
        self, cfg: CN, args: argparse.Namespace, parser: argparse.ArgumentParser
    ):
        """Initialize the application.

        Loads configuration, parses command-line arguments, and sets up the environment.
        """
        super().__init__(cfg, args, parser)
        self.setup_profile()
        self.merge_args_to_cfg()
        self.window = Window()
        # args is done now, start validation
        self.validate_cfg()
        self.cfg.freeze()  # cfg is done now
        self.display_info()

        self.result = BotResult()
        self.window = Window()
        self.player = Player(
            self.cfg, Timer(self.cfg), Detection(self.cfg, self.window), self.result
        )

        self.paused = False

    def validate_cfg(self):
        self.validate_smtp()
        self.validate_discord()
        self.validate_telegram()
        self.validate_game_window()
        self.validate_favorite_icon()
        self.validate_screenshot_notification()
        self.validate_spool_detection()

    def display_info(self):
        settings = Table(
            title="设置", show_header=False, box=box.HEAVY, min_width=36
        )
        settings.add_row("启动选项（最终）", " ".join(sys.argv[1:]))
        for k, v in self.cfg.PROFILE.items():
            if k != "DESCRIPTION":
                settings.add_row(k, str(v))
        print(settings)
        if self.cfg.PROFILE.DESCRIPTION:
            utils.print_description_box(self.cfg.PROFILE.DESCRIPTION)
        utils.print_usage_box(
            f"按 {self.cfg.KEY.PAUSE} 暂停，{self.cfg.KEY.QUIT} 退出。"
        )

    def validate_smtp(self) -> None:
        """Verify SMTP server connection for email notifications.

        Tests the connection to the configured SMTP server using stored
        credentials if email notifications are enabled.
        """
        if not self.cfg.ARGS.EMAIL or not self.cfg.BOT.SMTP_VERIFICATION:
            return
        logger.info("Verifying SMTP connection")

        try:
            with smtplib.SMTP_SSL(self.cfg.BOT.NOTIFICATION.SMTP_SERVER, 465) as server:
                server.login(
                    self.cfg.BOT.NOTIFICATION.EMAIL, self.cfg.BOT.NOTIFICATION.PASSWORD
                )
        except smtplib.SMTPAuthenticationError:
            logger.critical(
                "无效的电子邮件地址或应用密码\n"
                "检查 BOT.NOTIFICATION.EMAIL\n"
                "检查 BOT.NOTIFICATION.PASSWORD\n"
                "Gmail用户请参考："
                "https://support.google.com/accounts/answer/185833\n"
            )
            utils.safe_exit()
        except (TimeoutError, gaierror):
            logger.critical(
                "无效的 BOT.NOTIFICATION.SMTP_SERVER 或连接超时"
            )
            utils.safe_exit()

    def validate_discord(self) -> None:
        if not self.cfg.ARGS.DISCORD or self.cfg.BOT.NOTIFICATION.DISCORD_WEBHOOK_URL:
            return
        logger.critical(
            "未设置 BOT.NOTIFICATION.DISCORD_WEBHOOK_URL\n"
            "要创建webhook，请参考"
            "https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks"
        )
        utils.safe_exit()

    def validate_miaotixing(self) -> None:
        if not self.cfg.ARGS.MIAOTIXING or self.cfg.BOT.NOTIFICATION.MIAO_CODE:
            return
        logger.critical("未设置 BOT.NOTIFICATION.MIAO_CODE。")
        utils.safe_exit()

    def validate_telegram(self):
        def _is_telegram_bot_valid():
            url = (
                "https://api.telegram.org/"
                f"bot{self.cfg.BOT.NOTIFICATION.TELEGRAM_BOT_TOKEN}/getMe"
            )
            return requests.get(url).status_code == 200

        if not self.cfg.ARGS.TELEGRAM:
            return

        valid = True
        if not _is_telegram_bot_valid():
            logger.critical("无效的 BOT.NOTIFICATION.TELEGRAM_BOT_TOKEN")
            valid = False
        if self.cfg.BOT.NOTIFICATION.TELEGRAM_CHAT_ID == -1:
            logger.critical("未设置 BOT.NOTIFICATION.TELEGRAM_CHAT_ID")
            valid = False
        if not valid:
            logger.critical(
                "请参考："
                "https://gist.github.com/nafiesl/4ad622f344cd1dc3bb1ecbe468ff9f8a",
            )
            utils.safe_exit()

    def validate_profile(self, profile_name: str) -> None:
        """Check if a profile configuration is valid and complete.

        :param profile_name: Name of the profile to validate.
        :type profile_name: str
        """
        if profile_name not in self.cfg.PROFILE:
            logger.critical("Invalid profile name: '%s'", profile_name)
            utils.safe_exit()

        mode = self.cfg.PROFILE[profile_name].MODE
        if mode.upper() not in self.cfg.PROFILE:
            logger.critical("Invalid mode: '%s'", mode)
            utils.safe_exit()

        expected_keys = set(self.cfg.PROFILE[mode.upper()])
        actual_keys = set(self.cfg.PROFILE[profile_name])

        invalid_keys = actual_keys - expected_keys
        missing_keys = expected_keys - actual_keys

        if invalid_keys or missing_keys:
            for key in invalid_keys:
                logger.warning("Invalid setting: 'PROFILE.%s.%s'", profile_name, key)
            for key in missing_keys:
                logger.warning("Missing setting: 'PROFILE.%s.%s'", profile_name, key)

    def display_profiles(self) -> None:
        """显示可用配置文件表供用户选择。

        显示带有配置文件ID和名称的格式化表格。
        """
        profiles = Table(
            title="选择一个配置文件开始 ⚙️",
            box=box.HEAVY,
            show_header=False,
            min_width=36,
        )
        for i, profile in enumerate(self.cfg.PROFILE):
            profile_name = profile
            description = self.cfg.PROFILE[profile_name].DESCRIPTION
            profiles.add_row(f"{i:>2}. {profile_name} - {description}")
        print(profiles)

    def get_pid(self) -> None:
        """提示用户输入配置文件ID并验证输入。

        持续提示直到输入有效的配置文件ID或用户选择退出。
        """
        utils.print_usage_box("输入要使用的配置文件ID，q退出。")

        while True:
            user_input = input(">>> ")
            if user_input.isdigit() and 0 <= int(user_input) < len(self.cfg.PROFILE):
                break
            if user_input == "q":
                print("再见。")
                sys.exit()
            utils.print_error("无效的配置文件ID，请重试。")

        self.args.pid = int(user_input)

    def setup_profile(self) -> None:
        """Configure the user profile based on arguments or interactive selection.

        Selects a profile based on command-line arguments or user input,
        validates the profile, and merges it with the configuration.
        """
        if self.args.pname is not None:
            profile_name = self.args.pname
        else:
            if self.args.pid is None:
                self.display_profiles()
                self.get_pid()
            profile_name = list(self.cfg.PROFILE)[self.args.pid]
        self.merge_default_to_profile(profile_name)

    def merge_default_to_profile(self, profile_name) -> None:
        self.validate_profile(profile_name)
        mode = self.cfg.PROFILE[profile_name].MODE.upper()
        user_profile = CN({"NAME": profile_name}, new_allowed=True)
        user_profile.merge_from_other_cfg(self.cfg.PROFILE[mode])
        user_profile.merge_from_other_cfg(self.cfg.PROFILE[profile_name])
        self.cfg.PROFILE = user_profile  # Overwrite default profiles

    def merge_args_to_cfg(self) -> None:
        """Must be called after the profile is correctly configured."""
        if len(self.args.opts) % 2:
            logger.error(
                "Invalid launch options: '%s'\n"
                "These arguments are used for config override: '%s'\n",
                " ".join(sys.argv[1:]),
                " ".join(self.args.opts),
            )
            sys.exit()

        self.cfg.merge_from_list(self.args.opts)
        # Merge profile-level launch options
        if self.cfg.PROFILE.LAUNCH_OPTIONS:
            new_launch_options = shlex.split(self.cfg.PROFILE.LAUNCH_OPTIONS)
            base_len = len(shlex.split(self.cfg.BOT.LAUNCH_OPTIONS)) + 2
            sys.argv = sys.argv[:base_len] + new_launch_options + sys.argv[base_len:]
            self.args = self.parser.parse_args()
        # We need to convert items in args to uppercase to make them consistent with
        # those in CN(), so it must be done manually instead of using CN(dict).
        self.cfg.ARGS = config.dict_to_cfg(vars(self.args))

    def validate_game_window(self) -> None:
        """设置并验证游戏窗口。

        创建窗口对象，检查窗口大小是否受支持，
        并在需要时禁用不兼容的功能。
        """
        if self.window.is_title_bar_exist():
            logger.info("检测到窗口模式。不要移动游戏窗口")
        if self.window.is_size_supported():
            logger.info("支持的窗口大小。不要更改游戏窗口大小")
            return

        window_resolution = self.window.get_resolution_str()
        if window_resolution == "0x0":
            logger.critical("不支持全屏模式")
            utils.safe_exit()

        if self.cfg.PROFILE.MODE in ("telescopic", "bolognese"):
            logger.critical(
                "钓鱼模式 '%s' 不支持窗口大小 '%s'",
                self.cfg.PROFILE.MODE,
                self.window.get_resolution_str(),
            )
            utils.safe_exit()

        logger.warning(
            "不支持的窗口大小 '%s'\n"
            "支持的窗口大小：'2560x1440'、'1920x1080' 或 '1600x900'\n"
            "将在屏幕而不是游戏窗口上搜索图像",
            self.window.get_resolution_str(),
        )
        logger.error(
            "挂底检测将被禁用\n"
            "绕线检测将被禁用\n"
            "自动摩擦制动将被禁用\n"
        )

        self.cfg.ARGS.FRICTION_BRAKE = False
        self.cfg.BOT.SNAG_DETECTION = False
        self.cfg.BOT.SPOOLING_DETECTION = False

    def validate_favorite_icon(self):
        if (
            self.cfg.ARGS.COFFEE
            or self.cfg.ARGS.REFILL
            or self.cfg.ARGS.LURE
            or self.cfg.ARGS.DRY_MIX
            or self.cfg.ARGS.GROUNDBAIT
            or self.cfg.ARGS.PVA
        ):
            logger.info(
                "某些功能需要您将物品添加到收藏夹，"
                "请确保已这样做"
            )

    def validate_screenshot_notification(self):
        if self.cfg.ARGS.SCREENSHOT and self.cfg.ARGS.MIAOTIXING:
            logger.warning(
                "喵提醒不支持图片消息，不会发送截图"
            )

    def validate_spool_detection(self):
        if self.cfg.ARGS.RAINBOW is None:
            logger.warning(
                "检测到默认收线检测模式，请完全收起您的鱼线"
            )

    def _on_release(self, key: keyboard.KeyCode) -> None:
        """监控用户的击键并将按键转换为CTRL_C_EVENT。

        :param key: 被释放的键。
        :type key: keyboard.KeyCode

        当按下配置的退出键时退出应用程序。
        """
        # 触发CTRL_C_EVENT，将在start()中被捕获以模拟按下
        # CTRL-C来终止脚本。
        key = str(key).lower()
        if key == str(keyboard.KeyCode.from_char(self.cfg.KEY.QUIT)):
            os.kill(os.getpid(), signal.CTRL_C_EVENT)
            return False
        if key == str(keyboard.KeyCode.from_char(self.cfg.KEY.PAUSE)):
            logger.info("暂停机器人")
            os.kill(os.getpid(), signal.CTRL_C_EVENT)
            self.paused = True
            logger.info("机器人已暂停")  # 不要删除这个！它会干扰信号？
            return False

    def _pause_wait(self, key: keyboard.KeyCode) -> None:
        key = str(key).lower()
        if key == str(keyboard.KeyCode.from_char(self.cfg.KEY.PAUSE)):
            self.paused = False
            return False

    def reload_cfg(self) -> None:
        profile_name = self.cfg.PROFILE.NAME
        self.cfg = load_cfg()
        self.merge_default_to_profile(profile_name)
        self.merge_args_to_cfg()
        self.validate_cfg()
        self.cfg.freeze()
        self.display_info()

    def start(self) -> None:
        """Start the fishing automation process.

        Sets up all required components, activates the game window,
        registers key listeners, and begins the fishing automation.
        Handles termination and displays result.
        """
        while True:
            general_listener = keyboard.Listener(on_release=self._on_release)
            general_listener.start()
            self.window.activate_game_window()
            try:
                self.player.start_fishing()
            except KeyboardInterrupt:
                general_listener.stop()
                if not self.paused:
                    break

                utils.print_usage_box(
                    f"按 {self.cfg.KEY.PAUSE} 重新加载配置并重启。"
                )
                utils.print_hint_box(
                    "对LAUNCH_OPTIONS所做的任何修改将被忽略。"
                )
                with self.player.hold_keys(mouse=False, shift=False, reset=True):
                    pause_listener = keyboard.Listener(on_release=self._pause_wait)
                    pause_listener.start()

                while pause_listener.is_alive():
                    sleep(add_jitter(THREAD_CHECK_DELAY))

                logger.info("重启机器人而不重置记录")
                self.reload_cfg()
                self.player = Player(
                    self.cfg,
                    self.player.timer,
                    self.player.detection,
                    self.player.result,
                )
                self.paused = False

        self.player.handle_termination("用户终止", shutdown=False, send=False)


class CraftApp(App):
    """Main application class for automating crafting.

    This class manages the configuration, detection, and execution of the crafting
    process. It tracks the number of successful and failed crafts, as well as the
    total number of materials used.
    """

    def __init__(self, cfg, args, parser):
        super().__init__(cfg, args, parser)
        args_cfg = CN({"ARGS": config.dict_to_cfg(vars(self.args))})
        self.cfg.merge_from_other_cfg(args_cfg)
        self.cfg.merge_from_list(self.args.opts)
        self.cfg.freeze()

        settings = Table(
            title="设置", show_header=False, box=box.HEAVY, min_width=36
        )
        settings.add_row("启动选项（最终）", " ".join(sys.argv[1:]))
        print(settings)

        self.result = CraftResult()
        self.window = Window()
        self.detection = Detection(self.cfg, self.window)

    def craft_item(self, accept_key: str) -> None:
        """制作物品。

        :param craft_delay: 接受制作物品前的延迟（秒）。
        :type craft_delay: float
        :param accept_delay: 接受制作物品后的延迟（秒）。
        :type accept_delay: float
        :param accept_key: 接受制作物品后按下的键。
        :type accept_key: str
        """
        logger.info("制作物品")
        pag.click()
        sleep(add_jitter(CRAFT_DELAY))
        self.result.material += 1
        while True:
            if self.detection.is_operation_success():
                logger.info("制作成功")
                self.result.success += 1
                pag.press(accept_key)
                break

            if self.detection.is_operation_failed():
                logger.warning("制作失败")
                self.result.fail += 1
                pag.press("space")
                break
            sleep(add_jitter(LOOP_DELAY))
        sleep(add_jitter(ANIMATION_DELAY))
        discard_yes_position = self.detection.get_discard_yes_position()
        if discard_yes_position:
            pag.click(discard_yes_position)
        sleep(add_jitter(LOOP_DELAY))

    def _on_release(self, key: keyboard.KeyCode) -> None:
        """Handle keyboard release events for script control.

        :param key: Key released by the user.
        :type key: keyboard.KeyCode
        """
        if str(key).lower() == str(keyboard.KeyCode.from_char(self.cfg.KEY.QUIT)):
            os.kill(os.getpid(), signal.CTRL_C_EVENT)
            return False

    def start(self) -> None:
        """制作物品的主循环。

        执行制作物品的主循环，直到材料用完或达到制作限制。
        支持快速制作模式和丢弃物品。
        """
        listener = keyboard.Listener(on_release=self._on_release)
        listener.start()

        try:
            utils.print_usage_box(f"按 {self.cfg.KEY.QUIT} 退出。")
            logger.warning("这可能会导致您被封禁，使用风险自负")
            logger.warning("建议改用Razer或Logitech宏")
            random.seed(datetime.now().timestamp())
            accept_key = "backspace" if self.cfg.ARGS.DISCARD else "space"
            self.window.activate_game_window()
            make_button_position = self.detection.get_make_button_position()
            if make_button_position is None:
                logger.critical(
                    "未找到制作按钮，请将界面缩放设置为"
                    "1x或移动您的鼠标"
                )
                self.window.activate_script_window()
                sys.exit()
            pag.moveTo(make_button_position)
            while True:
                if (
                    not self.cfg.ARGS.IGNORE
                    and not self.detection.is_material_complete()
                ):
                    logger.critical("材料用尽")
                    break
                if self.result.material == self.cfg.ARGS.CRAFT_LIMIT:
                    logger.info("达到制作限制")
                    break
                self.craft_item(accept_key)
                pag.moveTo(make_button_position)
        except KeyboardInterrupt:
            pass
        self.display_result()


class MoveApp(App):
    """Main controller for movement automation in Russian Fishing 4.

    Manages configuration, keyboard event listeners, and W/Shift key simulation.

    Attributes:
        cfg (CfgNode): Configuration node merged from YAML and CLI arguments.
        w_key_pressed (bool): Tracks current state of W key simulation.
    """

    def __init__(self, cfg, args, parser):
        """Initialize configuration, CLI arguments, and game window.

        1. Format keybinds in cfg node.
        2. Create w key flag.
        """
        super().__init__(cfg, args, parser)
        args_cfg = CN({"ARGS": config.dict_to_cfg(vars(self.args))})
        self.cfg.merge_from_other_cfg(args_cfg)
        self.cfg.merge_from_list(self.args.opts)
        self.cfg.freeze()

        utils.print_usage_box(
            f"按 {self.cfg.KEY.MOVE_PAUSE} 暂停，"
            f"{self.cfg.KEY.MOVE_QUIT} 退出。",
        )

        self.result = Result()
        self.window = Window()
        self.w_key_pressed = True

    def _on_release(self, key: keyboard.KeyCode) -> None:
        """Handle keyboard release events for script control.

        :param key: Key released by the user.
        :type key: keyboard.KeyCode
        """
        key = str(key).lower()
        if key == str(keyboard.KeyCode.from_char(self.cfg.KEY.MOVE_QUIT)):
            return False
        if key == str(keyboard.KeyCode.from_char(self.cfg.KEY.MOVE_PAUSE)):
            if self.w_key_pressed:
                self.w_key_pressed = False
                return True
            pag.keyDown("w")
            self.w_key_pressed = True

    def start(self) -> None:
        """Wrapper method that handle window activation and result display."""
        listener = keyboard.Listener(on_release=self._on_release)
        listener.start()
        self.window.activate_game_window()

        if self.cfg.ARGS.SHIFT:
            pag.keyDown("shift")
        pag.keyDown("w")
        while listener.is_alive():
            sleep(add_jitter(THREAD_CHECK_DELAY))


class HarvestApp(App):
    """Main application class for automating bait harvesting and hunger/comfort refill.

    This class manages the configuration, detection, and execution of the harvesting
    and refill processes. It also handles power-saving mode and check delays.

    Attributes:
        timer (Timer): Timer instance for managing cooldowns.
    """

    def __init__(self, cfg, args, parser):
        """Initialize the application.

        Loads configuration, parses command-line arguments, and sets up the game window,
        detection, and timer instances.
        """
        super().__init__(cfg, args, parser)
        args_cfg = CN({"ARGS": config.dict_to_cfg(vars(self.args))})
        self.cfg.merge_from_other_cfg(args_cfg)
        self.cfg.merge_from_list(self.args.opts)
        self.cfg.freeze()

        settings = Table(
            title="设置", show_header=False, box=box.HEAVY, min_width=36
        )
        settings.add_row("启动选项（最终）", " ".join(sys.argv[1:]))
        settings.add_row("节能模式", str(self.cfg.HARVEST.POWER_SAVING))
        settings.add_row("检查延迟", str(self.cfg.HARVEST.CHECK_DELAY))
        settings.add_row("能量阈值", str(self.cfg.STAT.ENERGY_THRESHOLD))
        settings.add_row("饥饿阈值", str(self.cfg.STAT.HUNGER_THRESHOLD))
        settings.add_row("舒适度阈值", str(self.cfg.STAT.COMFORT_THRESHOLD))
        print(settings)
        utils.print_usage_box(f"按 {self.cfg.KEY.QUIT} 退出。")

        self.result = HarvestResult()
        self.timer = Timer(self.cfg)
        self.window = Window()
        self.detection = Detection(self.cfg, self.window)

    def harvest_baits(self) -> None:
        """使用铲子/勺子收集饵料。

        在调用此方法之前应该先拿出挖掘工具。等待
        收集成功并按下空格键完成过程。
        """
        logger.info("收集饵料")
        pag.click()
        while not self.detection.is_harvest_success():
            sleep(add_jitter(LOOP_DELAY))
        pag.press("space")
        logger.info("饵料收集成功")
        sleep(add_jitter(ANIMATION_DELAY))

    def refill_player_stats(self) -> None:
        """使用茶和胡萝卜补充玩家属性。"""
        if not self.cfg.ARGS.REFILL:
            return

        logger.info("补充玩家属性")
        # 舒适度受天气影响，添加检查以避免过度饮用
        if self.detection.is_comfort_low() and self.timer.is_tea_drinkable():
            self._use_item("tea")
            self.result.tea += 1

        if self.detection.is_hunger_low():
            self._use_item("carrot")
            self.result.carrot += 1

    def _on_release(self, key: keyboard.KeyCode) -> None:
        """Handle keyboard release events for script control.

        :param key: Key released by the user.
        :type key: keyboard.KeyCode
        """
        # Trigger CTRL_C_EVENT, which will be caught in start() to simulate pressing
        # CTRL-C to terminate the script.
        if str(key).lower() == str(keyboard.KeyCode.from_char(self.cfg.KEY.QUIT)):
            os.kill(os.getpid(), signal.CTRL_C_EVENT)
            return False

    def _use_item(self, item: str) -> None:
        """使用快捷选择或菜单按名称访问物品。

        :param item: 要访问的物品名称。
        :type item: str
        """
        logger.info("使用物品：%s", item)
        key = str(self.cfg.KEY[item.upper()])
        if key != "-1":  # 使用快捷键
            pag.press(key)
        else:  # 打开食物菜单
            with pag.hold("t"):
                sleep(add_jitter(ANIMATION_DELAY))
                food_position = self.detection.get_food_position(item)
                pag.moveTo(food_position)
                pag.click()
        sleep(add_jitter(ANIMATION_DELAY))

    def start(self) -> None:
        """处理窗口激活和结果显示的包装方法。"""
        listener = keyboard.Listener(on_release=self._on_release)
        listener.start()

        self.window.activate_game_window()
        try:
            pag.press(str(self.cfg.KEY.DIGGING_TOOL))
            sleep(3)
            while True:
                self.refill_player_stats()
                if self.detection.is_energy_high():
                    self.harvest_baits()
                    self.result.bait += 1
                else:
                    logger.info("能量不足")

                if self.cfg.HARVEST.POWER_SAVING:
                    pag.press("esc")
                    sleep(self.cfg.HARVEST.CHECK_DELAY)
                    pag.press("esc")
                    sleep(ANIMATION_DELAY)
                else:
                    sleep(self.cfg.HARVEST.CHECK_DELAY)
        except KeyboardInterrupt:
            pass
        self.display_result()


@dataclass
class Part:
    name: str
    prompt: str
    color: str
    base: float = 0.0
    load_capacity: Optional[float] = None
    wear: Optional[float] = None
    real_load_capacity: Optional[float] = None
    pre_real_load_capacity: Optional[float] = None

    def calculate_real_load_capacity(self) -> None:
        self.real_load_capacity = (
            self.load_capacity * (1 - self.base) * (1 - self.wear / 100)
            + self.load_capacity * self.base
        )


class CalculateCommand(Enum):
    RESTART = "r"
    PREVIOUS = "p"
    PREVIOUS_REMAINING = "P"
    SKIP = "s"
    SKIP_REMAINING = "S"
    QUIT = "q"


class CalculateApp:
    def __init__(self, cfg, args, parser):
        _ = cfg, args, parser
        self.result = None
        self.parts = [
            Part(name="鱼竿", prompt="负载能力（公斤）", color="orange1", base=0.3),
            Part(name="卷线器机构", prompt="机构（公斤）", color="plum1", base=0.3),
            Part(name="卷线器摩擦制动", prompt="阻力（公斤）", color="gold1"),
            Part(name="鱼线", prompt="负载能力（公斤）", color="salmon1"),
            Part(name="前导线", prompt="负载能力（公斤）", color="pale_green1"),
            Part(name="鱼钩", prompt="负载能力（公斤）", color="sky_blue1"),
        ]
        self.friction_brake = next(
            part for part in self.parts if part.name == "卷线器摩擦制动"
        )

    def calculate_tackle_stats(self):
        previous = False
        for part in self.parts:
            try:
                if previous:
                    if part.pre_real_load_capacity is not None:
                        raise exceptions.PreviousError
                    else:
                        utils.print_error(f"未找到 {part.name} 的值。")
                part.load_capacity = self.get_validated_input(part, part.prompt)
                part.wear = self.get_validated_input(part, "磨损度（%）")
            except exceptions.SkipError:
                if part.real_load_capacity is not None:
                    part.real_load_capacity = None
                continue
            except exceptions.PreviousError:
                part.real_load_capacity = part.pre_real_load_capacity
            except exceptions.PreviousRemainingError:
                part.real_load_capacity = part.pre_real_load_capacity
                previous = True
            else:
                part.calculate_real_load_capacity()
            self.result.add_row(part.name, f"{part.real_load_capacity:.2f} 公斤")

    def get_validated_input(self, part: Part, prompt: str) -> float:
        while True:
            user_input = Prompt.ask(
                f"[{part.color}][{part.name}][/{part.color}] {prompt}"
            )
            match user_input.strip():
                case CalculateCommand.RESTART.value:
                    raise exceptions.RestartError
                case CalculateCommand.PREVIOUS.value:
                    if part.pre_real_load_capacity is None:
                        utils.print_error(f"未找到 {part.name} 的值。")
                        continue
                    raise exceptions.PreviousError
                case CalculateCommand.PREVIOUS_REMAINING.value:
                    if part.pre_real_load_capacity is None:
                        utils.print_error(f"未找到 {part.name} 的值。")
                        continue
                    raise exceptions.PreviousRemainingError
                case CalculateCommand.SKIP.value:
                    raise exceptions.SkipError
                case CalculateCommand.SKIP_REMAINING.value:
                    raise exceptions.SkipRemainingError
                case CalculateCommand.QUIT.value:
                    raise exceptions.QuitError

            try:
                number = float(user_input)
                if prompt.startswith("磨损度"):
                    if not (0 <= number <= 100):
                        utils.print_error("磨损度必须在0到100之间。")
                        continue
                elif number < 0:
                    utils.print_error("值必须为非负数。")
                    continue
                return number
            except ValueError:
                utils.print_error("无效输入。请重试。")

    def reset_stats(self) -> None:
        for part in self.parts:
            part.pre_real_load_capacity = part.real_load_capacity
            part.real_load_capacity = None
        self.result = Table(
            "结果",
            title="钓组属性",
            show_header=False,
            box=box.HEAVY,
            min_width=36,
        )

    def update_result(self) -> None:
        valid_parts = [p for p in self.parts if p.real_load_capacity is not None]
        if not valid_parts:
            return
        weakest_part = min(valid_parts, key=lambda x: x.real_load_capacity)
        self.result.add_row("最薄弱部件", weakest_part.name)

        if self.friction_brake.real_load_capacity is None:
            return
        # k / 30 * drag < weakest -> k < weakest * 30 / drag
        try:
            recommend_friction_brake = min(
                MAX_FRICTION_BRAKE - 1,
                (
                    weakest_part.real_load_capacity
                    * MAX_FRICTION_BRAKE
                    / self.friction_brake.real_load_capacity
                ),
            )
            self.result.add_row(
                "推荐摩擦制动",
                f"{int(recommend_friction_brake):2d}",
            )
        except ZeroDivisionError:
            pass  # 静默失败

    def start(self):
        """运行摩擦制动器计算的主函数。

        提示用户输入，计算结果，并在表格中显示它们。
        """
        utils.print_usage_box(
            "命令：\n"
            "r：重新开始\n"
            "s：跳过一个部件\n"
            "S：跳过剩余部件\n"
            "p：对某个部件使用之前的值\n"
            "P：对剩余部件使用之前的值\n"
            "q：退出"
        )
        utils.print_hint_box("按V键并点击齿轮图标查看部件。")

        while True:
            self.reset_stats()
            try:
                self.calculate_tackle_stats()
            except exceptions.SkipRemainingError:
                pass
            except exceptions.RestartError:
                continue
            except exceptions.QuitError:
                print("Bye.")
                break
            if self.result.rows:
                self.update_result()
                print(self.result)


class FrictionBrakeApp(App):
    """Main application class for automating friction brake adjustments.

    This class manages the configuration, detection, and execution of the friction
    brake automation process. It also handles key bindings for exiting and resetting.

    Attributes:
        cfg (CfgNode): Configuration node merged from YAML and CLI arguments.
        friction_brake (FrictionBrake): Friction brake controller instance.
    """

    def __init__(self, cfg, args, parser):
        """Initialize the application.

        1. Check the game window state.
        2. Format keybinds in cfg node.
        3. Display cfg node.
        4. Initialize a friction brake instance.
        """
        super().__init__(cfg, args, parser)
        args_cfg = CN({"ARGS": config.dict_to_cfg(vars(self.args))})
        self.cfg.merge_from_other_cfg(args_cfg)
        self.cfg.merge_from_list(self.args.opts)
        self.cfg.freeze()

        settings = Table(
            title="设置", show_header=False, box=box.HEAVY, min_width=36
        )
        settings.add_row("启动选项（最终）", " ".join(sys.argv[1:]))
        settings.add_row("初始摩擦制动", str(self.cfg.FRICTION_BRAKE.INITIAL))
        settings.add_row("最大摩擦制动", str(self.cfg.FRICTION_BRAKE.MAX))
        settings.add_row("启动延迟", str(self.cfg.FRICTION_BRAKE.START_DELAY))
        settings.add_row("增加延迟", str(self.cfg.FRICTION_BRAKE.INCREASE_DELAY))
        settings.add_row("灵敏度", self.cfg.FRICTION_BRAKE.SENSITIVITY)
        print(settings)

        utils.print_usage_box(
            f"按 {self.cfg.KEY.FRICTION_BRAKE_RESET} 重置摩擦制动，"
            f"{self.cfg.KEY.FRICTION_BRAKE_QUIT} 退出。"
        )

        self.window = Window()
        if not self.is_game_window_valid():
            utils.safe_exit()

        self.detection = Detection(self.cfg, self.window)
        self.friction_brake = FrictionBrake(self.cfg, Lock(), self.detection)

    def is_game_window_valid(self) -> bool:
        """检查游戏窗口模式和大小是否有效。

        :return: 如果有效返回True，否则返回False
        :rtype: bool
        """
        if self.window.is_title_bar_exist():
            logger.info("检测到窗口模式。不要移动游戏窗口")
        if self.window.is_size_supported():
            logger.info("支持的窗口大小。不要更改游戏窗口大小")
            return True
        logger.critical('窗口模式必须是"无边框窗口"或"窗口模式"')
        logger.critical(
            "不支持的窗口大小 '%s'，使用 '2560x1440'、'1920x1080' 或 '1600x900'",
            self.window.get_resolution_str(),
        )
        return False

    def _on_release(self, key: keyboard.KeyCode) -> None:
        """处理退出和终止事件。

        :param key: 被释放的键。
        :type key: keyboard.KeyCode
        """
        key = str(key).lower()
        if key == str(keyboard.KeyCode.from_char(self.cfg.KEY.FRICTION_BRAKE_QUIT)):
            self.friction_brake.monitor_process.terminate()
            return False
        if key == str(keyboard.KeyCode.from_char(self.cfg.KEY.FRICTION_BRAKE_RESET)):
            self.friction_brake.reset(self.cfg.FRICTION_BRAKE.INITIAL)

    def start(self):
        """处理窗口激活和结果显示的包装方法。"""
        listener = keyboard.Listener(on_release=self._on_release)
        listener.start()
        self.window.activate_game_window()
        self.friction_brake.monitor_process.start()
        self.friction_brake.reset(self.cfg.FRICTION_BRAKE.INITIAL)

        while listener.is_alive():
            sleep(THREAD_CHECK_DELAY)
