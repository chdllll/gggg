from typing import List, Dict, Optional, Any
import asyncio
from datetime import datetime
from database import DatabaseManager
from api import DeepSeekClient
from core.background_selector import BackgroundSelector
from core.time_calculator import TimeCalculator
from core.remote_event_manager import RemoteEventManager
from core.script_manager import ScriptManager
from core.memory_manager import MemoryManager, ShortTermMemory, LongTermMemory
from core.event_extractor import EventExtractor
from core.long_term_memory_summarizer import LongTermMemorySummarizer

class DialogueManager:
    def __init__(
        self,
        deepseek_client: DeepSeekClient,
        db_manager: DatabaseManager,
        background_selector: BackgroundSelector,
        api1_client: DeepSeekClient = None,
        api2_client: DeepSeekClient = None,
        remote_event_manager: RemoteEventManager = None
    ):
        self.deepseek_client = deepseek_client
        self.api1_client = api1_client
        self.api2_client = api2_client
        self.db = db_manager
        self.bg_selector = background_selector
        self.time_calculator = TimeCalculator()
        self.remote_event_manager = remote_event_manager
        self.memory_status_callback = None
        self.script_manager = ScriptManager(db_manager)
        self.memory_manager = MemoryManager(db_manager)
        self.event_extractor = EventExtractor()
        self.long_term_summarizer = LongTermMemorySummarizer(api2_client) if api2_client else None
        
        self.chat_messages_cache = {}
        self.cache_ttl = 30
        self.max_cache_size = 100
        self._cache_cleanup_task = None
        self._start_cache_cleanup_task()
        self._async_tasks = {}
        self._task_counter = 0
    
    def set_memory_status_callback(self, callback):
        self.memory_status_callback = callback
    
    def _start_cache_cleanup_task(self):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._cache_cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())
        except RuntimeError:
            pass
    
    async def _periodic_cache_cleanup(self):
        while True:
            try:
                await asyncio.sleep(60)
                self._cleanup_expired_cache()
            except Exception as e:
                print(f"缓存清理任务错误: {e}")
    
    def _cleanup_expired_cache(self):
        import time
        current_time = time.time()
        keys_to_remove = []
        
        for key, (data, timestamp) in self.chat_messages_cache.items():
            if current_time - timestamp > self.cache_ttl:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.chat_messages_cache[key]
        
        if len(self.chat_messages_cache) > self.max_cache_size:
            sorted_items = sorted(
                self.chat_messages_cache.items(),
                key=lambda x: x[1][1]
            )
            items_to_remove = len(self.chat_messages_cache) - self.max_cache_size
            for key, _ in sorted_items[:items_to_remove]:
                del self.chat_messages_cache[key]
    
    def _get_chat_messages_with_cache(
        self,
        session_id: int,
        limit: int = 100,
        location: str = None,
        after_time_separator: bool = True
    ) -> List:
        import time
        
        cache_key = f"{session_id}_{location}_{after_time_separator}"
        
        if cache_key in self.chat_messages_cache:
            cached_data, timestamp = self.chat_messages_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
        
        messages = self.db.get_chat_messages_by_session(
            session_id,
            limit=limit,
            location=location,
            after_time_separator=after_time_separator
        )
        
        self.chat_messages_cache[cache_key] = (messages, time.time())
        
        if len(self.chat_messages_cache) > self.max_cache_size:
            self._cleanup_expired_cache()
        
        return messages
    
    def _invalidate_chat_messages_cache(
        self,
        session_id: int = None,
        location: str = None
    ):
        if session_id is None:
            self.chat_messages_cache.clear()
        else:
            keys_to_remove = []
            for key in self.chat_messages_cache:
                if key.startswith(f"{session_id}_"):
                    if location is None or f"_{location}_" in key:
                        keys_to_remove.append(key)
            for key in keys_to_remove:
                del self.chat_messages_cache[key]
    
    async def cleanup(self):
        if self._cache_cleanup_task:
            self._cache_cleanup_task.cancel()
            try:
                await self._cache_cleanup_task
            except asyncio.CancelledError:
                pass
        self.chat_messages_cache.clear()
        
        for task_id, task in self._async_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._async_tasks.clear()
    
    def _create_tracked_task(self, coro, task_name: str = "unknown"):
        task = asyncio.create_task(coro)
        self._task_counter += 1
        task_id = self._task_counter
        self._async_tasks[task_id] = task
        
        async def task_wrapper():
            try:
                await task
            except Exception as e:
                print(f"异步任务 [{task_name}] 执行失败: {e}")
                import traceback
                traceback.print_exc()
            finally:
                if task_id in self._async_tasks:
                    del self._async_tasks[task_id]
        
        asyncio.create_task(task_wrapper())
        return task
    
    def _format_time_for_api(self, date_str: str, time_str: str) -> tuple:
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            year = dt.year
            month = dt.month
            day = dt.day
            hour = dt.hour
            return f"{year}年{month}月{day}日", f"{hour}时"
        except Exception as e:
            print(f"时间格式转换失败: {e}, 使用默认值")
            return "2024年1月1日", "8时"
    
    def select_character_by_activity(self, characters: List, selected_character: str = None) -> Optional:
        if selected_character:
            return next((c for c in characters if c.name == selected_character), None)
        
        if not characters:
            return None
        
        total_score = sum(c.activity_score for c in characters)
        if total_score == 0:
            return characters[0]
        
        import random
        rand = random.randint(1, total_score)
        current = 0
        for char in characters:
            current += char.activity_score
            if rand <= current:
                return char
        
        return characters[-1]
    
    def update_activity_after_speech(self, world_id: int, spoken_character_id: int, all_characters: List):
        self.db.reset_activity_score(spoken_character_id)
        
        for char in all_characters:
            if char.id != spoken_character_id:
                self.db.update_activity_score(char.id, 10)
    
    def _get_gender_filtered_health(self, character) -> Dict[str, str]:
        health = {
            'mouth': character.health_mouth,
            'anus': character.health_anus,
            'buttocks': character.health_buttocks
        }
        
        if character.gender and character.gender.lower() == 'male':
            health.update({
                'penis': character.health_penis,
                'testicles': character.health_testicles
            })
        else:
            health.update({
                'left_breast': character.health_left_breast,
                'right_breast': character.health_right_breast,
                'vagina': character.health_vagina
            })
        
        return health
    
    def _select_chat_history(
        self,
        all_messages: List,
        character_name: str = None
    ) -> List:
        selected_messages = []
        selected_ids = set()
        
        if len(all_messages) == 0:
            return selected_messages
        
        # 1. 最新六条消息（从最新往回数六条）
        recent_count = min(6, len(all_messages))
        for i in range(recent_count):
            msg = all_messages[len(all_messages) - 1 - i]
            selected_messages.append(msg)
            selected_ids.add(msg.id)
        
        # 如果消息少于7条，直接返回
        if len(all_messages) < 7:
            return selected_messages
        
        # 2. 她自己说的四条消息（从六次对话前开始往回数，找到四条该角色的消息）
        if character_name:
            character_messages_count = 0
            for i in range(len(all_messages) - 7, -1, -1):
                msg = all_messages[i]
                if msg.id in selected_ids:
                    continue
                if msg.message_type == "character" and msg.character_name == character_name:
                    selected_messages.append(msg)
                    selected_ids.add(msg.id)
                    character_messages_count += 1
                    if character_messages_count >= 4:
                        break
        
        # 3. 四条用户说的消息（从六次对话前开始往回数，找到四条用户的消息）
        user_messages_count = 0
        for i in range(len(all_messages) - 7, -1, -1):
            msg = all_messages[i]
            if msg.id in selected_ids:
                continue
            if msg.message_type == "user":
                selected_messages.append(msg)
                selected_ids.add(msg.id)
                user_messages_count += 1
                if user_messages_count >= 4:
                    break
        
        # 按原始顺序排序（从旧到新）
        selected_messages.sort(key=lambda x: x.id)
        
        return selected_messages
    
    def _parse_communication_markers(self, user_message: str) -> tuple:
        """
        解析用户消息中的通讯标记
        返回: (communication_characters, end_communication_characters)
        - communication_characters: 通过【角色名】标记需要通讯的角色列表
        - end_communication_characters: 通过【-角色名】标记结束通讯的角色列表
        """
        import re
        
        # 先匹配【-角色名】模式（结束通讯）
        end_pattern = r'【-([^】]+)】'
        # 匹配【角色名】模式（开始通讯）
        start_pattern = r'【([^】]+)】'
        
        communication_characters = []
        end_communication_characters = []
        
        # 查找所有结束通讯的标记
        end_matches = re.findall(end_pattern, user_message)
        for match in end_matches:
            end_communication_characters.append(match.strip())
        
        # 查找所有开始通讯的标记
        start_matches = re.findall(start_pattern, user_message)
        for match in start_matches:
            # 排除以-开头的（这些是结束通讯标记）
            if not match.startswith('-'):
                communication_characters.append(match.strip())
        
        return communication_characters, end_communication_characters
    
    def _filter_user_message(self, user_message: str) -> str:
        """
        过滤用户消息，移除通讯标记
        """
        import re
        
        # 移除【角色名】和【-角色名】标记
        filtered_message = re.sub(r'【-?[^】]+】', '', user_message)
        return filtered_message.strip()
    
    async def _trigger_advance_day_mode(
        self,
        world_id: int,
        session_id: int,
        character_data: List[Dict[str, Any]],
        chat_history_formatted: List[Dict[str, str]],
        location: str = None
    ):
        """
        触发API2过一天模式
        """
        print(f"API2过一天模式触发")
        
        world = self.db.get_world(world_id)
        if not world:
            print("世界不存在，无法触发API2过一天模式")
            return
        
        api_config = self.db.get_api_config()
        if not api_config or not api_config.api2_key:
            print("未配置API2，跳过过一天模式")
            return
        
        api2_client = DeepSeekClient(api_key=api_config.api2_key)
        
        try:
            api2_model = api_config.api2_model if api_config.api2_model else "deepseek-chat"
            
            all_chat_messages = self._get_chat_messages_with_cache(session_id, limit=100, location=location, after_time_separator=True)
            
            user_messages = [msg for msg in all_chat_messages if msg.message_type == 'user']
            last_7_user_messages = user_messages[-7:] if len(user_messages) >= 7 else user_messages
            
            if not last_7_user_messages:
                print("没有用户消息，跳过记忆存储")
                return
            
            first_user_msg_id = last_7_user_messages[0].id
            last_user_msg_id = last_7_user_messages[-1].id
            
            chat_messages_for_memory = []
            for msg in all_chat_messages:
                if msg.id >= first_user_msg_id:
                    chat_messages_for_memory.append(msg)
            
            chat_history = [
                {
                    'content': msg.content,
                    'message_type': msg.message_type,
                    'character_name': msg.character_name if msg.message_type == 'character' else None
                }
                for msg in chat_messages_for_memory
            ]
            
            print(f"记忆存储：使用最后{len(last_7_user_messages)}条用户消息，共{len(chat_messages_for_memory)}条消息")
            print(f"用户消息范围：第{len(user_messages) - len(last_7_user_messages) + 1}条到第{len(user_messages)}条")
            
            api2_result = await api2_client.advance_day(
                world_context=world.background or "",
                characters=character_data,
                chat_history=chat_history,
                current_date=world.current_date,
                current_time=world.current_time,
                user_location=world.user_location or "",
                model=api2_model
            )
            
            print(f"API2过一天模式完成")
            
            api2_time_advancement_seconds = api2_result.get('time_advancement_seconds', 0)
            if api2_time_advancement_seconds > 0:
                print(f"API2过一天模式检测到时间推进：{api2_time_advancement_seconds}秒")
            
            api2_events = api2_result.get('other_character_events', [])
            if api2_events:
                print(f"API2过一天模式生成了{len(api2_events)}个其他角色事件")
                for event in api2_events:
                    character_name = event.get('character_name', '')
                    event_type = event.get('event_type', '')
                    description = event.get('description', '')
                    needs_user_help = event.get('needs_user_help', False)
                    print(f"  - {character_name} [{event_type}]: {description}")
                    if needs_user_help:
                        print(f"    需要用户帮助")
            
        except Exception as e:
            print(f"API2过一天模式执行失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            api2_client.close()
    
    async def _trigger_event_extraction(
        self,
        world_id: int,
        session_id: int,
        character_data: List[Dict[str, Any]],
        chat_history_formatted: List[Dict[str, str]],
        location: str = None
    ):
        """
        触发事件提取和记忆存储
        """
        print(f"事件提取触发")
        
        if self.memory_status_callback:
            self.memory_status_callback("storing")
        
        world = self.db.get_world(world_id)
        if not world:
            print("世界不存在，无法触发事件提取")
            return
        
        all_chat_messages = self._get_chat_messages_with_cache(session_id, limit=100, location=location, after_time_separator=True)
        user_messages = [msg for msg in all_chat_messages if msg.message_type == 'user']
        last_5_user_messages = user_messages[-5:] if len(user_messages) >= 5 else user_messages
        
        if not last_5_user_messages:
            print("没有用户消息，跳过事件提取")
            return
        
        first_user_msg_id = last_5_user_messages[0].id
        last_user_msg_id = last_5_user_messages[-1].id
        
        chat_messages_for_memory = []
        for msg in all_chat_messages:
            if msg.id >= first_user_msg_id:
                chat_messages_for_memory.append(msg)
        
        print(f"事件提取：使用最后{len(last_5_user_messages)}条用户消息，共{len(chat_messages_for_memory)}条消息")
        
        current_location = location if location else (world.user_location or "")
        current_date = world.current_date
        current_time = world.current_time
        
        present_characters = []
        for char in character_data:
            if char.get('location') == current_location:
                present_characters.append(char.get('name'))
        
        print(f"当前位置: {current_location}, 在场角色: {present_characters}")
        
        all_character_dialogues = []
        for msg in chat_messages_for_memory:
            if msg.message_type == 'character':
                all_character_dialogues.append(msg.content)
        
        if not all_character_dialogues:
            print("没有角色对话，跳过事件提取")
            return
        
        print(f"提取所有角色对话，共{len(all_character_dialogues)}条")
        
        events = self.event_extractor.extract_events(
            dialogues=all_character_dialogues,
            location=current_location,
            date=current_date,
            time=current_time,
            present_characters=present_characters
        )
        
        print(f"总共提取了{len(events)}个事件")
        
        for event in events:
            self.memory_manager.add_event(world_id, event)
            print(f"事件: {event.event_type} - {event.event_content} (重要性: {event.importance})")
        
        for char_name in present_characters:
            print(f"为角色 {char_name} 批量添加短期记忆")
            
            short_term_data = self.memory_manager.get_short_term_memories(world_id, char_name)
            current_counter = short_term_data.get('counter', 0)
            
            if current_counter >= 5:
                print(f"  角色 {char_name} 的短期记忆已满，跳过添加")
                continue
            
            memories_to_add = []
            for event in events:
                if current_counter >= 5:
                    break
                
                short_term_memory = ShortTermMemory(
                    content=event.event_content,
                    importance=event.importance,
                    memory_type=event.event_type,
                    source_event=event.event_content
                )
                memories_to_add.append(short_term_memory)
                current_counter += 1
            
            if memories_to_add:
                counter = self.memory_manager.add_short_term_memories_batch(world_id, char_name, memories_to_add)
                print(f"  为角色 {char_name} 批量添加了{len(memories_to_add)}条短期记忆, 计数器: {counter}")
                
                if counter >= 5:
                    print(f"  角色 {char_name} 的短期记忆已满，触发长期记忆总结...")
                    await self._trigger_long_term_summarization(world_id, char_name)
        
        if self.memory_status_callback:
            self.memory_status_callback("ready")
        
        await self._trigger_chapter_progression(world_id, session_id, location)
    
    async def _trigger_chapter_progression(self, world_id: int, session_id: int, location: str = None):
        """
        触发章节推进判断
        """
        from core.script_manager import ScriptManager
        script_manager = ScriptManager(self.db)
        
        if not script_manager.is_script_enabled(world_id):
            print("剧本未启用，跳过章节推进判断")
            return
        
        current_chapter = script_manager.get_current_chapter(world_id)
        if not current_chapter:
            print("没有当前篇章，跳过章节推进判断")
            return
        
        if current_chapter['index'] >= current_chapter['total_chapters'] - 1:
            print("已经是最后一个篇章，跳过章节推进判断")
            return
        
        next_chapter = script_manager.get_all_chapters(world_id)[current_chapter['index'] + 1]
        if not next_chapter:
            print("没有下一个篇章，跳过章节推进判断")
            return
        
        print(f"章节推进判断: 当前篇章 {current_chapter['title']}, 下一个篇章 {next_chapter['title']}")
        
        all_characters = self.db.get_characters_by_world(world_id)
        all_short_term_memories = []
        
        for char in all_characters:
            short_term_data = self.memory_manager.get_short_term_memories(world_id, char.name)
            short_term_memories = short_term_data.get('memories', [])
            all_short_term_memories.extend(short_term_memories)
        
        if not all_short_term_memories:
            print("没有短期记忆，跳过章节推进判断")
            return
        
        all_short_term_memories.sort(key=lambda x: x.importance, reverse=True)
        short_term_memories = all_short_term_memories[:3]
        
        print(f"使用最近的 {len(short_term_memories)} 条短期记忆进行章节推进判断")
        
        api_config = self.db.get_api_config()
        if not api_config or not api_config.api2_key:
            print("未配置API2，无法进行章节推进判断")
            return
        
        from api.deepseek_client import DeepSeekClient
        deepseek_client = DeepSeekClient(api_config.api2_key)
        
        try:
            memories_text = "\n".join([f"- {mem.content}" for mem in short_term_memories])
            
            prompt = f"""你是一个剧本推进判断助手。请根据最近的短期记忆和当前篇章、下一个篇章的内容，判断是否需要进入下一个篇章。

当前篇章：
标题：{current_chapter['title']}
描述：{current_chapter['description']}

下一个篇章：
标题：{next_chapter['title']}
描述：{next_chapter['description']}

最近的短期记忆（共{len(short_term_memories)}条）：
{memories_text}

请判断是否需要进入下一个篇章。如果当前篇章的主要目标已经完成，或者故事情节已经自然过渡到下一个篇章，则返回True；否则返回False。

请只返回True或False，不要返回其他内容。"""
            
            api2_model = api_config.api2_model if api_config.api2_model else "deepseek-chat"
            
            response = await deepseek_client.chat_completion(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model=api2_model,
                max_tokens=10
            )
            
            if response and response.get('choices'):
                content = response['choices'][0]['message']['content'].strip()
                print(f"API2返回: {content}")
                
                if content.lower() == 'true':
                    print(f"API2判断需要进入下一个篇章")
                    
                    if script_manager.advance_to_next_chapter(world_id):
                        new_chapter = script_manager.get_current_chapter(world_id)
                        if new_chapter:
                            print(f"已进入下一个篇章: {new_chapter['title']}")
                            
                            current_location = location if location else (world.user_location or "")
                            
                            self.db.create_chat_message(
                                session_id=session_id,
                                content=f"进入下一个篇章: {new_chapter['title']}",
                                message_type='chapter_change',
                                current_date=world.current_date,
                                current_time=world.current_time,
                                location=current_location
                            )
                            
                            self._invalidate_chat_messages_cache(session_id, location)
                            
                            timeline_event = {
                                'type': 'chapter_change',
                                'title': new_chapter['title'],
                                'description': new_chapter.get('description', ''),
                                'index': new_chapter['index'],
                                'total': new_chapter['total_chapters']
                            }
                            
                            return timeline_event
                        else:
                            print("所有篇章已完成")
                    else:
                        print("进入下一个篇章失败")
                else:
                    print(f"API2判断不需要进入下一个篇章")
        except Exception as e:
            print(f"章节推进判断失败: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    async def _trigger_long_term_summarization(self, world_id: int, character_name: str):
        """
        触发长期记忆总结
        """
        if not self.long_term_summarizer:
            print("未配置API2，无法总结长期记忆")
            return
        
        short_term_data = self.memory_manager.get_short_term_memories(world_id, character_name)
        short_term_memories = short_term_data.get('memories', [])
        counter = short_term_data.get('counter', 0)
        
        if not short_term_memories:
            print(f"角色 {character_name} 没有短期记忆，跳过长期记忆总结")
            return
        
        new_memories = short_term_memories[-counter:] if counter > 0 else []
        
        if not new_memories:
            print(f"角色 {character_name} 没有新的短期记忆，跳过长期记忆总结")
            return
        
        print(f"角色 {character_name} 有 {len(new_memories)} 条新的短期记忆需要总结")
        
        character = None
        all_characters = self.db.get_characters_by_world(world_id)
        for char in all_characters:
            if char.name == character_name:
                character = char
                break
        
        if not character:
            print(f"未找到角色 {character_name}")
            return
        
        world = self.db.get_world(world_id)
        
        character_relationships = self.db.get_character_relationships(world_id, source_character_id=character.id)
        
        old_long_term_memories = self.memory_manager.get_long_term_memories(world_id, character_name)
        
        try:
            updated_long_term_memories = await self.long_term_summarizer.summarize_to_long_term(
                character_name=character_name,
                character_background=character.background or "",
                character_description=character.description or "",
                character_relationships=[
                    {
                        'target_character': rel.target_character_id,
                        'description': rel.description,
                        'importance': rel.importance
                    }
                    for rel in character_relationships
                ],
                short_term_memories=new_memories,
                old_long_term_memories=[asdict(mem) for mem in old_long_term_memories],
                world_context=world.background or "",
                user_name=world.user_name
            )
            
            print(f"为角色 {character_name} 更新了{len(updated_long_term_memories)}条长期记忆")
            
            self.memory_manager.replace_long_term_memories(world_id, character_name, updated_long_term_memories)
            print(f"已替换角色 {character_name} 的长期记忆")
            
            self.memory_manager.reset_short_term_counter(world_id, character_name)
            print(f"已重置角色 {character_name} 的短期记忆计数器")
            
        except Exception as e:
            print(f"长期记忆总结失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def process_user_message(
        self,
        world_id: int,
        session_id: int,
        user_message: str,
        selected_character: str = None,
        location: str = None
    ) -> tuple:
        import time
        start_time = time.time()
        
        print(f"处理用户消息: {user_message}")
        world = self.db.get_world(world_id)
        if not world:
            raise Exception("世界不存在")
        
        print(f"world.user_message_count 类型: {type(world.user_message_count)}, 值: {world.user_message_count}")
        
        # 保存用户消息到数据库
        db_save_start = time.time()
        self.db.create_chat_message(
            session_id=session_id,
            content=user_message,
            message_type='user',
            current_date=world.current_date,
            current_time=world.current_time,
            location=location
        )
        db_save_time = time.time() - db_save_start
        print(f"保存用户消息耗时: {db_save_time:.3f}秒")
        
        self._invalidate_chat_messages_cache(session_id, location)
        
        # 解析通讯标记
        communication_characters, end_communication_characters = self._parse_communication_markers(user_message)
        filtered_user_message = self._filter_user_message(user_message)
        
        if communication_characters:
            print(f"检测到通讯标记，角色: {communication_characters}")
        if end_communication_characters:
            print(f"检测到结束通讯标记，角色: {end_communication_characters}")
        
        all_characters = self.db.get_characters_by_world(world_id)
        if not all_characters:
            raise Exception("世界中没有角色")
        
        # 根据当前视角位置选择角色
        if location:
            characters = [c for c in all_characters if c.location == location]
            print(f"当前视角位置: {location}, 该位置的角色: {[char.name for char in characters]}")
        else:
            user_location = world.user_location if world and world.user_location else None
            is_user_on_the_way = self.db.is_user_on_the_way(world_id, world.current_date, world.current_time)
            
            if is_user_on_the_way:
                print("用户正在路上，角色无法与用户面对面交流")
                characters = []
            elif user_location:
                characters = [c for c in all_characters if c.location == user_location]
                print(f"用户位置: {user_location}, 该位置的角色: {[char.name for char in characters]}")
            else:
                characters = all_characters
                print("未指定位置，将使用所有角色")
        
        # 记录通过通讯工具参与的角色
        communication_character_names = set()
        
        # 将通讯角色临时添加到角色列表
        if communication_characters:
            for comm_char_name in communication_characters:
                comm_char = next((c for c in all_characters if c.name == comm_char_name), None)
                if comm_char:
                    if comm_char not in characters:
                        print(f"添加通讯角色 {comm_char.name} 到角色列表（位置: {comm_char.location}）")
                        characters.append(comm_char)
                        communication_character_names.add(comm_char.name)
                    else:
                        print(f"角色 {comm_char.name} 已经在用户位置，无需通过通讯")
                        communication_character_names.add(comm_char.name)
        
        if not characters:
            print("没有可用的角色（用户在路上且未使用通讯工具）")
            return [], [], []
        
        # 批量查询所有角色的背景图，避免重复查询
        bg_query_start = time.time()
        all_bg_images = self.db.get_all_background_images(world_id)
        bg_images_map = {}
        for bg in all_bg_images:
            if bg.character_id not in bg_images_map:
                bg_images_map[bg.character_id] = []
            bg_images_map[bg.character_id].append(bg)
        bg_query_time = time.time() - bg_query_start
        print(f"批量查询背景图耗时: {bg_query_time:.3f}秒")
        
        all_chat_history = self._get_chat_messages_with_cache(session_id, limit=100, location=location, after_time_separator=True)
        
        selected_character = self.select_character_by_activity(characters, selected_character)
        if not selected_character:
            print("没有可用的角色")
            return [], [], []
        
        print(f"根据活跃度选择角色: {selected_character.name} (活跃度: {selected_character.activity_score})")
        
        chat_history = self._select_chat_history(all_chat_history, selected_character.name)
        print(f"获取到{len(all_chat_history)}条历史消息，选择了{len(chat_history)}条")
        for msg in chat_history:
            print(f"  - {msg.message_type}: {msg.content[:50]}...")
        
        character_ids = [selected_character.id]
        
        short_term_data = self.memory_manager.get_short_term_memories(world_id, selected_character.name)
        short_term_memories = short_term_data.get('memories', [])
        
        long_term_memories = self.memory_manager.get_long_term_memories(world_id, selected_character.name)
        
        memories = []
        for mem in short_term_memories:
            memories.append({
                'content': mem.content,
                'importance': mem.importance,
                'memory_type': mem.memory_type
            })
        for mem in long_term_memories:
            memories.append({
                'content': mem.content,
                'importance': mem.importance,
                'memory_type': mem.memory_type
            })
        
        memories = sorted(memories, key=lambda x: x['importance'], reverse=True)[:10]
        
        selected_char_data = None
        for char in characters:
            if char.id == selected_character.id:
                bg_images = bg_images_map.get(char.id, [])
                selected_char_data = {
                    'id': char.id,
                    'name': char.name,
                    'background': char.background,
                    'description': char.description,
                    'avatar_path': char.avatar_path,
                    'location': char.location,
                    'gender': char.gender,
                    'health': self._get_gender_filtered_health(char),
                    'background_images': [
                        {
                            'id': bg.id,
                            'description': bg.description,
                            'tags': bg.tags
                        }
                        for bg in bg_images
                    ]
                }
                break
        
        if not selected_char_data:
            print("无法找到选中的角色数据")
            return []
        
        character_data = [selected_char_data]
        
        all_characters_data = []
        for char in characters:
            bg_images = bg_images_map.get(char.id, [])
            char_data = {
                'id': char.id,
                'name': char.name,
                'background': char.background,
                'description': char.description,
                'location': char.location,
                'gender': char.gender,
                'health': self._get_gender_filtered_health(char),
                'background_images': [
                    {
                        'id': bg.id,
                        'description': bg.description,
                        'tags': bg.tags
                    }
                    for bg in bg_images
                ]
            }
            all_characters_data.append(char_data)
        
        print(f"API1: 传输给API1的角色列表（同一位置）: {[char['name'] for char in all_characters_data]}")
        
        character_relationships = self.db.get_character_relationships(world_id)
        relationships_data = []
        for rel in character_relationships:
            source_char = next((c for c in all_characters if c.id == rel.source_character_id), None)
            target_char = next((c for c in all_characters if c.id == rel.target_character_id), None)
            if source_char and target_char:
                relationships_data.append({
                    'source_character_id': rel.source_character_id,
                    'source_character_name': source_char.name,
                    'target_character_id': rel.target_character_id,
                    'target_character_name': target_char.name,
                    'relationship_type': rel.relationship_type,
                    'description': rel.description,
                    'importance': rel.importance
                })
        
        config = self.db.get_api_config()
        model = config.api1_model if config and config.api1_model else "deepseek-chat"
        
        user_health = {
            'mouth': world.user_health_mouth,
            'anus': world.user_health_anus,
            'buttocks': world.user_health_buttocks,
            'penis': world.user_health_penis,
            'testicles': world.user_health_testicles,
            'left_breast': world.user_health_left_breast,
            'right_breast': world.user_health_right_breast,
            'vagina': world.user_health_vagina
        }
        
        chat_history_formatted = [
            {
                'message_type': msg.message_type,
                'content': msg.content,
                'action': msg.action,
                'character_name': msg.character_name
            }
            for msg in chat_history
        ]
        
        # 获取当前篇章信息
        current_chapter = None
        if world.script_enabled:
            try:
                current_chapter = self.script_manager.get_current_chapter(world_id)
                if current_chapter:
                    print(f"当前篇章: {current_chapter['title']} (索引: {current_chapter['index']}/{current_chapter['total_chapters']})")
            except Exception as e:
                print(f"获取当前篇章信息时发生错误: {e}")
        
        responses = []
        
        if self.api1_client and self.api2_client:
            api1_key = config.api1_key if config and config.api1_key else None
            
            if api1_key:
                print("使用API1处理")
                
                api1_model = config.api1_model if config and config.api1_model else model
                
                api1_client = DeepSeekClient(api1_key)
                
                try:
                    print("使用API1生成对话")
                    
                    api_date, api_time = self._format_time_for_api(world.current_date, world.current_time)
                    
                    responses = await api1_client.generate_dialogue_simple(
                        world_context=world.background or "",
                        characters=all_characters_data,
                        relationships=relationships_data,
                        chat_history=chat_history_formatted,
                        user_message=filtered_user_message,
                        current_date=api_date,
                        current_time=api_time,
                        user_health=user_health,
                        memories=memories,
                        user_name=world.user_name,
                        model=api1_model
                    )
                    
                    print(f"API1完成，获得{len(responses)}个响应")
                        
                except Exception as e:
                    print(f"API1处理失败: {e}")
                    responses = []
                finally:
                    api1_client.close()
            else:
                print("API1未配置，使用默认API处理")
                
                api_date, api_time = self._format_time_for_api(world.current_date, world.current_time)
                
                responses = await self.deepseek_client.generate_dialogue(
                    world_context=world.background or "",
                    characters=[selected_char_data],
                    chat_history=chat_history_formatted,
                    user_message=filtered_user_message,
                    current_date=api_date,
                    current_time=api_time,
                    user_health=user_health,
                    memories=memories,
                    current_chapter=current_chapter,
                    user_name=world.user_name,
                    model=model
                )
        else:
            print("未配置双API，使用单API处理")
            
            api_date, api_time = self._format_time_for_api(world.current_date, world.current_time)
            
            responses = await self.deepseek_client.generate_dialogue(
                world_context=world.background or "",
                characters=[selected_char_data],
                chat_history=chat_history_formatted,
                user_message=filtered_user_message,
                current_date=api_date,
                current_time=api_time,
                user_health=user_health,
                memories=memories,
                current_chapter=current_chapter,
                user_name=world.user_name,
                model=model
            )
        
        result_responses = []
        time_advancement_seconds = 0
        
        print(f"DialogueManager: 收到{len(responses)}条API响应")
        
        # 测量API响应处理时间
        process_response_start = time.time()
        
        for response in responses:
            character_name = response.get('character_name')
            print(f"DialogueManager: 处理响应 - 角色名称: {character_name}")
            
            character = next((c for c in all_characters if c.name == response['character_name']), None)
            if not character:
                print(f"DialogueManager: 错误 - 角色 '{character_name}' 不在所有角色列表中")
                continue
            
            if response.get('time_advancement_seconds', 0) > 0:
                time_advancement_seconds = max(time_advancement_seconds, response.get('time_advancement_seconds', 0))
            
            background_image_id = None
            background_image_index = response.get('background_image_index')
            
            print(f"DialogueManager: 角色 {character.name} - API返回的背景图索引: {background_image_index}")
            
            if background_image_index is not None:
                char_bg_images = bg_images_map.get(character.id, [])
                print(f"DialogueManager: 角色 {character.name} - 可用背景图数量: {len(char_bg_images)}")
                
                if 0 <= background_image_index < len(char_bg_images):
                    background_image_id = char_bg_images[background_image_index].id
                    print(f"DialogueManager: 角色 {character.name} - 使用背景图索引{background_image_index}, ID={background_image_id}")
                else:
                    print(f"DialogueManager: 警告 - 角色 {character.name} 的背景图索引{background_image_index}超出范围(0-{len(char_bg_images)-1})")
            else:
                print(f"DialogueManager: 角色 {character.name} - 未指定背景图")
            
            segments = response.get('segments', [])
            
            if character.name in communication_character_names:
                print(f"角色 {character.name} 正在通过通讯工具发言，移除所有动作")
                segments = [seg for seg in segments if seg['type'] == 'speech']
            
            non_thought_segments = [seg for seg in segments if seg.get('type') != 'thought']
            thought_segments = [seg for seg in segments if seg.get('type') == 'thought']
            if thought_segments:
                segments = non_thought_segments + [thought_segments[0]]
            else:
                segments = non_thought_segments + [{'type': 'thought', 'content': '...'}]
            
            import json
            segments_json = json.dumps(segments, ensure_ascii=False)
            content = ' '.join([seg['content'] for seg in segments if seg['type'] == 'speech'])
            action = ' '.join([seg['content'] for seg in segments if seg['type'] == 'action'])
            
            self.db.create_chat_message(
                session_id=session_id,
                character_id=character.id,
                character_name=response['character_name'],
                content=content,
                action=action,
                background_image_id=background_image_id,
                avatar_path=character.avatar_path,
                message_type='character',
                segments=segments_json,
                current_date=world.current_date,
                current_time=world.current_time,
                location=location
            )
            
            self._invalidate_chat_messages_cache(session_id, location)
            
            self.update_activity_after_speech(world_id, character.id, all_characters)
            
            if response.get('health_updates'):
                health_updates = response['health_updates']
                print(f"角色 {character.name} 健康状态更新: {health_updates}")
                
                body_parts = ['mouth', 'anus', 'buttocks', 'penis', 'testicles', 'left_breast', 'right_breast', 'vagina']
                update_params = {}
                
                for part in body_parts:
                    if part in health_updates:
                        part_data = health_updates[part]
                        if isinstance(part_data, dict):
                            update_params[f'health_{part}'] = part_data.get('description')
                            update_params[f'health_{part}_color'] = part_data.get('color', '#28a745')
                        else:
                            update_params[f'health_{part}'] = part_data
                
                if update_params:
                    self.db.update_character(character.id, **update_params)
            
            segments = response.get('segments', [])
            if not segments:
                segments = []
                if response.get('action'):
                    segments.append({'type': 'action', 'content': response['action']})
                if response.get('content'):
                    segments.append({'type': 'speech', 'content': response['content']})
            
            non_thought_segments = [seg for seg in segments if seg.get('type') != 'thought']
            thought_segments = [seg for seg in segments if seg.get('type') == 'thought']
            if thought_segments:
                segments = non_thought_segments + [thought_segments[0]]
            else:
                segments = non_thought_segments + [{'type': 'thought', 'content': '...'}]
            
            result_responses.append({
                'character_id': character.id,
                'character_name': response['character_name'],
                'segments': segments,
                'background_image_id': background_image_id
            })
        
        user_health_update_params = {}
        for response in responses:
            if response.get('user_health_updates'):
                user_health_updates = response['user_health_updates']
                print(f"用户健康状态更新: {user_health_updates}")
                
                body_parts = ['mouth', 'anus', 'buttocks', 'penis', 'testicles', 'left_breast', 'right_breast', 'vagina']
                
                for part in body_parts:
                    if part in user_health_updates:
                        part_data = user_health_updates[part]
                        if isinstance(part_data, dict):
                            user_health_update_params[f'user_health_{part}'] = part_data.get('description')
                            user_health_update_params[f'user_health_{part}_color'] = part_data.get('color', '#28a745')
                        else:
                            user_health_update_params[f'user_health_{part}'] = part_data
        
        if user_health_update_params:
            self.db.update_world(world_id, **user_health_update_params)
        
        timeline_events = []
        
        # 合并所有世界数据更新，避免多次数据库操作
        world_update_params = {}
        
        if time_advancement_seconds > 0:
            current_time_str = f"{world.current_date} {world.current_time}"
            new_time_str = self.time_calculator.add_seconds(current_time_str, time_advancement_seconds)
            
            new_date_part, new_time_part = new_time_str.split(' ')
            world_update_params['current_date'] = new_date_part
            world_update_params['current_time'] = new_time_part
            
            new_total_seconds = world.total_seconds + time_advancement_seconds
            world_update_params['total_seconds'] = new_total_seconds
            
            time_desc = self.time_calculator.get_time_description(time_advancement_seconds)
            print(f"时间已推进{time_desc}：{new_date_part} {new_time_part}")
            print(f"总时间秒数：{new_total_seconds}")
            
            if new_total_seconds % 86400 == 0 and new_total_seconds > 0:
                print(f"检测到度过一天（总秒数{new_total_seconds}），触发API2过一天模式...")
                self._create_tracked_task(
                    self._trigger_advance_day_mode(world_id, session_id, character_data, chat_history_formatted, location),
                    "advance_day_mode"
                )
        
        all_chat_messages = self._get_chat_messages_with_cache(session_id, limit=1000, location=location, after_time_separator=True)
        total_messages = len(all_chat_messages)
        
        new_user_message_count = world.user_message_count + 1
        
        world_update_params['user_message_count'] = new_user_message_count
        
        if new_user_message_count % 5 == 0:
            print(f"已达到用户消息边界（第{new_user_message_count}条用户消息），触发事件提取...")
            self._create_tracked_task(
                self._trigger_event_extraction(world_id, session_id, all_characters_data, chat_history_formatted, location),
                "event_extraction"
            )
        
        # 一次性更新所有世界数据（时间、消息计数、用户健康）
        if world_update_params:
            world_update_start = time.time()
            self.db.update_world(world_id, **world_update_params)
            world = self.db.get_world(world_id)
            world_update_time = time.time() - world_update_start
            print(f"更新世界数据耗时: {world_update_time:.3f}秒")
        
        if time_advancement_seconds > 0:
            user_location = world.user_location or ""
            
            # 批量更新角色最后见面时间
            char_update_start = time.time()
            for character in characters:
                if character.location == user_location:
                    self.db.update_character(
                        character.id,
                        days_since_last_seen=0,
                        last_seen_date=world.current_date
                    )
                else:
                    current_time_str = f"{world.current_date} {world.current_time}"
                    last_seen_time_str = f"{character.last_seen_date} 00:00:00"
                    seconds_apart = self.time_calculator.get_time_diff_seconds(last_seen_time_str, current_time_str)
                    days_apart = seconds_apart // 86400
                    self.db.update_character(
                        character.id,
                        days_since_last_seen=days_apart
                    )
            char_update_time = time.time() - char_update_start
            print(f"批量更新角色最后见面时间耗时: {char_update_time:.3f}秒")
        
        # 测量API响应处理总时间
        process_response_time = time.time() - process_response_start
        print(f"处理API响应总耗时: {process_response_time:.3f}秒")
        
        # 测量总处理时间
        total_time = time.time() - start_time
        print(f"处理用户消息总耗时: {total_time:.3f}秒")
        
        # 检查并处理远程角色事件
        if self.remote_event_manager:
            try:
                remote_events = await self.remote_event_manager.check_and_process_events(world)
                timeline_events.extend(remote_events)
            except Exception as e:
                print(f"处理远程角色事件时发生错误: {e}")
        
        return result_responses, timeline_events, []
    
    def process_user_message_sync(
        self,
        world_id: int,
        session_id: int,
        user_message: str,
        user_location: str = None
    ) -> tuple:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.process_user_message(world_id, session_id, user_message, user_location)
            )
            return result
        except Exception as e:
            print(f"处理用户消息时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return [], [], []
        finally:
            loop.close()
    
    def get_conversation_context(
        self,
        world_id: int,
        session_id: int,
        include_memories: bool = True,
        character_name: str = None,
        location: str = None
    ) -> Dict[str, any]:
        world = self.db.get_world(world_id)
        characters = self.db.get_characters_by_world(world_id)
        all_chat_history = self._get_chat_messages_with_cache(session_id, limit=100, location=location, after_time_separator=True)
        chat_history = self._select_chat_history(all_chat_history, character_name)
        
        context = {
            'world': {
                'id': world.id,
                'name': world.name,
                'background': world.background
            } if world else None,
            'characters': [
                {
                    'id': char.id,
                    'name': char.name,
                    'description': char.description
                }
                for char in characters
            ],
            'chat_history': [
                {
                    'message_type': msg.message_type,
                    'content': msg.content,
                    'action': msg.action,
                    'character_name': msg.character_name,
                    'created_at': msg.created_at
                }
                for msg in chat_history
            ]
        }
        
        if include_memories:
            all_events = self.memory_manager.get_events(world_id)
            
            memories = []
            for event in all_events:
                memories.append({
                    'content': event.event_content,
                    'importance': event.importance,
                    'memory_type': event.event_type
                })
            
            memories = sorted(memories, key=lambda x: x['importance'], reverse=True)[:10]
            context['memories'] = memories
        
        return context
    
    def format_user_message(self, message: str) -> tuple:
        action = ""
        content = message
        
        if message.startswith('('):
            end_idx = message.find(')')
            if end_idx != -1:
                action = message[1:end_idx].strip()
                content = message[end_idx + 1:].strip()
        
        return content, action
    
    def format_character_message(self, content: str, action: str = "") -> str:
        if action:
            return f"({action}) {content}"
        return content
    
    async def let_character_speak(
        self,
        world_id: int,
        session_id: int,
        selected_character: str = None,
        location: str = None
    ) -> Dict[str, any]:
        print(f"让角色说话")
        world = self.db.get_world(world_id)
        if not world:
            raise Exception("世界不存在")
        
        all_characters = self.db.get_characters_by_world(world_id)
        if not all_characters:
            raise Exception("世界中没有角色")
        
        user_location = world.user_location if world and world.user_location else None
        
        if location:
            characters = [c for c in all_characters if c.location == location]
            print(f"查看位置: {location}, 该位置的角色: {[char.name for char in characters]}")
        elif user_location:
            characters = [c for c in all_characters if c.location == user_location]
            print(f"用户位置: {user_location}, 该位置的角色: {[char.name for char in characters]}")
        else:
            characters = all_characters
            print("未指定位置，将使用所有角色")
        
        selected_char = self.select_character_by_activity(characters, selected_character)
        if not selected_char:
            raise Exception("没有可用的角色")
        
        print(f"根据活跃度选择角色: {selected_char.name} (活跃度: {selected_char.activity_score})")
        
        # 批量查询所有角色的背景图，避免重复查询
        all_bg_images = self.db.get_all_background_images(world_id)
        bg_images_map = {}
        for bg in all_bg_images:
            if bg.character_id not in bg_images_map:
                bg_images_map[bg.character_id] = []
            bg_images_map[bg.character_id].append(bg)
        
        all_chat_history = self._get_chat_messages_with_cache(session_id, limit=100, location=location, after_time_separator=True)
        chat_history = self._select_chat_history(all_chat_history)
        print(f"获取到{len(all_chat_history)}条历史消息，选择了{len(chat_history)}条")
        
        character_ids = [selected_char.id]
        
        short_term_data = self.memory_manager.get_short_term_memories(world_id, selected_char.name)
        short_term_memories = short_term_data.get('memories', [])
        
        long_term_memories = self.memory_manager.get_long_term_memories(world_id, selected_char.name)
        
        memories = []
        for mem in short_term_memories:
            memories.append({
                'content': mem.content,
                'importance': mem.importance,
                'memory_type': mem.memory_type
            })
        for mem in long_term_memories:
            memories.append({
                'content': mem.content,
                'importance': mem.importance,
                'memory_type': mem.memory_type
            })
        
        memories = sorted(memories, key=lambda x: x['importance'], reverse=True)[:10]
        
        all_characters_data = []
        for char in all_characters:
            bg_images = bg_images_map.get(char.id, [])
            char_data = {
                'id': char.id,
                'name': char.name,
                'background': char.background,
                'description': char.description,
                'location': char.location,
                'gender': char.gender,
                'health': self._get_gender_filtered_health(char),
                'background_images': [
                    {
                        'id': bg.id,
                        'description': bg.description,
                        'tags': bg.tags
                    }
                    for bg in bg_images
                ]
            }
            all_characters_data.append(char_data)
        
        character_relationships = self.db.get_character_relationships(world_id)
        relationships_data = []
        for rel in character_relationships:
            source_char = next((c for c in all_characters if c.id == rel.source_character_id), None)
            target_char = next((c for c in all_characters if c.id == rel.target_character_id), None)
            if source_char and target_char:
                relationships_data.append({
                    'source_character_id': rel.source_character_id,
                    'source_character_name': source_char.name,
                    'target_character_id': rel.target_character_id,
                    'target_character_name': target_char.name,
                    'relationship_type': rel.relationship_type,
                    'description': rel.description,
                    'importance': rel.importance
                })
        
        character_data = [{
            'id': selected_char.id,
            'name': selected_char.name,
            'background': selected_char.background,
            'description': selected_char.description,
            'avatar_path': selected_char.avatar_path,
            'location': selected_char.location,
            'gender': selected_char.gender,
            'health': self._get_gender_filtered_health(selected_char),
            'background_images': [
                {
                    'id': bg.id,
                    'description': bg.description,
                    'tags': bg.tags
                }
                for bg in bg_images_map.get(selected_char.id, [])
            ]
        }]
        
        config = self.db.get_api_config()
        model = config.api1_model if config and config.api1_model else "deepseek-chat"
        
        response = await self.deepseek_client.generate_character_speech(
            world_context=world.background or "",
            characters=all_characters_data,
            relationships=relationships_data,
            chat_history=[
                {
                    'message_type': msg.message_type,
                    'content': msg.content,
                    'action': msg.action,
                    'character_name': msg.character_name,
                    'location': msg.location
                }
                for msg in chat_history
            ],
            memories=memories,
            model=model
        )
        
        if not response:
            raise Exception("未能获取角色发言")
        
        character = selected_char
        
        background_image_id = None
        background_image_index = response.get('background_image_index')
        
        if background_image_index is not None:
            char_bg_images = bg_images_map.get(character.id, [])
            if 0 <= background_image_index < len(char_bg_images):
                background_image_id = char_bg_images[background_image_index].id
        
        segments = response.get('segments', [])
        if not segments:
            segments = []
            if response.get('action'):
                segments.append({'type': 'action', 'content': response['action']})
            if response.get('content'):
                segments.append({'type': 'speech', 'content': response['content']})
        
        non_thought_segments = [seg for seg in segments if seg.get('type') != 'thought']
        thought_segments = [seg for seg in segments if seg.get('type') == 'thought']
        if thought_segments:
            segments = non_thought_segments + [thought_segments[0]]
        else:
            segments = non_thought_segments + [{'type': 'thought', 'content': '...'}]
        
        content = ' '.join([seg['content'] for seg in segments if seg['type'] == 'speech'])
        action = ' '.join([seg['content'] for seg in segments if seg['type'] == 'action'])
        
        import json
        segments_json = json.dumps(segments, ensure_ascii=False)
        
        self.db.create_chat_message(
            session_id=session_id,
            character_id=character.id,
            character_name=response['character_name'],
            content=content,
            action=action,
            background_image_id=background_image_id,
            avatar_path=character.avatar_path,
            message_type='character',
            segments=segments_json,
            current_date=world.current_date,
            current_time=world.current_time,
            location=location
        )
        
        self._invalidate_chat_messages_cache(session_id, location)
        
        if response.get('health_updates'):
            health_updates = response['health_updates']
            print(f"角色 {character.name} 健康状态更新: {health_updates}")
            
            update_params = {}
            if 'mouth' in health_updates:
                if isinstance(health_updates['mouth'], dict):
                    update_params['health_mouth'] = health_updates['mouth'].get('description')
                    update_params['health_mouth_color'] = health_updates['mouth'].get('color', '#28a745')
                else:
                    update_params['health_mouth'] = health_updates['mouth']
            if 'anus' in health_updates:
                if isinstance(health_updates['anus'], dict):
                    update_params['health_anus'] = health_updates['anus'].get('description')
                    update_params['health_anus_color'] = health_updates['anus'].get('color', '#28a745')
                else:
                    update_params['health_anus'] = health_updates['anus']
            if 'buttocks' in health_updates:
                if isinstance(health_updates['buttocks'], dict):
                    update_params['health_buttocks'] = health_updates['buttocks'].get('description')
                    update_params['health_buttocks_color'] = health_updates['buttocks'].get('color', '#28a745')
                else:
                    update_params['health_buttocks'] = health_updates['buttocks']
            if 'penis' in health_updates:
                if isinstance(health_updates['penis'], dict):
                    update_params['health_penis'] = health_updates['penis'].get('description')
                    update_params['health_penis_color'] = health_updates['penis'].get('color', '#28a745')
                else:
                    update_params['health_penis'] = health_updates['penis']
            if 'testicles' in health_updates:
                if isinstance(health_updates['testicles'], dict):
                    update_params['health_testicles'] = health_updates['testicles'].get('description')
                    update_params['health_testicles_color'] = health_updates['testicles'].get('color', '#28a745')
                else:
                    update_params['health_testicles'] = health_updates['testicles']
            if 'left_breast' in health_updates:
                if isinstance(health_updates['left_breast'], dict):
                    update_params['health_left_breast'] = health_updates['left_breast'].get('description')
                    update_params['health_left_breast_color'] = health_updates['left_breast'].get('color', '#28a745')
                else:
                    update_params['health_left_breast'] = health_updates['left_breast']
            if 'right_breast' in health_updates:
                if isinstance(health_updates['right_breast'], dict):
                    update_params['health_right_breast'] = health_updates['right_breast'].get('description')
                    update_params['health_right_breast_color'] = health_updates['right_breast'].get('color', '#28a745')
                else:
                    update_params['health_right_breast'] = health_updates['right_breast']
            if 'vagina' in health_updates:
                if isinstance(health_updates['vagina'], dict):
                    update_params['health_vagina'] = health_updates['vagina'].get('description')
                    update_params['health_vagina_color'] = health_updates['vagina'].get('color', '#28a745')
                else:
                    update_params['health_vagina'] = health_updates['vagina']
            
            if update_params:
                self.db.update_character(character.id, **update_params)
        
        if response.get('user_health_updates'):
            user_health_updates = response['user_health_updates']
            print(f"用户健康状态更新: {user_health_updates}")
            
            update_params = {}
            if 'mouth' in user_health_updates:
                if isinstance(user_health_updates['mouth'], dict):
                    update_params['user_health_mouth'] = user_health_updates['mouth'].get('description')
                    update_params['user_health_mouth_color'] = user_health_updates['mouth'].get('color', '#28a745')
                else:
                    update_params['user_health_mouth'] = user_health_updates['mouth']
            if 'anus' in user_health_updates:
                if isinstance(user_health_updates['anus'], dict):
                    update_params['user_health_anus'] = user_health_updates['anus'].get('description')
                    update_params['user_health_anus_color'] = user_health_updates['anus'].get('color', '#28a745')
                else:
                    update_params['user_health_anus'] = user_health_updates['anus']
            if 'buttocks' in user_health_updates:
                if isinstance(user_health_updates['buttocks'], dict):
                    update_params['user_health_buttocks'] = user_health_updates['buttocks'].get('description')
                    update_params['user_health_buttocks_color'] = user_health_updates['buttocks'].get('color', '#28a745')
                else:
                    update_params['user_health_buttocks'] = user_health_updates['buttocks']
            if 'penis' in user_health_updates:
                if isinstance(user_health_updates['penis'], dict):
                    update_params['user_health_penis'] = user_health_updates['penis'].get('description')
                    update_params['user_health_penis_color'] = user_health_updates['penis'].get('color', '#28a745')
                else:
                    update_params['user_health_penis'] = user_health_updates['penis']
            if 'testicles' in user_health_updates:
                if isinstance(user_health_updates['testicles'], dict):
                    update_params['user_health_testicles'] = user_health_updates['testicles'].get('description')
                    update_params['user_health_testicles_color'] = user_health_updates['testicles'].get('color', '#28a745')
                else:
                    update_params['user_health_testicles'] = user_health_updates['testicles']
            if 'left_breast' in user_health_updates:
                if isinstance(user_health_updates['left_breast'], dict):
                    update_params['user_health_left_breast'] = user_health_updates['left_breast'].get('description')
                    update_params['user_health_left_breast_color'] = user_health_updates['left_breast'].get('color', '#28a745')
                else:
                    update_params['user_health_left_breast'] = user_health_updates['left_breast']
            if 'right_breast' in user_health_updates:
                if isinstance(user_health_updates['right_breast'], dict):
                    update_params['user_health_right_breast'] = user_health_updates['right_breast'].get('description')
                    update_params['user_health_right_breast_color'] = user_health_updates['right_breast'].get('color', '#28a745')
                else:
                    update_params['user_health_right_breast'] = user_health_updates['right_breast']
            if 'vagina' in user_health_updates:
                if isinstance(user_health_updates['vagina'], dict):
                    update_params['user_health_vagina'] = user_health_updates['vagina'].get('description')
                    update_params['user_health_vagina_color'] = user_health_updates['vagina'].get('color', '#28a745')
                else:
                    update_params['user_health_vagina'] = user_health_updates['vagina']
            
            if update_params:
                self.db.update_world(world_id, **update_params)
        
        time_advancement_seconds = response.get('time_advancement_seconds', 0)
        if time_advancement_seconds > 0:
            print(f"推进时间: {time_advancement_seconds}秒")
            current_time_str = f"{world.current_date} {world.current_time}"
            new_time_str = self.time_calculator.add_seconds(current_time_str, time_advancement_seconds)
            
            new_date_part, new_time_part = new_time_str.split(' ')
            self.db.update_world(world_id, current_date=new_date_part, current_time=new_time_part)
            print(f"时间从 {world.current_date} {world.current_time} 推进到 {new_date_part} {new_time_part}")
        
        segments = response.get('segments', [])
        if not segments:
            segments = []
            if response.get('action'):
                segments.append({'type': 'action', 'content': response['action']})
            if response.get('content'):
                segments.append({'type': 'speech', 'content': response['content']})
        
        non_thought_segments = [seg for seg in segments if seg.get('type') != 'thought']
        thought_segments = [seg for seg in segments if seg.get('type') == 'thought']
        if thought_segments:
            segments = non_thought_segments + [thought_segments[0]]
        else:
            segments = non_thought_segments + [{'type': 'thought', 'content': '...'}]
        
        return {
            'character_id': character.id,
            'character_name': response['character_name'],
            'segments': segments,
            'background_image_id': background_image_id,
            'world_id': world_id,
            'all_characters': all_characters
        }
    
    def let_character_speak_sync(
        self,
        world_id: int,
        session_id: int,
        user_location: str,
        selected_character: str = None
    ) -> Dict[str, any]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.let_character_speak(world_id, session_id, user_location, selected_character)
            )
            return result
        except Exception as e:
            print(f"让角色说话时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            loop.close()
