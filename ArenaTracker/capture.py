import time, numpy as np, mss, pyautogui
from config import HOVER_DELAY_SEC


def bring_front():
    try:
        import appscript

        se = appscript.app('System Events')
        apps = [
            p
            for p in se.application_processes.get()
            if 'Arena' in p.name.get() or 'MTGA' in p.name.get()
        ]
        if apps:
            apps[0].frontmost.set(True)
    except Exception:
        pass
    w, h = pyautogui.size()
    pyautogui.click(w // 2, h // 2)


def mouse_safe():
    try:
        pyautogui.moveTo(1, 1, duration=0)
    except Exception:
        pass


def screenshot() -> np.ndarray:
    with mss.mss() as sct:
        mon = sct.monitors[0]
        img = np.array(sct.grab(mon))[:, :, :3]
        return img


def hover_screenshot(cx: int, cy: int):
    try:
        pyautogui.moveTo(cx, cy, duration=0)
        time.sleep(HOVER_DELAY_SEC)
        img = screenshot()
    finally:
        mouse_safe()
    return img
