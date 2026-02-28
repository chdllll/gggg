from typing import List, Dict, Optional
import asyncio
from api import DeepSeekClient

class BackgroundSelector:
    def __init__(self, deepseek_client: DeepSeekClient):
        self.deepseek_client = deepseek_client
        self.cache = {}
    
    async def select_background(
        self,
        character_id: int,
        character_name: str,
        dialogue_content: str,
        action: str,
        background_images: List[Dict[str, any]],
        world_context: str,
        model: str = "deepseek-chat"
    ) -> Optional[int]:
        if not background_images:
            return None
        
        cache_key = f"{character_id}_{hash(dialogue_content)}_{hash(action)}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        selected_id = await self.deepseek_client.select_background_image(
            character_name=character_name,
            dialogue_content=dialogue_content,
            action=action,
            background_images=background_images,
            world_context=world_context,
            model=model
        )
        
        if selected_id:
            self.cache[cache_key] = selected_id
            if len(self.cache) > 100:
                self.cache.pop(next(iter(self.cache)))
        
        return selected_id
    
    def select_background_sync(
        self,
        character_id: int,
        character_name: str,
        dialogue_content: str,
        action: str,
        background_images: List[Dict[str, any]],
        world_context: str,
        model: str = "deepseek-chat"
    ) -> Optional[int]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.select_background(
                    character_id=character_id,
                    character_name=character_name,
                    dialogue_content=dialogue_content,
                    action=action,
                    background_images=background_images,
                    world_context=world_context,
                    model=model
                )
            )
            return result
        except Exception as e:
            print(f"选择背景图时发生错误: {e}")
            return None
        finally:
            loop.close()
    
    def select_background_by_tags(
        self,
        dialogue_content: str,
        action: str,
        background_images: List[Dict[str, any]]
    ) -> Optional[int]:
        if not background_images:
            return None
        
        combined_text = f"{dialogue_content} {action}".lower()
        
        scored_images = []
        for bg in background_images:
            score = 0
            tags = bg.get('tags', '').lower() if bg.get('tags') else ''
            description = bg.get('description', '').lower() if bg.get('description') else ''
            
            tag_parts = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            sexual_activity_keywords = ['性', '做爱', '性爱', '插入', '射精', '高潮', '性交', '交配', '亲密', '抚摸', '亲吻', '口', '手', '脚', '乳房', '阴道', '阴茎', '肛门', '进入', '抱住', '骑', '跪', '躺', '坐']
            is_sexual = any(keyword in combined_text for keyword in sexual_activity_keywords)
            
            if len(tag_parts) >= 1:
                sexual_status = tag_parts[0]
                if is_sexual and '正在进行性行为' in sexual_status:
                    score += 3
                elif not is_sexual and '未进行性行为' in sexual_status:
                    score += 3
            
            if len(tag_parts) >= 2:
                if '正在进行性行为' in tag_parts[0]:
                    position = tag_parts[1]
                    position_keywords = {
                        '前面': ['前面', '正面', '面对面', '面对面'],
                        '后面': ['后面', '背面', '背对', '从后面', '后入'],
                        '骑乘': ['骑', '骑乘', '在上面', '女上', '上位'],
                        '跪着': ['跪', '跪着', '跪姿', '趴跪'],
                        '侧躺': ['侧躺', '侧卧', '躺着', '躺'],
                        '侧坐': ['侧坐', '坐', '坐着', '坐姿']
                    }
                    
                    for pos, keywords in position_keywords.items():
                        if pos == position and any(keyword in combined_text for keyword in keywords):
                            score += 2
                            break
                else:
                    emotion = tag_parts[1]
                    emotion_keywords = {
                        '开心': ['开心', '高兴', '快乐', '愉快', '笑', '喜悦'],
                        '厌恶': ['厌恶', '讨厌', '恶心', '反感']
                    }
                    
                    for emo, keywords in emotion_keywords.items():
                        if emo == emotion and any(keyword in combined_text for keyword in keywords):
                            score += 1
                            break
            
            for word in description.split():
                word = word.strip()
                if word and word in combined_text:
                    score += 0.5
            
            if score > 0:
                scored_images.append((bg['id'], score))
        
        if scored_images:
            scored_images.sort(key=lambda x: x[1], reverse=True)
            return scored_images[0][0]
        
        return None
    
    def select_background_random(self, background_images: List[Dict[str, any]]) -> Optional[int]:
        if not background_images:
            return None
        
        import random
        return random.choice(background_images)['id']
    
    def clear_cache(self):
        self.cache.clear()
