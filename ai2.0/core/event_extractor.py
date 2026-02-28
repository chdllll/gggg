from typing import List, Dict, Any
from core.memory_manager import Event

EMOTION_DICT = {
    "高兴": {"intensity": 5, "polarity": "positive"},
    "开心": {"intensity": 5, "polarity": "positive"},
    "快乐": {"intensity": 5, "polarity": "positive"},
    "兴奋": {"intensity": 6, "polarity": "positive"},
    "满意": {"intensity": 4, "polarity": "positive"},
    "喜欢": {"intensity": 4, "polarity": "positive"},
    "爱": {"intensity": 7, "polarity": "positive"},
    "感激": {"intensity": 5, "polarity": "positive"},
    "放心": {"intensity": 3, "polarity": "positive"},
    "安心": {"intensity": 3, "polarity": "positive"},
    "生气": {"intensity": 5, "polarity": "negative"},
    "愤怒": {"intensity": 7, "polarity": "negative"},
    "讨厌": {"intensity": 5, "polarity": "negative"},
    "恨": {"intensity": 7, "polarity": "negative"},
    "难过": {"intensity": 5, "polarity": "negative"},
    "伤心": {"intensity": 6, "polarity": "negative"},
    "痛苦": {"intensity": 7, "polarity": "negative"},
    "害怕": {"intensity": 5, "polarity": "negative"},
    "恐惧": {"intensity": 6, "polarity": "negative"},
    "紧张": {"intensity": 4, "polarity": "negative"},
    "焦虑": {"intensity": 5, "polarity": "negative"},
    "失望": {"intensity": 5, "polarity": "negative"},
    "绝望": {"intensity": 8, "polarity": "negative"},
    "担心": {"intensity": 4, "polarity": "negative"},
    "忧虑": {"intensity": 4, "polarity": "negative"},
    "平静": {"intensity": 2, "polarity": "neutral"},
    "冷静": {"intensity": 2, "polarity": "neutral"},
    "淡然": {"intensity": 1, "polarity": "neutral"},
    "矛盾": {"intensity": 4, "polarity": "mixed"},
    "纠结": {"intensity": 4, "polarity": "mixed"},
    "犹豫": {"intensity": 3, "polarity": "mixed"},
}

INTENSITY_MODIFIERS = {
    "非常": 1.5,
    "极其": 2.0,
    "特别": 1.5,
    "超级": 1.8,
    "有点": 0.5,
    "稍微": 0.5,
    "比较": 0.7,
    "相当": 1.2,
}

EVENT_VERBS = [
    "打", "打了", "救", "救了", "杀", "杀了", "遇", "遇到", "遇到了", "去", "去了", "做", "做了", "买", "买了", "吃", "吃了",
    "帮助", "攻击", "保护", "拒绝", "接受", "离开", "到达",
    "开始", "结束", "继续", "停止", "改变", "决定", "选择", "发现",
    "寻找", "找到", "失去", "获得", "给予", "邀请",
    "回答", "询问", "告诉", "解释", "描述", "讨论", "争论", "同意",
    "反对", "支持", "建议", "要求", "请求", "命令", "指示",
    "打篮球", "打球", "出去", "活动", "运动", "练习", "学习", "看书", "读书", "弹琴", "弹钢琴"
]

RELATIONSHIP_VERBS = [
    "喜欢", "讨厌", "爱", "恨", "信任", "怀疑", "感谢", "道歉",
    "原谅", "责怪", "批评", "表扬", "鼓励", "安慰", "威胁",
    "帮助", "支持", "反对", "合作", "竞争", "欺骗", "背叛"
]

INFORMATION_KEYWORDS = [
    "是", "有", "没有", "住在", "来自", "工作", "学习", "生活",
    "出生", "死亡", "结婚", "离婚", "属于", "包含", "需要", "想要",
    "希望", "计划", "准备", "打算", "认为", "觉得", "相信", "知道"
]

JIEBA_AVAILABLE = False
try:
    import jieba
    import jieba.posseg
    JIEBA_AVAILABLE = True
    print("jieba分词器加载成功")
except ImportError:
    print("警告: jieba未安装，使用简化版事件提取")
    JIEBA_AVAILABLE = False


class EventExtractor:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300
        self.max_cache_size = 100
    
    def _cleanup_cache(self):
        import time
        current_time = time.time()
        keys_to_remove = []
        
        for key, (result, timestamp) in self.cache.items():
            if current_time - timestamp > self.cache_ttl:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
                del self.cache[key]
        
        if len(self.cache) > self.max_cache_size:
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1][1]
            )
            items_to_remove = len(self.cache) - self.max_cache_size
            for key, _ in sorted_items[:items_to_remove]:
                del self.cache[key]
    
    def _get_cached_result(self, text: str, processor):
        import time
        
        cache_key = f"{processor}_{text}"
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result
        
        result = None
        if processor == 'segment':
            result = list(jieba.cut(text))
        elif processor == 'posseg':
            words = jieba.posseg.cut(text)
            result = [(w.word, w.flag) for w in words]
        
        if result:
            self.cache[cache_key] = (result, time.time())
            
            if len(self.cache) > self.max_cache_size:
                self._cleanup_cache()
        
        return result
    
    def extract_events(
        self,
        dialogues: List[str],
        location: str,
        date: str,
        time: str,
        present_characters: List[str]
    ) -> List[Event]:
        events = []
        
        for dialogue in dialogues:
            if JIEBA_AVAILABLE:
                event_memories = self._extract_event_memories_jieba(dialogue)
                emotion_memories = self._extract_emotion_memories_jieba(dialogue)
                relationship_memories = self._extract_relationship_memories_jieba(dialogue)
                information_memories = self._extract_information_memories_jieba(dialogue)
            else:
                event_memories = self._extract_event_memories_simple(dialogue)
                emotion_memories = self._extract_emotion_memories_simple(dialogue)
                relationship_memories = self._extract_relationship_memories_simple(dialogue)
                information_memories = self._extract_information_memories_simple(dialogue)
            
            all_memories = event_memories + emotion_memories + relationship_memories + information_memories
            
            for memory in all_memories:
                event = Event(
                    event_content=memory['content'],
                    event_type=memory['memory_type'],
                    location=location,
                    date=date,
                    time=time,
                    importance=memory['importance'],
                    present_characters=present_characters
                )
                events.append(event)
        
        return events
    
    def _extract_event_memories_jieba(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        words = self._get_cached_result(text, 'segment')
        if not words:
            return memories
        
        posseg_result = self._get_cached_result(text, 'posseg')
        if not posseg_result:
            return memories
        
        for i in range(0, len(words)):
            word = words[i]
            pos_flag = posseg_result[i][1] if i < len(posseg_result) else ''
            
            if pos_flag.startswith('v'):
                if any(verb in word for verb in EVENT_VERBS):
                    obj = None
                    for j in range(i + 1, len(posseg_result)):
                        next_pos = posseg_result[j][1]
                        if next_pos.startswith('n') or next_pos.startswith('a'):
                            obj = words[j]
                            break
                    
                    if obj:
                        content = f"{word}{obj}"
                        importance = 6
                        
                        for mod_word, mod_value in INTENSITY_MODIFIERS.items():
                            if mod_word in text:
                                importance = int(importance * mod_value)
                                break
                        
                        memories.append({
                            "content": content,
                            "importance": importance,
                            "memory_type": "event"
                        })
        
        return memories
    
    def _extract_emotion_memories_jieba(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        for emotion_word, emotion_data in EMOTION_DICT.items():
            if emotion_word in text:
                intensity = emotion_data["intensity"]
                
                for mod_word, mod_value in INTENSITY_MODIFIERS.items():
                    if mod_word in text:
                        intensity = int(intensity * mod_value)
                        break
                
                memories.append({
                    "content": f"情绪: {emotion_word}",
                    "importance": intensity,
                    "memory_type": "emotion"
                })
        
        return memories
    
    def _extract_relationship_memories_jieba(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        words = self._get_cached_result(text, 'segment')
        if not words:
            return memories
        
        posseg_result = self._get_cached_result(text, 'posseg')
        if not posseg_result:
            return memories
        
        for i in range(0, len(words)):
            word = words[i]
            pos_flag = posseg_result[i][1] if i < len(posseg_result) else ''
            
            if pos_flag.startswith('v'):
                if any(verb in word for verb in RELATIONSHIP_VERBS):
                    obj = None
                    for j in range(i + 1, len(posseg_result)):
                        next_pos = posseg_result[j][1]
                        if next_pos.startswith('n') or next_pos.startswith('a'):
                            obj = words[j]
                            break
                    
                    if obj:
                        content = f"关系: {word}{obj}"
                        importance = 5
                        
                        for mod_word, mod_value in INTENSITY_MODIFIERS.items():
                            if mod_word in text:
                                importance = int(importance * mod_value)
                                break
                        
                        memories.append({
                            "content": content,
                            "importance": importance,
                            "memory_type": "relationship"
                        })
        
        return memories
    
    def _extract_information_memories_jieba(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        for keyword in INFORMATION_KEYWORDS:
            if keyword in text:
                importance = 4
                if len(text) > 20:
                    importance += 1
                
                memories.append({
                    "content": text[:100],
                    "importance": importance,
                    "memory_type": "information"
                })
                break
        
        return memories
    
    def _extract_event_memories_simple(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        for verb in EVENT_VERBS:
            if verb in text:
                importance = 6
                for modifier in INTENSITY_MODIFIERS:
                    if modifier in text:
                        importance = int(importance * INTENSITY_MODIFIERS[modifier])
                        break
                
                memories.append({
                    "content": text[:50],
                    "importance": importance,
                    "memory_type": "event"
                })
                break
        
        return memories
    
    def _extract_emotion_memories_simple(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        for emotion_word, emotion_data in EMOTION_DICT.items():
            if emotion_word in text:
                intensity = emotion_data["intensity"]
                
                for modifier in INTENSITY_MODIFIERS:
                    if modifier in text:
                        intensity = int(intensity * INTENSITY_MODIFIERS[modifier])
                        break
                
                memories.append({
                    "content": f"情绪: {emotion_word}",
                    "importance": intensity,
                    "memory_type": "emotion"
                })
                break
        
        return memories
    
    def _extract_relationship_memories_simple(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        for verb in RELATIONSHIP_VERBS:
            if verb in text:
                importance = 5
                for modifier in INTENSITY_MODIFIERS:
                    if modifier in text:
                        importance = int(importance * INTENSITY_MODIFIERS[modifier])
                        break
                
                memories.append({
                    "content": text[:50],
                    "importance": importance,
                    "memory_type": "relationship"
                })
                break
        
        return memories
    
    def _extract_information_memories_simple(self, text: str) -> List[Dict[str, Any]]:
        memories = []
        
        for keyword in INFORMATION_KEYWORDS:
            if keyword in text:
                importance = 4
                if len(text) > 20:
                    importance += 1
                
                memories.append({
                    "content": text[:50],
                    "importance": importance,
                    "memory_type": "information"
                })
                break
        
        return memories
