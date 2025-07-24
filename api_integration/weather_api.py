# weather_api.py
# 天气查询系统主程序
# 功能：通过心知天气API获取指定地点未来3天天气预报

import requests
from datetime import datetime, timedelta
from config import SENIVERSE_API_KEY

def get_weather_forecast(location):
    """
    获取指定地点未来3天天气预报
    
    参数:
        location (str): 要查询的地点名称(中文/拼音)
    
    返回:
        dict: 包含以下字段的结构化数据:
            - formatted: 格式化后的天气信息字符串
            - raw_data: 原始天气数据
            - status: 请求状态(success/error)
            - message: 状态详细信息
    """
    # API端点
    url = "https://api.seniverse.com/v3/weather/daily.json"
    
    # API请求参数
    params = {
        "key": SENIVERSE_API_KEY,
        "location": location,
        "language": "zh-Hans",
        "unit": "c",
        "start": "0",
        "days": "3"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        weather_data = response.json()
        
        if "results" not in weather_data:
            return {
                "status": "error",
                "message": "未获取到有效天气数据",
                "formatted": "天气查询失败: 未获取到有效数据"
            }
        
        # 提取原始数据
        raw_data = {
            "location": weather_data["results"][0]["location"]["name"],
            "forecast": [],
            "update_time": weather_data["results"][0]["last_update"]
        }
        
        # 处理预报数据
        for daily in weather_data["results"][0]["daily"]:
            raw_data["forecast"].append({
                "date": daily["date"],
                "day_weather": daily["text_day"],
                "night_weather": daily["text_night"],
                "high_temp": daily["high"],
                "low_temp": daily["low"]
            })
        
        # 格式化天气信息
        formatted_text = _format_weather_data(raw_data)
        
        return {
            "status": "success",
            "message": "获取成功",
            "formatted": formatted_text,
            "raw_data": raw_data
        }
        
    except requests.exceptions.RequestException as e:
        error_msg = f"天气查询失败: {str(e)}"
        return {
            "status": "error",
            "message": error_msg,
            "formatted": error_msg
        }
    except Exception as e:
        error_msg = f"处理天气数据时出错: {str(e)}"
        return {
            "status": "error",
            "message": error_msg,
            "formatted": error_msg
        }

def _format_weather_data(raw_data):
    """格式化天气数据为字符串"""
    # 获取当前日期
    today = datetime.now().date()
    date_labels = {
        today.strftime("%Y-%m-%d"): "今天",
        (today + timedelta(days=1)).strftime("%Y-%m-%d"): "明天",
        (today + timedelta(days=2)).strftime("%Y-%m-%d"): "后天"
    }
    
    forecast_lines = []
    for day in raw_data["forecast"]:
        # 获取日期标签（今天/明天/后天），如果没有匹配则使用原始日期
        date_label = date_labels.get(day['date'], day['date'])
        forecast_lines.append(
            f"{date_label}({day['date']}): "
            f"白天{day['day_weather']}/夜间{day['night_weather']}, "
            f"温度{day['low_temp']}~{day['high_temp']}℃"
        )
    
    return (
        f"地点: {raw_data['location']}\n"
        f"更新时间: {raw_data['update_time']}\n"
        f"未来3天天气预报:\n"
        + "\n".join(forecast_lines)
    )


if __name__ == "__main__":
    print("天气查询系统 (输入q退出)")
    
    while True:
        location = input("\n请输入要查询的地点: ").strip()
        if location.lower() in ['q', 'quit', 'exit']:
            break
            
        if not location:
            print("⚠ 请输入有效地点名称")
            continue
            
        weather_info = get_weather_forecast(location)
        print("\n" + weather_info["formatted"])
    
    print("感谢使用天气查询系统！")