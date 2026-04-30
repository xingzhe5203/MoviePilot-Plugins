# PT音乐下载插件

MoviePilot插件，用于下载OpenCD站点的无损音乐资源。

## 功能特性

- Cookie认证登录OpenCD站点
- 搜索音乐资源
- 获取最新种子列表
- 下载种子文件到本地
- 支持远程命令 `/ptmusic_search` 和 `/ptmusic_list`
- RESTful API接口

## 安装

1. 将 `ptmusic` 文件夹放入 `MoviePilot-Plugins/plugins.v2/` 目录
2. 在插件市场安装并启用插件
3. 配置Cookie和下载路径

## 配置说明

| 配置项 | 说明 |
|--------|------|
| Cookie | OpenCD站点的登录Cookie |
| Passkey | 下载密钥（可选） |
| 下载路径 | 种子文件保存目录 |
| 最大下载数 | 单次最大下载数量 |

## Cookie获取方法

1. 使用浏览器登录 https://open.cd
2. 按F12打开开发者工具
3. 切换到Network（网络）标签
4. 刷新页面
5. 点击第一个请求，在Request Headers中找到Cookie并复制

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/plugin/Ptmusic/search` | GET | 搜索音乐资源 |
| `/api/v1/plugin/Ptmusic/list` | GET | 获取种子列表 |
| `/api/v1/plugin/Ptmusic/download` | POST | 下载种子 |
| `/api/v1/plugin/Ptmusic/status` | GET | 检查登录状态 |

## 远程命令

- `/ptmusic_search <关键词>` - 搜索音乐
- `/ptmusic_list [页码]` - 获取列表

## 版本历史

- v1.0.0: 初始版本