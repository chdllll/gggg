import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from api import DeepSeekClient, Message
from database import Character, World, DatabaseManager


@dataclass
class RemoteCharacterEvent:
    def __init__(
        self,
        id: int = None,
        character_id: int = None,
        character_name: str = None,
        event_type: str = None,
        description: str = None,
        target_date: str = None,
        target_time: str = None,
        is_processed: bool = False,
        created_at: str = None
    ):
        self.id = id
        self.character_id = character_id
        self.character_name = character_name
        self.event_type = event_type
        self.description = description
        self.target_date = target_date
        self.target_time = target_time
        self.is_processed = is_processed
        self.created_at = created_at


class RemoteEventManager:
    def __init__(self, deepseek_client: DeepSeekClient, db_manager: DatabaseManager):
        self.deepseek_client = deepseek_client
        self.db = db_manager
        self.last_processed_date = None
        self.communication_request_counts = {}
    
    async def initialize_database(self):
        """初始化数据库表"""
        cursor = self.db.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS remote_character_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                character_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                target_date TEXT NOT NULL,
                target_time TEXT NOT NULL,
                is_processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        ''')
        
        self.db.conn.commit()
        print("远程角色事件表初始化完成")
    
    async def check_and_process_events(self, world: World, model: str = "deepseek-chat") -> List[Dict]:
        """检查并处理事件，返回处理的事件列表"""
        current_date = world.current_date
        current_time = world.current_time
        
        print(f"\n检查远程角色事件，当前时间: {current_date} {current_time}")
        
        await self._generate_events_for_remote_characters(world, model)
        processed_events = await self._process_pending_events(world, current_date, current_time)
        
        return processed_events
    
    async def _generate_events_for_remote_characters(self, world: World, model: str = "deepseek-chat"):
        """为外地角色生成事件"""
        user_location = world.user_location
        
        all_characters = self.db.get_characters_by_world(world.id)
        remote_characters = [
            char for char in all_characters 
            if char.location and char.location != user_location
        ]
        
        if not remote_characters:
            print("没有外地角色")
            return
        
        print(f"发现{len(remote_characters)}个外地角色")
        
        for character in remote_characters:
            await self._generate_event_for_character(character, world, model)
    
    async def _generate_event_for_character(
        self,
        character: Character,
        world: World,
        model: str = "deepseek-chat"
    ):
        """为单个角色生成事件"""
        existing_events = self._get_pending_events_for_character(character.id)
        
        if existing_events:
            print(f"角色 {character.name} 已有{len(existing_events)}个待处理事件，跳过生成")
            return
        
        user_location = world.user_location or "未知"
        
        # 为了测试，直接生成模拟事件，不调用API
        import random
        event_types = ["位置跃迁", "通讯请求", "记忆变化", "生活事件"]
        event_type = random.choice(event_types)
        
        if event_type == "位置跃迁":
            description = f"从{character.location}移动到其他位置"
        elif event_type == "通讯请求":
            description = "通过电话联系用户"
        elif event_type == "记忆变化":
            description = "想起了重要的事情"
        else:
            description = "日常生活中发生了一些事情"
        
        target_date, target_time = self._calculate_target_time(world.current_date, world.current_time)
        
        event = RemoteCharacterEvent(
            character_id=character.id,
            character_name=character.name,
            event_type=event_type,
            description=description,
            target_date=target_date,
            target_time=target_time,
            is_processed=False
        )
        
        self._save_event_to_database(event)
        print(f"为角色 {character.name} 生成事件: {event_type} - {description}")
    
    def _calculate_target_time(self, current_date: str, current_time: str) -> Tuple[str, str]:
        """计算目标时间（当前时间的一天后）"""
        try:
            date_parts = current_date.split('-')
            year = int(date_parts[0])
            month = int(date_parts[1])
            day = int(date_parts[2])
            
            time_parts = current_time.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            second = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            target_datetime = datetime(year, month, day, hour, minute, second) + timedelta(days=1)
            
            target_date = target_datetime.strftime('%Y-%m-%d')
            target_time = target_datetime.strftime('%H:%M:%S')
            
            return target_date, target_time
        except Exception as e:
            print(f"计算目标时间时发生错误: {e}")
            return current_date, current_time
    
    def _save_event_to_database(self, event: RemoteCharacterEvent):
        """保存事件到数据库"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            INSERT INTO remote_character_events 
            (character_id, character_name, event_type, description, target_date, target_time, is_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.character_id,
            event.character_name,
            event.event_type,
            event.description,
            event.target_date,
            event.target_time,
            0
        ))
        self.db.conn.commit()
    
    def _get_pending_events_for_character(self, character_id: int) -> List[RemoteCharacterEvent]:
        """获取角色的待处理事件"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM remote_character_events 
            WHERE character_id = ? AND is_processed = 0
            ORDER BY target_date, target_time
        ''', (character_id,))
        rows = cursor.fetchall()
        return [RemoteCharacterEvent(*row) for row in rows]
    
    async def _process_pending_events(self, world: World, current_date: str, current_time: str) -> List[Dict]:
        """处理待处理的事件，返回处理的事件列表"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM remote_character_events 
            WHERE is_processed = 0 
            AND (target_date < ? OR (target_date = ? AND target_time <= ?))
            ORDER BY target_date, target_time
        ''', (current_date, current_date, current_time))
        rows = cursor.fetchall()
        
        print(f"[DEBUG] 查询条件: is_processed=0 AND (target_date < '{current_date}' OR (target_date = '{current_date}' AND target_time <= '{current_time}'))")
        print(f"[DEBUG] 查询结果: {len(rows)} 条记录")
        
        if not rows:
            print("没有待处理的事件")
            return []
        
        events = [RemoteCharacterEvent(*row) for row in rows]
        print(f"发现{len(events)}个待处理事件")
        
        processed_events = []
        for event in events:
            print(f"处理事件: {event.character_name} - {event.event_type} - {event.description}")
            print(f"  事件时间: {event.target_date} {event.target_time}")
            print(f"  当前时间: {current_date} {current_time}")
            await self._process_single_event(event, world)
            self._mark_event_as_processed(event.id)
            
            processed_events.append({
                'character_name': event.character_name,
                'event_type': event.event_type,
                'description': event.description,
                'needs_user_help': event.event_type == "通讯请求",
                'is_subjective': event.event_type == "通讯请求"
            })
        
        return processed_events
    
    async def _process_single_event(self, event: RemoteCharacterEvent, world: World):
        """处理单个事件"""
        print(f"处理事件: {event.character_name} - {event.event_type} - {event.description}")
        
        if event.event_type == "通讯请求":
            await self._process_communication_request(event)
        elif event.event_type == "记忆变化":
            await self._process_memory_change(event, world)
        elif event.event_type == "生活事件":
            await self._process_life_event(event)
    
    async def _process_communication_request(self, event: RemoteCharacterEvent):
        """处理通讯请求事件"""
        try:
            character = self.db.get_character(event.character_id)
            if not character:
                print(f"找不到角色 {event.character_name}")
                return
            
            self.db.create_incoming_call_request(
                world_id=character.world_id,
                character_id=event.character_id,
                character_name=event.character_name,
                request_date=event.target_date,
                request_time=event.target_time
            )
            
            print(f"角色 {event.character_name} 请求通讯，已创建来电请求")
        except Exception as e:
            print(f"处理通讯请求时发生错误: {e}")
    
    async def _process_memory_change(self, event: RemoteCharacterEvent, world: World):
        """处理记忆变化事件"""
        try:
            memory_content = f"【事件】{event.description}"
            
            self.db.create_memory(
                world_id=world.id,
                character_id=event.character_id,
                memory_type="事件",
                content=memory_content,
                importance=5,
                segment=1
            )
            print(f"为角色 {event.character_name} 添加记忆: {memory_content}")
        except Exception as e:
            print(f"处理记忆变化时发生错误: {e}")
    
    async def _process_life_event(self, event: RemoteCharacterEvent):
        """处理生活事件"""
        print(f"角色 {event.character_name} 发生生活事件: {event.description}")
    
    def _mark_event_as_processed(self, event_id: int):
        """标记事件为已处理"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            UPDATE remote_character_events 
            SET is_processed = 1 
            WHERE id = ?
        ''', (event_id,))
        self.db.conn.commit()
    
    def get_communication_request_count(self, character_id: int) -> int:
        """获取角色的通讯请求次数"""
        return self.communication_request_counts.get(character_id, 0)
    
    def clear_communication_request_counts(self):
        """清空通讯请求计数"""
        self.communication_request_counts.clear()
    
    async def cleanup_old_events(self, days: int = 7):
        """清理旧事件"""
        cursor = self.db.conn.cursor()
        cursor.execute(f'''
            DELETE FROM remote_character_events 
            WHERE created_at < datetime('now', '-{days} days')
        ''')
        deleted_count = cursor.rowcount
        self.db.conn.commit()
        print(f"清理了{deleted_count}个旧事件")
