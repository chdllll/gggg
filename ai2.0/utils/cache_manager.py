import os
import json
import tempfile
from typing import Dict, Optional, List
from datetime import datetime

class CacheManager:
    def __init__(self):
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'ai_roleplay_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.api_cache_file = os.path.join(self.cache_dir, 'api_cache.json')
        self.world_cache_file = os.path.join(self.cache_dir, 'world_cache.json')
        self.character_cache_file = os.path.join(self.cache_dir, 'character_cache.json')
        self.chat_cache_file = os.path.join(self.cache_dir, 'chat_cache.json')
    
    def _load_cache_file(self, file_path: str) -> Dict:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载缓存文件失败 {file_path}: {e}")
        return {}
    
    def _save_cache_file(self, file_path: str, data: Dict):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存文件失败 {file_path}: {e}")
    
    def _delete_cache_file(self, file_path: str):
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"删除缓存文件失败 {file_path}: {e}")
    
    def save_api_cache(self, api_config: Dict):
        cache_data = {
            'api_config': api_config,
            'updated_at': datetime.now().isoformat()
        }
        self._save_cache_file(self.api_cache_file, cache_data)
    
    def load_api_cache(self) -> Optional[Dict]:
        return self._load_cache_file(self.api_cache_file)
    
    def clear_api_cache(self):
        self._delete_cache_file(self.api_cache_file)
    
    def save_world_cache(self, world_data: Dict):
        cache_data = {
            'world_data': world_data,
            'updated_at': datetime.now().isoformat()
        }
        self._save_cache_file(self.world_cache_file, cache_data)
    
    def load_world_cache(self) -> Optional[Dict]:
        return self._load_cache_file(self.world_cache_file)
    
    def clear_world_cache(self):
        self._delete_cache_file(self.world_cache_file)
    
    def save_character_cache(self, character_data: Dict, avatar_path: str = None, background_images: List = None):
        cache_data = {
            'character_data': character_data,
            'avatar_path': avatar_path,
            'background_images': background_images or [],
            'updated_at': datetime.now().isoformat()
        }
        self._save_cache_file(self.character_cache_file, cache_data)
    
    def copy_to_cache(self, source_path: str, cache_type: str = "general") -> Optional[str]:
        if not source_path or not os.path.exists(source_path):
            return None
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{cache_type}_{timestamp}_{os.path.basename(source_path)}"
            dest_path = os.path.join(self.cache_dir, filename)
            
            shutil = __import__('shutil')
            shutil.copy2(source_path, dest_path)
            
            return dest_path
        except Exception as e:
            print(f"复制文件到缓存失败: {e}")
            return None
    
    def load_character_cache(self) -> Optional[Dict]:
        return self._load_cache_file(self.character_cache_file)
    
    def clear_character_cache(self):
        self._delete_cache_file(self.character_cache_file)
    
    def save_chat_cache(self, world_id: int, session_id: int, messages: List[Dict]):
        cache_data = {
            'world_id': world_id,
            'session_id': session_id,
            'messages': messages,
            'updated_at': datetime.now().isoformat()
        }
        self._save_cache_file(self.chat_cache_file, cache_data)
    
    def load_chat_cache(self) -> Optional[Dict]:
        return self._load_cache_file(self.chat_cache_file)
    
    def clear_chat_cache(self):
        self._delete_cache_file(self.chat_cache_file)
    
    def clear_all_cache(self):
        self.clear_api_cache()
        self.clear_world_cache()
        self.clear_character_cache()
        self.clear_chat_cache()
    
    def get_cache_size(self) -> int:
        total_size = 0
        for file_path in [self.api_cache_file, self.world_cache_file, 
                         self.character_cache_file, self.chat_cache_file]:
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
        return total_size
    
    def cleanup_old_cache(self, max_age_hours: int = 24):
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in [self.api_cache_file, self.world_cache_file, 
                         self.character_cache_file, self.chat_cache_file]:
            if os.path.exists(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    self._delete_cache_file(file_path)
    
    def get_cache_info(self) -> Dict:
        return {
            'cache_dir': self.cache_dir,
            'api_cache_exists': os.path.exists(self.api_cache_file),
            'world_cache_exists': os.path.exists(self.world_cache_file),
            'character_cache_exists': os.path.exists(self.character_cache_file),
            'chat_cache_exists': os.path.exists(self.chat_cache_file),
            'total_size_bytes': self.get_cache_size(),
            'total_size_mb': round(self.get_cache_size() / (1024 * 1024), 2)
        }
