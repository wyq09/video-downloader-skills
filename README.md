# Video Downloader - 视频下载工具

一个功能强大的跨平台视频下载和格式转换工具，支持 YouTube、Bilibili、小红书等 300+ 网站的视频下载。

[English](README_EN.md) | 简体中文

## 功能特性

- 支持 300+ 视频网站（YouTube、Bilibili、Vimeo、小红书等）
- 智能画质选择，自动下载最佳质量
- 批量下载支持，支持频道/用户主页批量下载
- 音频提取功能（MP3/M4A）
- 自动字幕嵌入
- Cookie 认证支持，可下载需要登录的视频
- 自动格式转换为标准 MP4
- 智能错误处理和重试机制

## 不支持的平台

- 抖音 (Douyin) - 由于严格的反爬虫措施
- TikTok - 同上

## 安装依赖

### macOS
```bash
brew install yt-dlp ffmpeg
```

### Linux (Debian/Ubuntu)
```bash
sudo apt install yt-dlp ffmpeg
```

### Linux (Fedora)
```bash
sudo dnf install yt-dlp ffmpeg
```

### Linux (Arch)
```bash
sudo pacman -S yt-dlp ffmpeg
```

### Windows
```bash
winget install yt-dlp ffmpeg
# 或者
pip install yt-dlp
```

## 使用方法

### 基本用法

| 使用场景 | 命令格式 |
|---------|---------|
| 下载单个视频 | `/video-downloader <URL>` |
| 批量下载 | `/video-downloader <URL1> <URL2> <URL3>` |
| 仅提取音频 | `/video-downloader --audio-only <URL>` |
| 指定保存路径 | `/video-downloader -o "路径" <URL>` |
| 强制画质 | `/video-downloader --quality 720p <URL>` |
| 使用浏览器 Cookie | `/video-downloader --cookies-from-browser chrome <URL>` |
| 频道批量下载 | `/video-downloader --channel <URL> --count 20` |

### 示例

#### 1. 下载单个视频
```bash
/video-downloader https://www.youtube.com/watch?v=xxxxx
```

#### 2. 批量下载
```bash
/video-downloader https://www.youtube.com/watch?v=1 https://www.youtube.com/watch?v=2
```

#### 3. 仅提取音频
```bash
/video-downloader --audio-only https://www.bilibili.com/video/BVxxxxx
```

#### 4. 下载 B 站视频（使用 Cookie）
```bash
/video-downloader --cookies-from-browser chrome https://www.bilibili.com/video/BVxxxxx
```

#### 5. 批量下载频道视频
```bash
# 下载最新 10 个视频（默认）
/video-downloader --channel https://www.youtube.com/@username

# 下载最新 20 个视频
/video-downloader --channel https://www.youtube.com/@username --count 20

# 下载 B 站用户视频
/video-downloader --channel https://space.bilibili.com/390306161 --count 5
```

## 参数说明

| 参数 | 简写 | 默认值 | 说明 |
|-----|------|-------|------|
| `--output` | `-o` | `~/Downloads/videos/` | 输出路径（支持自然语言） |
| `--audio-only` | `-a` | `false` | 仅提取音频（MP3） |
| `--quality` | `-q` | `auto` | 强制画质（1080p/720p/480p） |
| `--embed-subs` | `-s` | `true` | 嵌入可用字幕 |
| `--no-convert` | `-n` | `false` | 跳过格式转换 |
| `--max-size` | `-m` | `2.0` | 文件大小上限（GB），超过则降画质 |
| `--cookies-from-browser` | - | `null` | 从浏览器加载 Cookie |
| `--cookies` | - | `null` | Cookie 文件路径 |
| `--channel` | - | `null` | 频道/用户主页 URL |
| `--count` | - | `10` | 下载最新 N 个视频 |
| `--parallel` | - | `1` | 并行下载数量 |

## Cookie 管理

某些网站需要 Cookie 才能下载视频（如 B 站会员视频、微博等）。

### 使用浏览器 Cookie（推荐）
```bash
/video-downloader --cookies-from-browser chrome <URL>
```

支持的浏览器：`chrome`、`firefox`、`safari`、`edge`

### 使用 Cookie 文件
1. 安装浏览器扩展 "Get cookies.txt" 或 "EditThisCookie"
2. 访问目标网站并登录
3. 导出 Cookie 为 Netscape 格式
4. 使用命令：
```bash
/video-downloader --cookies /path/to/cookies.txt <URL>
```

## 自然语言路径支持

工具支持中文路径别名：
- `下载` → `~/Downloads`
- `桌面` → `~/Desktop`
- `文档` → `~/Documents`
- `视频` → `~/Movies`
- `主目录` → `~`
- `当前目录` → `.`

示例：
```bash
/video-downloader -o "桌面" <URL>  # 保存到桌面
/video-downloader -o "下载" <URL>  # 保存到下载文件夹
```

## 支持的频道下载平台

| 平台 | URL 格式 | 需要 Cookie |
|-----|---------|------------|
| YouTube | `youtube.com/@user` 或 `youtube.com/channel/xxx` | 否 |
| Bilibili | `bilibili.com/space/xxx` | 推荐 |
| 小红书 | `xiaohongshu.com/user/profile/xxx` | 推荐 |
| TikTok | `tiktok.com/@username` | 否 |
| Vimeo | `vimeo.com/username` | 否 |

## 抖音替代方案

由于抖音的反爬虫限制，推荐以下替代方案：

1. **抖音 APP** - 使用内置的"保存到本地"功能
2. **浏览器扩展** - 安装"抖音视频下载"或"Video DownloadHelper"
3. **屏幕录制** - 播放视频时进行屏幕录制

## 项目结构

```
video-downloader/
├── SKILL.md           # Skill 配置文件
├── README.md          # 中文说明文档
├── README_EN.md       # 英文说明文档
├── video_downloader.py # 核心实现脚本
└── cookies/           # Cookie 存储目录
```

## 常见问题

**Q: 为什么 B 站下载失败？**
A: B 站某些视频需要 Cookie，请使用 `--cookies-from-browser chrome` 参数。

**Q: 如何加快下载速度？**
A: 可以使用 `--parallel` 参数进行并行下载。

**Q: 下载的视频格式不是 MP4？**
A: 工具会自动转换为 MP4，如需跳过转换请使用 `--no-convert`。

**Q: 如何下载特定画质的视频？**
A: 使用 `--quality` 参数指定，如 `--quality 720p`。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
