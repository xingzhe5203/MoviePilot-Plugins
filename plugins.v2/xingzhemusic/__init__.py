import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType


class XingzheMusic(_PluginBase):

    plugin_name = "行者music"
    plugin_desc = "OpenCD无损音乐资源下载插件"
    plugin_icon = "music.png"
    plugin_version = "1.0.0"
    plugin_author = "ptmusic"
    author_url = "https://github.com/ptmusic"
    plugin_config_prefix = "xingzhe_music_"
    plugin_order = 50
    auth_level = 1

    _enabled: bool = False
    _cookie: str = ""
    _pass_key: str = ""
    _site_url: str = "https://open.cd"
    _site_name: str = "OpenCD"
    _download_path: str = ""
    _max_downloads: int = 5
    _logged_in: bool = False

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._cookie = config.get("cookie") or ""
            self._pass_key = config.get("pass_key") or ""
            self._download_path = config.get("download_path") or ""
            self._max_downloads = config.get("max_downloads") or 5
        self._logged_in = False

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [
            {
                "cmd": "/ptmusic_search",
                "event": EventType.PluginAction,
                "desc": "PT音乐搜索",
                "category": "PT音乐",
                "data": {
                    "action": "ptmusic_search"
                }
            },
            {
                "cmd": "/ptmusic_list",
                "event": EventType.PluginAction,
                "desc": "PT音乐列表",
                "category": "PT音乐",
                "data": {
                    "action": "ptmusic_list"
                }
            }
        ]

    @eventmanager.register(EventType.PluginAction)
    def process_action(self, event: Event):
        event_data = event.event_data or {}
        action = event_data.get("action")
        if action == "ptmusic_search":
            keyword = event_data.get("keyword", "")
            asyncio.create_task(self._async_search(keyword))
        elif action == "ptmusic_list":
            page = event_data.get("page", 1)
            asyncio.create_task(self._async_list(page))

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/search",
                "endpoint": self.api_search,
                "methods": ["GET"],
                "summary": "搜索音乐资源",
                "auth": "bear"
            },
            {
                "path": "/list",
                "endpoint": self.api_list,
                "methods": ["GET"],
                "summary": "获取种子列表",
                "auth": "bear"
            },
            {
                "path": "/download",
                "endpoint": self.api_download,
                "methods": ["POST"],
                "summary": "下载种子",
                "auth": "bear"
            },
            {
                "path": "/status",
                "endpoint": self.api_status,
                "methods": ["GET"],
                "summary": "检查登录状态",
                "auth": "bear"
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "max_downloads",
                                            "label": "最大下载数"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "cookie",
                                            "label": "OpenCD Cookie",
                                            "placeholder": "请输入完整的Cookie字符串"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "pass_key",
                                            "label": "Passkey",
                                            "placeholder": "下载密钥（可选）"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "download_path",
                                            "label": "下载保存路径",
                                            "placeholder": "/path/to/downloads"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "info",
                                            "variant": "tonal",
                                            "text": "Cookie获取方法：登录 open.cd 后，按F12打开开发者工具，在Network中找到请求的Cookie头并复制"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "cookie": "",
            "pass_key": "",
            "download_path": "",
            "max_downloads": 5
        }

    def get_page(self) -> List[dict]:
        status = "未登录" if not self._logged_in else "已登录"
        status_color = "error" if not self._logged_in else "success"

        return [
            {
                "component": "VRow",
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 3},
                        "content": [
                            {
                                "component": "VCard",
                                "props": {"variant": "tonal", "color": status_color},
                                "content": [
                                    {
                                        "component": "VCardText",
                                        "content": [
                                            {
                                                "component": "div",
                                                "props": {"class": "text-center"},
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-h6"},
                                                        "text": self._site_name
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-h4 font-weight-bold"},
                                                        "text": status
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    async def _check_login(self) -> bool:
        if not self._cookie:
            return False
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Cookie": self._cookie
                }
                response = await client.get(f"{self._site_url}/torrents.php", headers=headers)
                if response.status_code == 200:
                    if "登录" not in response.text and "注册" not in response.text:
                        self._logged_in = True
                        logger.info(f"{self._site_name} Cookie认证成功")
                        return True
            self._logged_in = False
            return False
        except Exception as e:
            logger.error(f"{self._site_name} 认证异常: {str(e)}")
            self._logged_in = False
            return False

    async def _search(self, keyword: str, page: int = 1) -> List[Dict[str, Any]]:
        if not self._logged_in:
            await self._check_login()
        if not self._logged_in:
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Cookie": self._cookie
                }
                params = {"search": keyword, "page": page}
                response = await client.get(f"{self._site_url}/torrents.php", params=params, headers=headers)
                return self._parse_torrents(response.text)
        except Exception as e:
            logger.error(f"搜索异常: {str(e)}")
            return []

    async def _list_torrents(self, page: int = 1) -> List[Dict[str, Any]]:
        if not self._logged_in:
            await self._check_login()
        if not self._logged_in:
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Cookie": self._cookie
                }
                params = {"page": page}
                response = await client.get(f"{self._site_url}/torrents.php", params=params, headers=headers)
                return self._parse_torrents(response.text)
        except Exception as e:
            logger.error(f"获取列表异常: {str(e)}")
            return []

    def _parse_torrents(self, html: str) -> List[Dict[str, Any]]:
        resources = []
        pattern = r'<tr[^>]*class="[^"]*torrent(?:[^\s"]*)"[^>]*>(.*?)</tr>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            try:
                resource = self._parse_torrent_row(match)
                if resource:
                    resources.append(resource)
            except Exception:
                continue

        if not resources:
            resources = self._fallback_parse(html)

        return resources

    def _parse_torrent_row(self, row_html: str) -> Optional[Dict[str, Any]]:
        try:
            id_match = re.search(r'torrents\.php\?id=(\d+)', row_html)
            if not id_match:
                id_match = re.search(r'/download\.php\?id=(\d+)', row_html)
            if not id_match:
                return None

            torrent_id = id_match.group(1)

            title_match = re.search(r'title="([^"]+)"', row_html)
            if not title_match:
                title_match = re.search(r'<a[^>]+>([^<]+)</a>', row_html)
            title = title_match.group(1).strip() if title_match else "Unknown"

            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB))', row_html, re.IGNORECASE)
            size_str = size_match.group(1) if size_match else "0 B"

            seeders_match = re.search(r'<td[^>]*class="[^"]*seeders?[^"]*"[^>]*>(\d+)</td>', row_html, re.IGNORECASE)
            seeders = int(seeders_match.group(1)) if seeders_match else 0

            leechers_match = re.search(r'<td[^>]*class="[^"]*leechers?[^"]*"[^>]*>(\d+)</td>', row_html, re.IGNORECASE)
            leechers = int(leechers_match.group(1)) if leechers_match else 0

            free_match = re.search(r'(?:class="[^"]*free[^"]*"|FREE|免费)', row_html, re.IGNORECASE)
            is_free = free_match is not None

            download_url = f"{self._site_url}/download.php?id={torrent_id}"
            if self._pass_key:
                download_url += f"&passkey={self._pass_key}"

            return {
                "id": torrent_id,
                "title": title,
                "size": size_str,
                "seeders": seeders,
                "leechers": leechers,
                "is_free": is_free,
                "download_url": download_url
            }
        except Exception:
            return None

    def _fallback_parse(self, html: str) -> List[Dict[str, Any]]:
        resources = []
        link_pattern = r'<a[^>]+href="(/torrents\.php\?id=\d+)"[^>]*>([^<]+)</a>'
        links = re.findall(link_pattern, html)

        for link_url, link_text in links:
            try:
                id_match = re.search(r'id=(\d+)', link_url)
                if not id_match:
                    continue
                torrent_id = id_match.group(1)
                resources.append({
                    "id": torrent_id,
                    "title": link_text.strip(),
                    "size": "Unknown",
                    "seeders": 0,
                    "leechers": 0,
                    "is_free": False,
                    "download_url": f"{self._site_url}/download.php?id={torrent_id}"
                })
            except Exception:
                continue

        return resources

    async def _download_torrent(self, torrent_id: str, title: str = "") -> Optional[str]:
        if not self._logged_in:
            await self._check_login()
        if not self._logged_in:
            return None

        try:
            download_url = f"{self._site_url}/download.php?id={torrent_id}"
            if self._pass_key:
                download_url += f"&passkey={self._pass_key}"

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Cookie": self._cookie
                }
                response = await client.get(download_url, headers=headers)

                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" in content_type.lower():
                        logger.error("Cookie已失效，无法下载")
                        return None

                    if self._download_path:
                        import os
                        os.makedirs(self._download_path, exist_ok=True)

                        safe_title = self._clean_filename(title) if title else torrent_id
                        filename = f"{safe_title}.torrent"
                        filepath = os.path.join(self._download_path, filename)

                        counter = 1
                        while os.path.exists(filepath):
                            filepath = os.path.join(self._download_path, f"{safe_title}_{counter}.torrent")
                            counter += 1

                        with open(filepath, "wb") as f:
                            f.write(response.content)

                        logger.info(f"种子下载成功: {filepath}")
                        return filepath

                return None
        except Exception as e:
            logger.error(f"下载异常: {str(e)}")
            return None

    def _clean_filename(self, filename: str) -> str:
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        cleaned = re.sub(invalid_chars, '_', filename)
        cleaned = cleaned.strip('. ')
        if len(cleaned) > 200:
            cleaned = cleaned[:200]
        return cleaned or "untitled"

    async def _async_search(self, keyword: str):
        results = await self._search(keyword)
        count = len(results)
        message = f"搜索「{keyword}」找到 {count} 条结果"
        if count > 0:
            top_results = results[:5]
            details = "\n".join([f"{i+1}. {r.get('title', 'Unknown')} ({r.get('size', 'N/A')})" 
                                  for i, r in enumerate(top_results)])
            message += f"\n\n{details}"
            if count > 5:
                message += f"\n\n... 还有 {count - 5} 条结果"
        self.post_message(title="PT音乐搜索", text=message)

    async def _async_list(self, page: int = 1):
        results = await self._list_torrents(page)
        count = len(results)
        message = f"获取到第 {page} 页 {count} 条最新资源"
        if count > 0:
            top_results = results[:5]
            details = "\n".join([f"{i+1}. {r.get('title', 'Unknown')} (做种:{r.get('seeders', 0)})" 
                                  for i, r in enumerate(top_results)])
            message += f"\n\n{details}"
        self.post_message(title="PT音乐列表", text=message)

    async def api_search(self, keyword: str = "", page: int = 1) -> Dict[str, Any]:
        if not keyword:
            return {"success": False, "message": "请提供搜索关键词"}
        
        results = await self._search(keyword, page)
        return {
            "success": True,
            "data": results,
            "total": len(results)
        }

    async def api_list(self, page: int = 1) -> Dict[str, Any]:
        results = await self._list_torrents(page)
        return {
            "success": True,
            "data": results,
            "total": len(results)
        }

    async def api_download(self, torrent_id: str, title: str = "") -> Dict[str, Any]:
        if not torrent_id:
            return {"success": False, "message": "请提供种子ID"}
        
        filepath = await self._download_torrent(torrent_id, title)
        if filepath:
            return {"success": True, "path": filepath}
        return {"success": False, "message": "下载失败，请检查Cookie是否有效"}

    async def api_status(self) -> Dict[str, Any]:
        logged_in = await self._check_login()
        return {
            "success": True,
            "logged_in": logged_in,
            "site": self._site_name
        }

    def stop_service(self):
        self._logged_in = False