# Video Downloader

A powerful cross-platform video download and format conversion tool supporting 300+ websites including YouTube, Bilibili, Xiaohongshu (XHS), and more.

English | [简体中文](README.md)

## Features

- Supports 300+ video websites (YouTube, Bilibili, Vimeo, XHS, etc.)
- Intelligent quality selection with automatic best quality download
- Batch download support for channels/user homepages
- Audio extraction (MP3/M4A)
- Automatic subtitle embedding
- Cookie authentication support for login-required content
- Automatic format conversion to standard MP4
- Smart error handling and retry mechanisms

## Not Supported Platforms

- Douyin (抖音) - Due to strict anti-scraping measures
- TikTok - Same as above

## Dependencies

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
# or
pip install yt-dlp
```

## Usage

### Basic Commands

| Use Case | Command Pattern |
|----------|----------------|
| Download single video | `/video-downloader <URL>` |
| Batch download | `/video-downloader <URL1> <URL2> <URL3>` |
| Audio only | `/video-downloader --audio-only <URL>` |
| Custom path | `/video-downloader -o "path" <URL>` |
| Force quality | `/video-downloader --quality 720p <URL>` |
| Use browser cookies | `/video-downloader --cookies-from-browser chrome <URL>` |
| Channel batch download | `/video-downloader --channel <URL> --count 20` |

### Examples

#### 1. Download Single Video
```bash
/video-downloader https://www.youtube.com/watch?v=xxxxx
```

#### 2. Batch Download
```bash
/video-downloader https://www.youtube.com/watch?v=1 https://www.youtube.com/watch?v=2
```

#### 3. Extract Audio Only
```bash
/video-downloader --audio-only https://www.bilibili.com/video/BVxxxxx
```

#### 4. Download Bilibili Video (with Cookie)
```bash
/video-downloader --cookies-from-browser chrome https://www.bilibili.com/video/BVxxxxx
```

#### 5. Batch Download Channel Videos
```bash
# Download latest 10 videos (default)
/video-downloader --channel https://www.youtube.com/@username

# Download latest 20 videos
/video-downloader --channel https://www.youtube.com/@username --count 20

# Download Bilibili user videos
/video-downloader --channel https://space.bilibili.com/390306161 --count 5
```

## Parameters Reference

| Parameter | Short | Default | Description |
|-----------|-------|---------|-------------|
| `--output` | `-o` | `~/Downloads/videos/` | Output path (supports natural language) |
| `--audio-only` | `-a` | `false` | Extract audio only (MP3) |
| `--quality` | `-q` | `auto` | Force quality (1080p/720p/480p) |
| `--embed-subs` | `-s` | `true` | Embed available subtitles |
| `--no-convert` | `-n` | `false` | Skip format conversion |
| `--max-size` | `-m` | `2.0` | Max file size in GB before quality downgrade |
| `--cookies-from-browser` | - | `null` | Load cookies from browser |
| `--cookies` | - | `null` | Path to cookie file |
| `--channel` | - | `null` | Channel/user homepage URL |
| `--count` | - | `10` | Download latest N videos |
| `--parallel` | - | `1` | Parallel download count |

## Cookie Management

Some websites require cookies to download videos (e.g., Bilibili premium content, Weibo, etc.).

### Using Browser Cookies (Recommended)
```bash
/video-downloader --cookies-from-browser chrome <URL>
```

Supported browsers: `chrome`, `firefox`, `safari`, `edge`

### Using Cookie File
1. Install browser extension "Get cookies.txt" or "EditThisCookie"
2. Visit the target website and log in
3. Export cookies in Netscape format
4. Use command:
```bash
/video-downloader --cookies /path/to/cookies.txt <URL>
```

## Natural Language Path Support

The tool supports Chinese path aliases:
- `下载` → `~/Downloads`
- `桌面` → `~/Desktop`
- `文档` → `~/Documents`
- `视频` → `~/Movies`
- `主目录` → `~`
- `当前目录` → `.`

Example:
```bash
/video-downloader -o "desktop" <URL>  # Save to desktop
/video-downloader -o "downloads" <URL>  # Save to downloads folder
```

## Supported Channel Download Platforms

| Platform | URL Pattern | Cookie Required |
|----------|-------------|-----------------|
| YouTube | `youtube.com/@user` or `youtube.com/channel/xxx` | No |
| Bilibili | `bilibili.com/space/xxx` | Recommended |
| XHS | `xiaohongshu.com/user/profile/xxx` | Recommended |
| TikTok | `tiktok.com/@username` | No |
| Vimeo | `vimeo.com/username` | No |

## Douyin Alternative Solutions

Due to Douyin's anti-scraping restrictions, here are recommended alternatives:

1. **Douyin APP** - Use built-in "Save to local" feature
2. **Browser Extension** - Install "抖音视频下载" or "Video DownloadHelper"
3. **Screen Recording** - Record the video while playing

## Project Structure

```
video-downloader/
├── SKILL.md            # Skill configuration file
├── README.md           # Chinese documentation
├── README_EN.md        # English documentation
├── video_downloader.py # Core implementation script
└── cookies/            # Cookie storage directory
```

## FAQ

**Q: Why does Bilibili download fail?**
A: Some Bilibili videos require cookies. Please use `--cookies-from-browser chrome` parameter.

**Q: How to speed up downloads?**
A: You can use `--parallel` parameter for parallel downloading.

**Q: The downloaded video is not in MP4 format?**
A: The tool automatically converts to MP4. To skip conversion, use `--no-convert`.

**Q: How to download videos with specific quality?**
A: Use `--quality` parameter, e.g., `--quality 720p`.

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!
