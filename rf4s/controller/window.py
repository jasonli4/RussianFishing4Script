"""Module for window controller.

This module provides functionality for managing and interacting with the game window
and terminal window in Russian Fishing 4.

.. moduleauthor:: Derek Lee <dereklee0310@gmail.com>
"""

from pathlib import Path
from time import sleep

# import win32api, win32con
import pyautogui as pag
import win32con
import win32gui

from rf4s import utils
from rf4s.controller import logger

ANIMATION_DELAY = 0.5


class Window:
    """Controller for terminal and game windows management.

    This class handles window focus, size detection, and screenshot functionality
    for the game and terminal windows.

    Attributes:
        game_title (str): Title of the game window.
        terminal_hwnd (int): Handle of the terminal window.
    """

    def __init__(self, game_title: str = "Russian Fishing 4"):
        """Set the hwnd of the terminal where user run the script.

        We didn't retrieve the game window's hwnd here because we don't want to check
        if the window is open right away. Instead, we perform the check after the
        configuration is set.

        :param game_title: Title of the game, defaults to "Russian Fishing 4".
        :type game_title: str, optional
        """
        self.game_title = game_title
        self.terminal_hwnd = win32gui.GetForegroundWindow()

    def _get_game_hwnd(self) -> int:
        """Get the handle of the game window.

        :return: Process handle of the game window.
        :rtype: int
        """
        # 使用更可靠的方法查找游戏窗口
        # 1. 先尝试直接查找
        hwnd = win32gui.FindWindow(None, self.game_title)

        # 2. 如果找到窗口，验证它是否是有效的游戏窗口
        if hwnd != 0:
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            # 如果窗口太小，可能不是主窗口，继续查找
            if width >= 800 and height >= 600:
                return hwnd

        # 3. 枚举所有窗口，找到最可能的游戏主窗口
        def enum_callback(candidate_hwnd, candidates):
            if win32gui.IsWindowVisible(candidate_hwnd):
                title = win32gui.GetWindowText(candidate_hwnd)
                if title and self.game_title in title:
                    rect = win32gui.GetWindowRect(candidate_hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    # 只收集合理大小的窗口
                    if width >= 800 and height >= 600:
                        candidates.append({
                            'hwnd': candidate_hwnd,
                            'width': width,
                            'height': height,
                            'area': width * height
                        })

        candidates = []
        win32gui.EnumWindows(enum_callback, candidates)

        if not candidates:
            logger.critical(
                "无法定位游戏窗口，请打开游戏后重试\n"
                "提示：可以运行 diagnose_windows.py 来诊断窗口问题"
            )
            utils.safe_exit()

        # 4. 选择面积最大的窗口作为游戏主窗口
        candidates.sort(key=lambda x: x['area'], reverse=True)
        selected = candidates[0]

        logger.debug(
            f"找到游戏窗口: {self.game_title} "
            f"(大小: {selected['width']}x{selected['height']}, "
            f"句柄: {selected['hwnd']})"
        )

        return selected['hwnd']

    def is_title_bar_exist(self) -> bool:
        """Check if the game window is in windowed mode.

        :return: True if the game window has a title bar, False otherwise.
        :rtype: bool
        """
        style = win32gui.GetWindowLong(self._get_game_hwnd(), win32con.GWL_STYLE)
        return style & win32con.WS_CAPTION

    def get_box(self) -> tuple[int, int, int, int]:
        """Get the coordinates and dimensions of the game window.

        :return: Tuple containing (x, y, width, height) of the game window.
        :rtype: tuple[int, int, int, int]
        """
        game_hwnd = self._get_game_hwnd()

        # 尝试激活游戏窗口，确保它在前台
        try:
            win32gui.SetForegroundWindow(game_hwnd)
            sleep(0.3)  # 等待窗口激活
        except:
            pass

        # 使用 GetWindowRect 获取整个窗口大小（更可靠）
        left, top, right, bottom = win32gui.GetWindowRect(game_hwnd)
        width = right - left
        height = bottom - top

        logger.debug(f"窗口外部大小: {width}x{height}, 位置: ({left}, {top})")

        # 检查是否是窗口模式（有标题栏）
        style = win32gui.GetWindowLong(game_hwnd, win32con.GWL_STYLE)
        has_title_bar = style & win32con.WS_CAPTION

        # 如果是窗口模式，需要减去标题栏和边框
        if has_title_bar:
            # Windows 10 标题栏高度约 32px，左右边框各约 8px
            content_width = width - 16  # 左右边框
            content_height = height - 32  # 标题栏
            # 基础坐标也需要调整
            base_x = left + 8
            base_y = top + 31
            logger.debug(f"窗口模式检测到，内容区域大小: {content_width}x{content_height}")
        else:
            # 无边框窗口或全屏
            content_width = width
            content_height = height
            base_x = left
            base_y = top
            logger.debug(f"无边框/全屏模式，内容区域大小: {content_width}x{content_height}")

        # 验证窗口大小
        if content_width < 1000 or content_height < 500:
            logger.warning(
                f"检测到异常窗口大小 {content_width}x{content_height}，"
                f"可能游戏窗口还未完全启动。请确保游戏窗口已完全显示。"
            )
            # 不再重试，直接使用检测到的值（让用户看到实际检测到的大小）
            # 这样可以帮助诊断问题
        else:
            logger.info(f"检测到游戏窗口大小: {content_width}x{content_height}")

        return base_x, base_y, content_width, content_height

    def get_base_coordinates(self) -> tuple[int, int]:
        """Get the base coordinates of the game window.

        :return: Tuple containing (x, y) of the base coordinates.
        :rtype: tuple[int, int]
        """
        return self.get_box()[:2]

    def get_resolution_str(self) -> str:
        """Get the resolution of the game window.

        :return: Game window resolution string (axb).
        :rtype: str
        """
        width, height = self.get_box()[2:]

        # 支持的分辨率，允许±10像素的误差
        supported_resolutions = [
            (2560, 1440),
            (1920, 1080),
            (1600, 900),
        ]

        # 查找最接近的匹配分辨率
        for supported_width, supported_height in supported_resolutions:
            if abs(width - supported_width) <= 10 and abs(height - supported_height) <= 10:
                return f"{supported_width}x{supported_height}"

        # 如果没有匹配，返回实际大小
        return f"{width}x{height}"

    def activate_script_window(self) -> None:
        """Focus the terminal where user run the script."""
        pag.press("alt")
        win32gui.SetForegroundWindow(self.terminal_hwnd)
        sleep(ANIMATION_DELAY)

    def activate_game_window(self) -> None:
        """Focus game window."""
        pag.press("alt")
        win32gui.SetForegroundWindow(self._get_game_hwnd())
        sleep(ANIMATION_DELAY)

    def is_size_supported(self) -> bool:
        """Check if the game window size is supported.

        :return: True if it's supported, False otherwise.
        :rtype: bool
        """
        width, height = self.get_box()[2:]

        # 支持的分辨率，允许±10像素的误差（适应不同Windows版本的边框差异）
        supported_resolutions = [
            (2560, 1440),
            (1920, 1080),
            (1600, 900),
        ]

        for supported_width, supported_height in supported_resolutions:
            if abs(width - supported_width) <= 10 and abs(height - supported_height) <= 10:
                logger.debug(
                    f"窗口大小 {width}x{height} 匹配支持的分辨率 {supported_width}x{supported_height}"
                )
                return True

        return False

    def save_screenshot(self, filepath: Path) -> None:
        """Save a screenshot of the game window to the screenshots directory."""
        pag.screenshot(
            imageFilename=filepath,
            region=self.get_box(),
        )


if __name__ == "__main__":
    w = Window("Russian Fishing 4")
    # w.activate_game_window()
    print(w.get_box())
    print(w.get_base_coordinates())
    print(w.get_resolution_str())
    print(w.is_size_supported())

# SetForegroundWindow bug reference :
# https://stackoverflow.com/questions/56857560/win32gui-setforegroundwindowhandle-not-working-in-loop
