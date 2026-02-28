from datetime import datetime, timedelta
from typing import Tuple

class TimeCalculator:
    def __init__(self):
        pass
    
    def parse_time_string(self, time_str: str) -> Tuple[int, int, int, int, int, int]:
        """
        解析时间字符串，返回年、月、日、时、分、秒
        
        参数:
            time_str: 时间字符串，支持以下格式：
                - "2024年1月1日 8时30分15秒" 或 "2024年1月1日 8时" (中文格式)
                - "2026-02-08 20:17:49" 或 "2026-02-08" (ISO格式)
        
        返回:
            (year, month, day, hour, minute, second)
        """
        try:
            if '-' in time_str:
                parts = time_str.split(' ')
                
                date_part = parts[0]
                time_part = parts[1] if len(parts) > 1 else "00:00:00"
                
                date_parts = date_part.split('-')
                year = int(date_parts[0])
                month = int(date_parts[1])
                day = int(date_parts[2])
                
                time_parts = time_part.split(':')
                hour = int(time_parts[0]) if len(time_parts) > 0 else 0
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                second = int(time_parts[2]) if len(time_parts) > 2 else 0
            else:
                parts = time_str.split(' ')
                
                date_part = parts[0]
                time_part = parts[1] if len(parts) > 1 else "0时0分0秒"
                
                date_part = date_part.replace('第', '')
                date_parts = date_part.replace('年', ' ').replace('月', ' ').replace('日', '').split()
                year = int(date_parts[0])
                month = int(date_parts[1])
                day = int(date_parts[2])
                
                time_parts = time_part.replace('时', ' ').replace('分', ' ').replace('秒', '').split()
                hour = int(time_parts[0]) if len(time_parts) > 0 else 0
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                second = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            return year, month, day, hour, minute, second
        except Exception as e:
            print(f"解析时间字符串失败: {e}")
            return 2024, 1, 1, 8, 0, 0
    
    def format_time_string(self, year: int, month: int, day: int, hour: int, minute: int, second: int) -> str:
        """
        格式化时间字符串
        
        参数:
            year: 年
            month: 月
            day: 日
            hour: 时
            minute: 分
            second: 秒
        
        返回:
            时间字符串，格式如 "2024-01-01 08:30:15" (ISO格式)
        """
        return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
    
    def add_seconds(self, time_str: str, seconds: int) -> str:
        """
        在当前时间上增加指定的秒数
        
        参数:
            time_str: 当前时间字符串
            seconds: 要增加的秒数
        
        返回:
            新的时间字符串
        """
        try:
            year, month, day, hour, minute, second = self.parse_time_string(time_str)
            
            dt = datetime(year, month, day, hour, minute, second)
            new_dt = dt + timedelta(seconds=seconds)
            
            return self.format_time_string(new_dt.year, new_dt.month, new_dt.day, 
                                       new_dt.hour, new_dt.minute, new_dt.second)
        except Exception as e:
            print(f"时间计算失败: {e}")
            return time_str
    
    def get_time_diff_seconds(self, time_str1: str, time_str2: str) -> int:
        """
        计算两个时间之间的秒数差
        
        参数:
            time_str1: 时间字符串1
            time_str2: 时间字符串2
        
        返回:
            秒数差（time_str2 - time_str1）
        """
        try:
            year1, month1, day1, hour1, minute1, second1 = self.parse_time_string(time_str1)
            year2, month2, day2, hour2, minute2, second2 = self.parse_time_string(time_str2)
            
            dt1 = datetime(year1, month1, day1, hour1, minute1, second1)
            dt2 = datetime(year2, month2, day2, hour2, minute2, second2)
            
            return int((dt2 - dt1).total_seconds())
        except Exception as e:
            print(f"时间差计算失败: {e}")
            return 0
    
    def get_time_description(self, seconds: int) -> str:
        """
        将秒数转换为人类可读的时间描述
        
        参数:
            seconds: 秒数
        
        返回:
            时间描述，如 "2小时30分15秒"
        """
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes}分{secs}秒"
            else:
                return f"{minutes}分"
        elif seconds < 86400:
            hours = seconds // 3600
            remaining = seconds % 3600
            minutes = remaining // 60
            secs = remaining % 60
            parts = []
            if hours > 0:
                parts.append(f"{hours}小时")
            if minutes > 0:
                parts.append(f"{minutes}分")
            if secs > 0:
                parts.append(f"{secs}秒")
            return "".join(parts)
        else:
            days = seconds // 86400
            remaining = seconds % 86400
            hours = remaining // 3600
            remaining = remaining % 3600
            minutes = remaining // 60
            secs = remaining % 60
            parts = []
            if days > 0:
                parts.append(f"{days}天")
            if hours > 0:
                parts.append(f"{hours}小时")
            if minutes > 0:
                parts.append(f"{minutes}分")
            if secs > 0:
                parts.append(f"{secs}秒")
            return "".join(parts)