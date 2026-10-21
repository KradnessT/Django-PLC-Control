import json
import requests

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .plc_client import read_motor, send_command
from .plc_client import set_motor_speed, SPEED_MIN, SPEED_MAX

@require_GET
def index(request):
    return render(request, "plc/index.html")


@never_cache
@require_GET
def motor_status(request):
    try:
        motor = read_motor()
        return JsonResponse({"ok": True, "motor": motor})

    except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
        return JsonResponse(
            {"ok": False, "message": str(exc)},
            status=502,
        )


@require_POST
def motor_command(request, command):
    if command not in ("start", "stop"):
        return JsonResponse(
            {"ok": False, "message": "不支援的指令"},
            status=400,
        )

    try:
        send_command(command)
        return JsonResponse({
            "ok": True,
            "message": "啟動請求已寫入 PLC"
                       if command == "start"
                       else "停止請求已寫入 PLC",
        })

    except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
        return JsonResponse(
            {"ok": False, "message": str(exc)},
            status=502,
        )


@require_POST
def motor_speed(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"ok": False, "message": "JSON 格式錯誤"},
            status=400,
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {"ok": False, "message": "資料必須是 JSON 物件"},
            status=400,
        )

    rpm = data.get("rpm")

    if type(rpm) is not int or not SPEED_MIN <= rpm <= SPEED_MAX:
        return JsonResponse(
            {
                "ok": False,
                "message": (
                    f"請輸入 {SPEED_MIN}～{SPEED_MAX} 的整數轉速"
                ),
            },
            status=400,
        )

    try:
        set_motor_speed(rpm)

        return JsonResponse({
            "ok": True,
            "message": f"轉速設定值 {rpm} rpm 已寫入 PLC",
        })

    except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
        return JsonResponse(
            {"ok": False, "message": str(exc)},
            status=502,
        )