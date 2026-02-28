import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import threading

@dataclass
class Event:
    event_content: str
    event_type: str
    location: str
    date: str
    time: str
    importance: int
    present_characters: List[str]

@dataclass
class ShortTermMemory:
    content: str
    importance: int
    memory_type: str
    source_event: str

@dataclass
class LongTermMemory:
    content: str
    importance: int
    memory_type: str

class MemoryManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.short_term_cache = {}
        self.long_term_cache = {}
        self.events_cache = {}
        self.cache_ttl = 30
        self._file_lock = threading.Lock()
        self.max_cache_size = 50
    
    def _cleanup_cache(self, cache_dict):
        import time
        current_time = time.time()
        keys_to_remove = []
        
        for key, (data, timestamp) in cache_dict.items():
            if current_time - timestamp > self.cache_ttl:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del cache_dict[key]
        
        if len(cache_dict) > self.max_cache_size:
            sorted_items = sorted(
                cache_dict.items(),
                key=lambda x: x[1][1]
            )
            items_to_remove = len(cache_dict) - self.max_cache_size
            for key, _ in sorted_items[:items_to_remove]:
                del cache_dict[key]
    
    def _get_world_dir(self, world_id: int) -> str:
        return os.path.join(self.db._get_world_dir(world_id))
    
    def _get_events_path(self, world_id: int) -> str:
        return os.path.join(self._get_world_dir(world_id), 'events.json')
    
    def _get_character_dir(self, world_id: int, character_name: str) -> str:
        return os.path.join(self._get_world_dir(world_id), 'characters', character_name)
    
    def _get_memories_path(self, world_id: int, character_name: str) -> str:
        return os.path.join(self._get_character_dir(world_id, character_name), 'memories.json')
    
    def _get_long_memories_path(self, world_id: int, character_name: str) -> str:
        return os.path.join(self._get_character_dir(world_id, character_name), 'long_memories.json')
    
    def add_event(self, world_id: int, event: Event):
        events_path = self._get_events_path(world_id)
        
        with self._file_lock:
            os.makedirs(os.path.dirname(events_path), exist_ok=True)
            
            events = []
            if os.path.exists(events_path):
                with open(events_path, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            
            events.append(asdict(event))
            
            with open(events_path, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
    
    def get_events(self, world_id: int) -> List[Event]:
        events_path = self._get_events_path(world_id)
        
        if not os.path.exists(events_path):
            return []
        
        with self._file_lock:
            with open(events_path, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
        
        return [Event(**event) for event in events_data]
    
    def add_short_term_memory(self, world_id: int, character_name: str, memory: ShortTermMemory) -> int:
        memories_path = self._get_memories_path(world_id, character_name)
        
        with self._file_lock:
            os.makedirs(os.path.dirname(memories_path), exist_ok=True)
            
            data = {
                'memories': [],
                'counter': 0
            }
            
            if os.path.exists(memories_path):
                with open(memories_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            memories = data['memories']
            counter = data['counter']
            
            memories.append(asdict(memory))
            
            if len(memories) > 5:
                memories = memories[-5:]
                if counter > 5:
                    counter = 5
            
            counter += 1
            
            data = {
                'memories': memories,
                'counter': counter
            }
            
            with open(memories_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return counter
    
    def add_short_term_memories_batch(self, world_id: int, character_name: str, memories: List[ShortTermMemory]) -> int:
        memories_path = self._get_memories_path(world_id, character_name)
        
        with self._file_lock:
            os.makedirs(os.path.dirname(memories_path), exist_ok=True)
            
            data = {
                'memories': [],
                'counter': 0
            }
            
            if os.path.exists(memories_path):
                with open(memories_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            existing_memories = data['memories']
            counter = data['counter']
            
            for memory in memories:
                existing_memories.append(asdict(memory))
                counter += 1
            
            if len(existing_memories) > 5:
                existing_memories = existing_memories[-5:]
                if counter > 5:
                    counter = 5
            
            data = {
                'memories': existing_memories,
                'counter': counter
            }
            
            with open(memories_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        cache_key = f"{world_id}_{character_name}"
        if cache_key in self.short_term_cache:
            del self.short_term_cache[cache_key]
        
        self._cleanup_cache(self.short_term_cache)
        
        return counter
    
    def get_short_term_memories(self, world_id: int, character_name: str) -> Dict[str, Any]:
        import time
        cache_key = f"{world_id}_{character_name}"
        
        if cache_key in self.short_term_cache:
            cached_data, timestamp = self.short_term_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
        
        memories_path = self._get_memories_path(world_id, character_name)
        
        if not os.path.exists(memories_path):
            result = {
                'memories': [],
                'counter': 0
            }
            self.short_term_cache[cache_key] = (result, time.time())
            return result
        
        with self._file_lock:
            with open(memories_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        memories = [ShortTermMemory(**mem) for mem in data.get('memories', [])]
        
        result = {
            'memories': memories,
            'counter': data.get('counter', 0)
        }
        
        self.short_term_cache[cache_key] = (result, time.time())
        
        if len(self.short_term_cache) > self.max_cache_size:
            self._cleanup_cache(self.short_term_cache)
        
        return result
    
    def clear_short_term_memories(self, world_id: int, character_name: str):
        memories_path = self._get_memories_path(world_id, character_name)
        
        if not os.path.exists(memories_path):
            return
        
        with self._file_lock:
            with open(memories_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['counter'] = 0
            
            with open(memories_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def reset_short_term_counter(self, world_id: int, character_name: str):
        memories_path = self._get_memories_path(world_id, character_name)
        
        if not os.path.exists(memories_path):
            return
        
        with self._file_lock:
            with open(memories_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['counter'] = 0
            
            with open(memories_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_long_term_memory(self, world_id: int, character_name: str, memory: LongTermMemory):
        long_memories_path = self._get_long_memories_path(world_id, character_name)
        
        with self._file_lock:
            os.makedirs(os.path.dirname(long_memories_path), exist_ok=True)
            
            long_memories = []
            if os.path.exists(long_memories_path):
                with open(long_memories_path, 'r', encoding='utf-8') as f:
                    long_memories = json.load(f)
            
            long_memories.append(asdict(memory))
            
            with open(long_memories_path, 'w', encoding='utf-8') as f:
                json.dump(long_memories, f, ensure_ascii=False, indent=2)
    
    def get_long_term_memories(self, world_id: int, character_name: str) -> List[LongTermMemory]:
        import time
        cache_key = f"{world_id}_{character_name}_long"
        
        if cache_key in self.long_term_cache:
            cached_data, timestamp = self.long_term_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
        
        long_memories_path = self._get_long_memories_path(world_id, character_name)
        
        if not os.path.exists(long_memories_path):
            result = []
            self.long_term_cache[cache_key] = (result, time.time())
            return result
        
        with self._file_lock:
            with open(long_memories_path, 'r', encoding='utf-8') as f:
                long_memories_data = json.load(f)
        
        result = [LongTermMemory(**memory) for memory in long_memories_data]
        
        self.long_term_cache[cache_key] = (result, time.time())
        
        if len(self.long_term_cache) > self.max_cache_size:
            self._cleanup_cache(self.long_term_cache)
        
        return result
    
    def replace_long_term_memories(self, world_id: int, character_name: str, memories: List[LongTermMemory]):
        long_memories_path = self._get_long_memories_path(world_id, character_name)
        
        with self._file_lock:
            os.makedirs(os.path.dirname(long_memories_path), exist_ok=True)
            
            long_memories = [asdict(mem) for mem in memories]
            
            with open(long_memories_path, 'w', encoding='utf-8') as f:
                json.dump(long_memories, f, ensure_ascii=False, indent=2)