import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from database import DatabaseManager, Memory
from dataclasses import dataclass

@dataclass
class TimelineEvent:
    def __init__(self, character_id: int, character_name: str, event_type: str, 
                 description: str, needs_user_help: bool = False, 
                 is_subjective: bool = False):
        self.character_id = character_id
        self.character_name = character_name
        self.event_type = event_type
        self.description = description
        self.needs_user_help = needs_user_help
        self.is_subjective = is_subjective

class MemorySystem:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.short_term_memory_limit = 50
        self.long_term_memory_limit = 100
        self.segment_size = 10
    
    def add_memory(
        self,
        world_id: int,
        content: str,
        memory_type: str = "general",
        importance: int = 1,
        character_id: int = None,
        segment: int = 1
    ) -> Memory:
        return self.db.create_memory(
            world_id=world_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            character_id=character_id,
            segment=segment
        )
    
    def get_memories(
        self,
        world_id: int,
        memory_type: str = None,
        character_id: int = None,
        limit: int = 20
    ) -> List[Memory]:
        if character_id:
            return self.db.get_memories_by_character(character_id, memory_type, limit)
        else:
            return self.db.get_memories_by_world(world_id, memory_type, limit)
    
    def get_recent_memories(
        self,
        world_id: int,
        hours: int = 24,
        limit: int = 20
    ) -> List[Memory]:
        memories = self.db.get_memories_by_world(world_id, limit=limit * 2)
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_memories = []
        
        for mem in memories:
            try:
                mem_time = datetime.fromisoformat(mem.created_at)
                if mem_time >= cutoff_time:
                    recent_memories.append(mem)
                if len(recent_memories) >= limit:
                    break
            except (ValueError, TypeError):
                continue
        
        return recent_memories
    
    def get_important_memories(
        self,
        world_id: int,
        min_importance: int = 3,
        limit: int = 20
    ) -> List[Memory]:
        memories = self.db.get_memories_by_world(world_id, limit=limit * 2)
        
        important_memories = []
        for mem in memories:
            if mem.importance >= min_importance:
                important_memories.append(mem)
            if len(important_memories) >= limit:
                break
        
        return important_memories
    
    def get_context_memories(
        self,
        world_id: int,
        character_id: int = None,
        limit: int = 15,
        character_ids: List[int] = None
    ) -> List[Dict[str, str]]:
        return self.get_memories_for_prompt(world_id, limit, character_ids)
    
    def update_memory_importance(self, memory_id: int, importance: int):
        self.db.update_memory(memory_id, importance=importance)
    
    def delete_memory(self, memory_id: int):
        self.db.delete_memory(memory_id)
    
    def extract_and_store_memories(
        self,
        world_id: int,
        chat_messages: List[Dict[str, str]],
        character_id: int = None,
        segment: int = 1
    ) -> List[Memory]:
        if not chat_messages:
            return []
        
        from api import DeepSeekClient
        
        config = self.db.get_api_config()
        if not config or not config.api1_key:
            return []
        
        world = self.db.get_world(world_id)
        if not world:
            return []
        
        try:
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()
                should_close_loop = False
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                should_close_loop = True
            
            deepseek_client = DeepSeekClient(
                config.api1_key,
                "https://api.deepseek.com/v1"
            )
            
            try:
                if should_close_loop:
                    memories_data = loop.run_until_complete(
                        deepseek_client.extract_memory(
                            world_context=world.background or "",
                            chat_messages=chat_messages,
                            model=config.deepseek_model or "deepseek-chat"
                        )
                    )
                    deepseek_client.close_sync()
                else:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(
                                deepseek_client.extract_memory(
                                    world_context=world.background or "",
                                    chat_messages=chat_messages,
                                    model=config.deepseek_model or "deepseek-chat"
                                )
                            )
                        )
                        memories_data = future.result()
                        
                        deepseek_client.close_sync()
            finally:
                if should_close_loop:
                    loop.close()
            
            stored_memories = []
            for mem_data in memories_data:
                if 'content' in mem_data and mem_data['content']:
                    memory = self.add_memory(
                        world_id=world_id,
                        content=mem_data['content'],
                        memory_type="auto_extracted",
                        importance=mem_data.get('importance', 1),
                        character_id=character_id,
                        segment=segment
                    )
                    stored_memories.append(memory)
            
            return stored_memories
            
        except Exception as e:
            print(f"提取和存储记忆时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def format_memories_for_prompt(self, memories: List[Dict[str, str]]) -> str:
        if not memories:
            return "无相关记忆"
        
        formatted = []
        for i, mem in enumerate(memories, 1):
            importance_str = "⭐" * min(mem.get('importance', 1), 5)
            formatted.append(f"{i}. {mem['content']} {importance_str}")
        
        return "\n".join(formatted)
    
    def cleanup_old_memories(self, world_id: int, days: int = 30):
        memories = self.db.get_memories_by_world(world_id, limit=1000)
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for mem in memories:
            try:
                mem_time = datetime.fromisoformat(mem.created_at)
                if mem_time < cutoff_time and mem.importance < 3:
                    self.db.delete_memory(mem.id)
            except (ValueError, TypeError):
                continue
    
    def calculate_segment(self, user_message_count: int) -> int:
        return (user_message_count // 7) + 1
    
    def get_memories_for_prompt(self, world_id: int, limit: int = 15, character_ids: List[int] = None) -> List[Dict[str, str]]:
        all_memories = []
        seen_content = set()
        
        max_segment = self.db.get_max_segment(world_id)
        
        for segment in range(max_segment, 0, -1):
            segment_memories = self.db.get_memories_by_segment(world_id, segment)
            
            for mem in segment_memories:
                if character_ids and mem.character_id and mem.character_id not in character_ids:
                    continue
                
                if mem.content not in seen_content:
                    all_memories.append({
                        'content': mem.content,
                        'importance': mem.importance,
                        'type': mem.memory_type,
                        'segment': mem.segment
                    })
                    seen_content.add(mem.content)
            
            if len(all_memories) >= limit:
                break
        
        all_memories.sort(key=lambda x: x['importance'], reverse=True)
        
        return all_memories[:limit]
    
    def add_timeline_event_memory(
        self,
        world_id: int,
        event: TimelineEvent,
        current_date: str,
        current_time: str
    ) -> Optional[Memory]:
        content = f"{current_date} {current_time} - {event.character_name}：{event.description}"
        
        importance = 2
        if event.needs_user_help:
            importance = 4
        elif event.event_type in ['冒险', '情感']:
            importance = 3
        
        return self.add_memory(
            world_id=world_id,
            content=content,
            memory_type="timeline_event",
            importance=importance,
            character_id=event.character_id
        )
    
    def add_observed_event_memory(
        self,
        world_id: int,
        observer_character_id: int,
        event: TimelineEvent,
        current_date: str,
        current_time: str
    ) -> Optional[Memory]:
        content = f"{current_date} {current_time} - 观察到{event.character_name}：{event.description}"
        
        importance = 2
        if event.needs_user_help:
            importance = 3
        
        return self.add_memory(
            world_id=world_id,
            content=content,
            memory_type="observed_event",
            importance=importance,
            character_id=observer_character_id
        )
    
    def add_communication_request_memory(
        self,
        world_id: int,
        character_id: int,
        event_type: str,
        current_date: str,
        current_time: str
    ) -> Optional[Memory]:
        content = f"{current_date} {current_time} - 申请通讯 ({event_type})"
        
        return self.add_memory(
            world_id=world_id,
            content=content,
            memory_type="communication_request",
            importance=3,
            character_id=character_id
        )
    
    async def extract_character_memories_async(
        self,
        world_id: int,
        chat_messages: List[Dict[str, str]],
        character_names: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        异步提取角色记忆
        
        参数:
            world_id: 世界ID
            chat_messages: 对话消息列表
            character_names: 需要提取记忆的角色名称列表
        
        返回:
            Dict[str, List[Dict]]: 键为角色名，值为该角色的记忆列表
        """
        from api import DeepSeekClient
        
        config = self.db.get_api_config()
        if not config or not config.api2_key:
            return {}
        
        world = self.db.get_world(world_id)
        if not world:
            return {}
        
        try:
            api2_client = DeepSeekClient(config.api2_key, "https://api.deepseek.com/v1")
            
            result = await api2_client.extract_character_memories(
                world_context=world.background or "",
                chat_messages=chat_messages,
                character_names=character_names,
                model=config.api2_model or "deepseek-chat"
            )
            
            api2_client.close_sync()
            
            return result
        except Exception as e:
            print(f"异步提取角色记忆时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    async def consolidate_memories_async(
        self,
        world_id: int,
        character_id: int = None,
        short_term_limit: int = 20
    ) -> Dict[str, Any]:
        """
        异步提炼记忆
        
        参数:
            world_id: 世界ID
            character_id: 角色ID（可选）
            short_term_limit: 短期记忆数量阈值
        
        返回:
            Dict: 包含提炼结果
        """
        from api import DeepSeekClient
        
        config = self.db.get_api_config()
        if not config or not config.api2_key:
            return {
                'consolidated_memories': [],
                'short_term_ids_to_delete': []
            }
        
        world = self.db.get_world(world_id)
        if not world:
            return {
                'consolidated_memories': [],
                'short_term_ids_to_delete': []
            }
        
        try:
            short_term_memories = self.db.get_short_term_memories(world_id, character_id, limit=short_term_limit)
            long_term_memories = self.db.get_long_term_memories(world_id, character_id, limit=10)
            
            if len(short_term_memories) < short_term_limit:
                return {
                    'consolidated_memories': [],
                    'short_term_ids_to_delete': []
                }
            
            short_term_data = [
                {
                    'id': mem.id,
                    'content': mem.content,
                    'importance': mem.importance
                }
                for mem in short_term_memories
            ]
            
            long_term_data = [
                {
                    'id': mem.id,
                    'content': mem.content,
                    'importance': mem.importance
                }
                for mem in long_term_memories
            ]
            
            character = self.db.get_character(character_id) if character_id else None
            character_name = character.name if character else None
            
            api2_client = DeepSeekClient(config.api2_key, "https://api.deepseek.com/v1")
            
            result = await api2_client.consolidate_memories(
                world_context=world.background or "",
                short_term_memories=short_term_data,
                long_term_memories=long_term_data,
                character_name=character_name,
                model=config.api2_model or "deepseek-chat"
            )
            
            api2_client.close_sync()
            
            return result
        except Exception as e:
            print(f"异步提炼记忆时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {
                'consolidated_memories': [],
                'short_term_ids_to_delete': []
            }
    
    def save_short_term_memories(
        self,
        world_id: int,
        character_memories: Dict[str, List[Dict[str, Any]]],
        source_message_ids: List[int] = None
    ) -> List[int]:
        """
        保存短期记忆
        
        参数:
            world_id: 世界ID
            character_memories: 角色记忆字典 {角色名: [记忆列表]}
            source_message_ids: 来源消息ID列表
        
        返回:
            List[int]: 保存的短期记忆ID列表
        """
        saved_ids = []
        source_ids_str = json.dumps(source_message_ids) if source_message_ids else None
        
        for character_name, memories in character_memories.items():
            character = self.db.get_character_by_name(world_id, character_name)
            if not character:
                continue
            
            for mem_data in memories:
                memory = self.db.create_short_term_memory(
                    world_id=world_id,
                    content=mem_data.get('content', ''),
                    importance=mem_data.get('importance', 1),
                    character_id=character.id,
                    source_message_ids=source_ids_str
                )
                saved_ids.append(memory.id)
        
        return saved_ids
    
    def save_consolidated_memories(
        self,
        world_id: int,
        consolidated_memories: List[Dict[str, Any]],
        character_id: int = None,
        source_short_term_ids: List[int] = None
    ) -> List[int]:
        """
        保存提炼后的长期记忆
        
        参数:
            world_id: 世界ID
            consolidated_memories: 提炼后的记忆列表
            character_id: 角色ID（可选）
            source_short_term_ids: 来源短期记忆ID列表
        
        返回:
            List[int]: 保存的长期记忆ID列表
        """
        saved_ids = []
        source_ids_str = json.dumps(source_short_term_ids) if source_short_term_ids else None
        
        for mem_data in consolidated_memories:
            memory = self.db.create_long_term_memory(
                world_id=world_id,
                content=mem_data.get('content', ''),
                importance=mem_data.get('importance', 1),
                character_id=character_id,
                source_short_term_ids=source_ids_str
            )
            saved_ids.append(memory.id)
        
        return saved_ids
    
    def get_all_memories_for_prompt(
        self,
        world_id: int,
        character_id: int = None,
        limit: int = 15
    ) -> List[Dict[str, str]]:
        """
        获取所有记忆（短期+长期）用于提示
        
        参数:
            world_id: 世界ID
            character_id: 角色ID（可选）
            limit: 记忆数量限制
        
        返回:
            List[Dict]: 记忆列表
        """
        all_memories = []
        
        short_term_memories = self.db.get_short_term_memories(world_id, character_id, limit=limit)
        for mem in short_term_memories:
            all_memories.append({
                'content': mem.content,
                'importance': mem.importance,
                'type': 'short_term',
                'created_at': mem.created_at
            })
        
        remaining_limit = limit - len(all_memories)
        if remaining_limit > 0:
            long_term_memories = self.db.get_long_term_memories(world_id, character_id, limit=remaining_limit)
            for mem in long_term_memories:
                all_memories.append({
                    'content': mem.content,
                    'importance': mem.importance,
                    'type': 'long_term',
                    'created_at': mem.created_at
                })
        
        all_memories.sort(key=lambda x: x['importance'], reverse=True)
        
        return all_memories[:limit]
