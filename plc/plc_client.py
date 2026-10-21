import logging
import os
from threading import Lock

import requests

URL = "https://192.168.0.2/api/jsonrpc"
USER = "python_user"

logger = logging.getLogger(__name__)
plc_lock = Lock()


def execute_api(method, params):
    password = os.environ.get("PLC_PASSWORD")
    if not password:
        raise RuntimeError("尚未設定 PLC_PASSWORD，請在啟動 Django 前設定")

    # 同一個 Django 程序內，依序處理 PLC 請求
    with plc_lock, requests.Session() as session:
        # 僅供目前本機模擬測試，正式環境改用可信任憑證
        session.verify = False
        request_id = 0
        logged_in = False

        def call_api(api_method, api_params=None):
            nonlocal request_id
            request_id += 1

            body = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": api_method,
            }

            if api_params is not None:
                body["params"] = api_params

            response = session.post(URL, json=body, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                error = data["error"]
                raise RuntimeError(
                    f"{api_method}：{error.get('code')} "
                    f"{error.get('message', 'API 錯誤')}"
                )

            return data["result"]

        try:
            login = call_api("Api.Login", {
                "user": USER,
                "password": password,
            })

            session.headers["X-Auth-Token"] = login["token"]
            logged_in = True

            return call_api(method, params)

        finally:
            if logged_in:
                try:
                    call_api("Api.Logout")
                except (requests.RequestException, RuntimeError, ValueError, KeyError):
                    # 登出失敗不覆蓋前面讀寫的結果
                    logger.warning("PLC 登出失敗，請留意連線狀況")


def send_command(command):
    tags = {
        "start": '"Motor_POST_DB".StartReq',
        "stop": '"Motor_POST_DB".StopReq',
    }

    if command not in tags:
        raise ValueError("不支援的指令")

    result = execute_api("PlcProgram.Write", {
        "var": tags[command],
        "value": True,
        "mode": "simple",
    })

    if result is not True:
        raise RuntimeError(f"PLC 未確認寫入成功：{result}")

    return result


def read_motor():
    result = execute_api("PlcProgram.Read", {
        "var": '"Motor_POST_DB".Motor',
        "mode": "simple",
    })

    if not isinstance(result, bool):
        raise RuntimeError("Motor 的回傳值不是 BOOL，請確認 PLC 變數")

    return result

# 模擬測試範圍，實際應依設備調整
SPEED_MIN = 0
SPEED_MAX = 3000


def set_motor_speed(rpm):
    if type(rpm) is not int:
        raise ValueError("轉速必須是整數")

    if not SPEED_MIN <= rpm <= SPEED_MAX:
        raise ValueError(
            f"轉速必須介於 {SPEED_MIN}～{SPEED_MAX} rpm"
        )

    result = execute_api("PlcProgram.Write", {
        "var": '"Motor_POST_DB".SpeedSetpoint',
        "value": rpm,
        "mode": "simple",
    })

    if result is not True:
        raise RuntimeError(f"PLC 未確認寫入成功：{result}")

    return result