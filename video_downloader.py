#!/usr/bin/env python3
"""
Video Downloader - Cross-platform video download and conversion tool
Supports: yt-dlp for downloading, ffmpeg for conversion
"""

import argparse
import csv
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


@dataclass
class DownloadResult:
    """Result of a download operation"""
    url: str
    success: bool = False
    output_file: Optional[str] = None
    error: Optional[str] = None
    was_converted: bool = False
    needs_cookies: bool = False


@dataclass
class DownloadOptions:
    """Options for video download"""
    output_dir: str = "~/Downloads/videos"
    audio_only: bool = False
    quality: Optional[str] = None  # 1080p, 720p, 480p
    embed_subs: bool = True
    no_convert: bool = False
    max_size_gb: float = 2.0
    verbose: bool = False
    cookies_from_browser: Optional[str] = None  # chrome, firefox, safari, etc.
    cookies_file: Optional[str] = None  # Path to cookie file
    no_cookies: bool = False  # Skip cookie handling


@dataclass
class ChannelInfo:
    """博主信息"""
    platform: str
    channel_name: str
    channel_url: str
    fan_count: Optional[int] = None
    video_count: int = 0
    avatar_url: Optional[str] = None


@dataclass
class VideoMetadata:
    """视频元数据"""
    video_id: str
    title: str
    url: str
    duration: Optional[int] = None  # 秒
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    repost_count: Optional[int] = None  # B站
    coin_count: Optional[int] = None  # B站
    favorite_count: Optional[int] = None
    thumbnail: Optional[str] = None


@dataclass
class ChannelOptions:
    """频道下载选项"""
    count: Optional[int] = None  # 下载数量
    date_after: Optional[str] = None  # 日期筛选
    date_before: Optional[str] = None  # 日期范围筛选
    min_views: Optional[int] = None  # 最小播放量筛选
    parallel: int = 1  # 并发数
    output_dir: str = "./output"
    cookies_from_browser: Optional[str] = None  # 浏览器 cookies
    cookies_file: Optional[str] = None  # cookie 文件路径


class PathResolver:
    """Resolve natural language paths to actual filesystem paths"""

    ALIASES = {
        "下载": "~/Downloads",
        "桌面": "~/Desktop",
        "documents": "~/Documents",
        "文档": "~/Documents",
        "视频": "~/Movies",
        "music": "~/Music",
        "音乐": "~/Music",
        "pictures": "~/Pictures",
        "图片": "~/Pictures",
        "home": "~",
        "主目录": "~",
        "current": ".",
        "当前目录": ".",
    }

    @classmethod
    def resolve(cls, path: str) -> str:
        """Resolve a path, handling natural language aliases"""
        # Check for natural language aliases
        for alias, target in cls.ALIASES.items():
            if alias.lower() in path.lower():
                # Replace the alias with the target
                path = path.lower().replace(alias, target).strip()

        # Expand user home directory
        path = os.path.expanduser(path)

        # Convert to absolute path
        path = os.path.abspath(path)

        return path

    @classmethod
    def ensure_dir(cls, path: str) -> str:
        """Ensure directory exists, create if needed"""
        resolved = cls.resolve(path)
        Path(resolved).mkdir(parents=True, exist_ok=True)
        return resolved


class DependencyManager:
    """Manage installation and checking of yt-dlp and ffmpeg"""

    REQUIRED_VERSIONS = {
        "yt-dlp": "2023.3.4",
        "ffmpeg": "4.0"
    }

    @classmethod
    def check_dependencies(cls) -> Dict[str, bool]:
        """Check which dependencies are installed"""
        return {
            "yt-dlp": shutil.which("yt-dlp") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None,
        }

    @classmethod
    def get_version(cls, cmd: str) -> Optional[str]:
        """Get version of a command"""
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version from output
                first_line = result.stdout.split('\n')[0]
                return first_line
        except Exception:
            pass
        return None

    @classmethod
    def install_dependency(cls, dep: str) -> bool:
        """Attempt to install a missing dependency"""
        system = platform.system()
        try:
            if dep == "yt-dlp":
                # yt-dlp can always be installed via pip
                print(f"Installing yt-dlp via pip...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                    capture_output=True,
                    timeout=300
                )
                return result.returncode == 0

            elif dep == "ffmpeg":
                if system == "Darwin":  # macOS
                    if shutil.which("brew"):
                        print(f"Installing ffmpeg via Homebrew...")
                        result = subprocess.run(
                            ["brew", "install", "ffmpeg"],
                            capture_output=True,
                            timeout=600
                        )
                        return result.returncode == 0
                elif system == "Linux":
                    # Try common package managers
                    for pm, cmd in [
                        ("apt", ["sudo", "apt", "install", "-y", "ffmpeg"]),
                        ("dnf", ["sudo", "dnf", "install", "-y", "ffmpeg"]),
                        ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"]),
                    ]:
                        if shutil.which(pm):
                            print(f"Installing ffmpeg via {pm}...")
                            result = subprocess.run(cmd, capture_output=True, timeout=600)
                            return result.returncode == 0
                elif system == "Windows":
                    if shutil.which("winget"):
                        print(f"Installing ffmpeg via winget...")
                        result = subprocess.run(
                            ["winget", "install", "ffmpeg", "--accept-source-agreements"],
                            capture_output=True,
                            timeout=600
                        )
                        return result.returncode == 0
        except Exception as e:
            print(f"Failed to install {dep}: {e}")

        return False

    @classmethod
    def ensure_dependencies(cls, verbose: bool = False) -> bool:
        """Ensure all required dependencies are installed"""
        deps = cls.check_dependencies()
        all_good = True

        for dep, installed in deps.items():
            if installed:
                version = cls.get_version(dep)
                if verbose:
                    print(f"✓ {dep} is installed: {version}")
            else:
                print(f"✗ {dep} is not installed")
                if cls.install_dependency(dep):
                    print(f"✓ Successfully installed {dep}")
                else:
                    print(f"✗ Failed to install {dep}")
                    if dep == "ffmpeg":
                        print("  Warning: Some features may not work without ffmpeg")
                    else:
                        all_good = False

        return all_good


class CookieManager:
    """Manage cookies for sites that require authentication"""

    # Sites that require cookies
    COOKIE_REQUIRED_SITES = {
        "douyin.com": "抖音",
        "tiktok.com": "TikTok",
        "bilibili.com": "B站",
        "weibo.com": "微博",
        "ixigua.com": "西瓜视频",
    }

    # Cookie storage directory
    COOKIE_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "cookies"
    )

    @classmethod
    def get_domain_from_url(cls, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            # Check for known cookie-required sites
            for site_domain in cls.COOKIE_REQUIRED_SITES:
                if site_domain in domain:
                    return site_domain
        except Exception:
            pass
        return None

    @classmethod
    def is_cookie_required(cls, url: str) -> Tuple[bool, Optional[str]]:
        """Check if URL requires cookies"""
        domain = cls.get_domain_from_url(url)
        if domain:
            return True, cls.COOKIE_REQUIRED_SITES.get(domain, domain)
        return False, None

    @classmethod
    def needs_cookie_error(cls, error_msg: str) -> bool:
        """Check if error indicates cookies are needed"""
        error_lower = error_msg.lower()
        indicators = [
            "cookies are needed",
            "fresh cookies",
            "login required",
            "authentication",
            "sign in",
            "not logged in",
        ]
        return any(indicator in error_lower for indicator in indicators)

    @classmethod
    def get_cookie_file_path(cls, domain: str) -> str:
        """Get cookie file path for a domain"""
        os.makedirs(cls.COOKIE_DIR, exist_ok=True)
        return os.path.join(cls.COOKIE_DIR, f"{domain}.txt")

    @classmethod
    def cookie_file_exists(cls, domain: str) -> bool:
        """Check if cookie file exists for domain"""
        return os.path.exists(cls.get_cookie_file_path(domain))

    @classmethod
    def get_available_browsers(cls) -> List[str]:
        """Get list of available browsers for cookie extraction"""
        browsers = []
        system = platform.system()

        if system == "Darwin":  # macOS
            browser_paths = {
                "chrome": os.path.expanduser("~/Library/Application Support/Google/Chrome/Default"),
                "chromium": os.path.expanduser("~/Library/Application Support/Chromium/Default"),
                "firefox": os.path.expanduser("~/Library/Application Support/Firefox/Profiles"),
                "safari": os.path.expanduser("~/Library/Safari"),
                "edge": os.path.expanduser("~/Library/Application Support/Microsoft Edge/Default"),
            }
        elif system == "Linux":
            browser_paths = {
                "chrome": os.path.expanduser("~/.config/google-chrome/Default"),
                "chromium": os.path.expanduser("~/.config/chromium/Default"),
                "firefox": os.path.expanduser("~/.mozilla/firefox"),
                "edge": os.path.expanduser("~/.config/microsoft-edge/Default"),
            }
        elif system == "Windows":
            browser_paths = {
                "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default"),
                "firefox": os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles"),
                "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default"),
            }
        else:
            return []

        for browser, path in browser_paths.items():
            if os.path.exists(path):
                browsers.append(browser)

        return browsers

    @classmethod
    def prompt_for_cookies(cls, url: str, site_name: str) -> Optional[str]:
        """Prompt user to provide cookies"""
        print(f"\n{'=' * 60}")
        print(f"⚠ {site_name} 需要登录才能下载此视频")
        print(f"{'=' * 60}")
        print(f"\nURL: {url}\n")

        available_browsers = cls.get_available_browsers()

        if available_browsers:
            print(f"可用浏览器: {', '.join(available_browsers)}")
            print(f"\n选项 1: 从浏览器自动获取 cookies (推荐)")
            for browser in available_browsers:
                print(f"   --cookies-from-browser {browser}")

        print(f"\n选项 2: 手动导出 cookies")
        print(f"   1. 在浏览器中访问 {site_name} 并登录")
        print(f"   2. 安装 'Get cookies.txt' 扩展")
        print(f"   3. 导出 cookies 并保存")
        print(f"   4. 使用 --cookies 指定文件路径")

        print(f"\n选项 3: 跳过此视频 (batch 模式下继续下一个)")

        return None

    @classmethod
    def get_cookie_args(cls, url: str, options: DownloadOptions) -> List[str]:
        """Get cookie-related command line arguments for yt-dlp"""
        args = []

        # Explicit cookie file takes precedence
        if options.cookies_file:
            args.extend(["--cookies", options.cookies_file])
            return args

        # Browser cookies
        if options.cookies_from_browser:
            args.extend(["--cookies-from-browser", options.cookies_from_browser])
            return args

        # Auto-detect and use saved cookie file
        domain = cls.get_domain_from_url(url)
        if domain and cls.cookie_file_exists(domain):
            cookie_file = cls.get_cookie_file_path(domain)
            args.extend(["--cookies", cookie_file])
            return args

        return args


class DouyinDownloader:
    """Helper class for Douyin URL detection"""

    # Douyin/TikTok domains
    DOMAINS = [
        "douyin.com",
        "v.douyin.com",
        "tiktok.com",
        "vt.tiktok.com",
    ]

    @classmethod
    def is_douyin_url(cls, url: str) -> bool:
        """Check if URL is from Douyin or TikTok"""
        return any(domain in url.lower() for domain in cls.DOMAINS)


class VideoInfo:
    """Information about a video"""

    def __init__(self, url: str):
        self.url = url
        self.title: Optional[str] = None
        self.duration: Optional[int] = None
        self.formats: List[Dict] = []
        self.subtitles: Dict = {}
        self.estimated_size: Optional[int] = None

    @classmethod
    def fetch(cls, url: str, verbose: bool = False) -> Optional['VideoInfo']:
        """Fetch video information using yt-dlp"""
        try:
            cmd = ["yt-dlp", "--dump-json", url]
            if verbose:
                print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if verbose:
                    print(f"Failed to fetch info: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            info = cls(url)
            info.title = data.get("title")
            info.duration = data.get("duration")
            info.formats = data.get("formats", [])
            info.subtitles = data.get("subtitles", {})

            # Estimate file size from format data
            if info.formats:
                best_format = max(
                    [f for f in info.formats if f.get("filesize")],
                    key=lambda x: x.get("filesize", 0),
                    default=None
                )
                if best_format:
                    info.estimated_size = best_format.get("filesize")

            return info

        except Exception as e:
            if verbose:
                print(f"Error fetching video info: {e}")
            return None


class ConversionEngine:
    """Handle video format conversion using ffmpeg"""

    @staticmethod
    def get_video_info(file_path: str) -> Optional[Dict]:
        """Get video codec information using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=codec_name,codec_type",
                "-show_entries", "format=format_name",
                "-of", "json",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None

    @staticmethod
    def should_convert(file_path: str) -> bool:
        """Check if video needs conversion to standard MP4"""
        info = ConversionEngine.get_video_info(file_path)
        if not info:
            return True  # Assume conversion needed if we can't check

        # Check format
        format_name = info.get("format", {}).get("format_name", "")
        is_mp4 = "mp4" in format_name

        # Check codecs
        streams = info.get("streams", [])
        video_codec = None
        audio_codec = None

        for stream in streams:
            if stream.get("codec_type") == "video":
                video_codec = stream.get("codec_name")
            elif stream.get("codec_type") == "audio":
                audio_codec = stream.get("codec_name")

        is_h264 = video_codec in ["h264", "H264"]
        is_aac = audio_codec in ["aac", "AAC"]

        # Already in desired format?
        return not (is_mp4 and is_h264 and is_aac)

    @staticmethod
    def convert_to_mp4(input_path: str, output_path: str, verbose: bool = False) -> bool:
        """Convert video to standard MP4 format"""
        try:
            cmd = [
                "ffmpeg", "-i", input_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",  # Overwrite output
                output_path
            ]

            if verbose:
                print(f"Converting: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0

        except Exception as e:
            if verbose:
                print(f"Conversion error: {e}")
            return False


class DownloadEngine:
    """Handle video downloads using yt-dlp"""

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Sanitize filename for safe filesystem use"""
        # Remove/replace problematic characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.strip()
        # Limit length
        if len(name) > 200:
            name = name[:200]
        return name

    @staticmethod
    def get_format_string(options: DownloadOptions, video_info: Optional[VideoInfo] = None) -> str:
        """Generate yt-dlp format string based on options"""
        if options.quality:
            # User-specified quality
            height = options.quality.replace("p", "")
            return f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best[height<={height}]"

        # Auto quality based on estimated file size
        if video_info and video_info.estimated_size:
            size_gb = video_info.estimated_size / (1024 ** 3)
            if size_gb > options.max_size_gb:
                # Downgrade to max 1080p for large files
                return "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]"

        # Default: best quality
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    @staticmethod
    def get_output_path(output_dir: str, title: str, ext: str = "mp4") -> str:
        """Generate output file path with date prefix and sanitized name"""
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        safe_title = DownloadEngine.sanitize_filename(title)
        filename = f"{date_prefix}_{safe_title}.{ext}"
        return os.path.join(output_dir, filename)

    @staticmethod
    def handle_file_conflict(path: str) -> str:
        """Handle filename conflicts by adding numeric suffixes"""
        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(path):
            path = f"{base} ({counter}){ext}"
            counter += 1
        return path

    @staticmethod
    def download_video(url: str, options: DownloadOptions) -> DownloadResult:
        """Download a single video"""
        result = DownloadResult(url=url)

        try:
            # Check if cookies might be needed
            needs_cookie, site_name = CookieManager.is_cookie_required(url)

            # Prepare output directory
            output_dir = PathResolver.ensure_dir(options.output_dir)

            # Build yt-dlp command
            cmd = ["yt-dlp"]

            # Add cookie arguments
            cookie_args = CookieManager.get_cookie_args(url, options)
            cmd.extend(cookie_args)

            # For initial info fetch, try with cookies
            info_cmd = cmd.copy()
            info_cmd.extend(["--dump-json", url])

            if options.verbose:
                print(f"Fetching video info...")

            result_process = subprocess.run(
                info_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Check if cookies are needed
            if result_process.returncode != 0:
                error_msg = result_process.stderr

                # For Douyin, directly inform user it's not supported
                if DouyinDownloader.is_douyin_url(url):
                    result.error = "抖音视频暂不支持下载。建议使用抖音APP内置的「保存到本地」功能，或使用浏览器扩展（如「抖音视频下载」）下载。"
                    if options.verbose:
                        print(f"\n⚠ {result.error}")
                    return result

                # Check if error indicates cookies are needed (for other sites)
                if CookieManager.needs_cookie_error(error_msg) and not options.no_cookies:
                    has_cookie_args = bool(options.cookies_from_browser or options.cookies_file)
                    if site_name and not has_cookie_args:
                        CookieManager.prompt_for_cookies(url, site_name)
                        result.error = f"{site_name} requires login cookies. Use --cookies-from-browser or --cookies"
                        result.needs_cookies = True
                        return result
                    else:
                        result.error = error_msg
                        if CookieManager.needs_cookie_error(error_msg):
                            result.needs_cookies = True
                            if has_cookie_args:
                                result.error = f"Cookies may be expired. Try re-authenticating or use a different browser."
                        return result
                else:
                    result.error = error_msg
                    return result

            # Parse video info
            try:
                data = json.loads(result_process.stdout)
            except json.JSONDecodeError:
                result.error = "Failed to parse video information"
                return result

            video_info = VideoInfo(url)
            video_info.title = data.get("title")
            video_info.duration = data.get("duration")
            video_info.formats = data.get("formats", [])
            video_info.subtitles = data.get("subtitles", {})

            # Estimate file size from format data
            if video_info.formats:
                best_format = max(
                    [f for f in video_info.formats if f.get("filesize")],
                    key=lambda x: x.get("filesize", 0),
                    default=None
                )
                if best_format:
                    video_info.estimated_size = best_format.get("filesize")

            # Build download command with format string
            format_string = DownloadEngine.get_format_string(options, video_info)
            cmd = ["yt-dlp", "-f", format_string]

            # Add cookie arguments again for download
            cmd.extend(cookie_args)

            if options.embed_subs:
                cmd.extend(["--write-subs", "--embed-subs"])

            if options.audio_only:
                cmd.extend(["-x", "--audio-format", "mp3"])
                output_template = "%(title)s.%(ext)s"
            else:
                output_template = "%(title)s.%(ext)s"

            cmd.extend(["-o", os.path.join(output_dir, output_template), url])

            if options.verbose:
                print(f"Running: {' '.join(cmd)}")

            # Run download
            result_process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes
            )

            if result_process.returncode != 0:
                result.error = result_process.stderr
                # Check again for cookie errors in download phase
                if CookieManager.needs_cookie_error(result.error or "") and not options.no_cookies:
                    result.needs_cookies = True
                return result

            # Find the downloaded file
            safe_title = DownloadEngine.sanitize_filename(video_info.title or "video")
            ext = "mp3" if options.audio_only else "mp4"
            output_file = os.path.join(output_dir, f"{safe_title}.{ext}")

            # Handle file conflicts
            output_file = DownloadEngine.handle_file_conflict(output_file)

            if not os.path.exists(output_file):
                result.error = "Download completed but file not found"
                return result

            # Handle conversion if needed
            if not options.audio_only and not options.no_convert:
                if ConversionEngine.should_convert(output_file):
                    temp_output = output_file.replace(".mp4", "_converted.mp4")
                    if ConversionEngine.convert_to_mp4(output_file, temp_output, options.verbose):
                        os.remove(output_file)
                        os.rename(temp_output, output_file)
                        result.was_converted = True
                    else:
                        result.error = "Conversion failed"
                        return result

            result.success = True
            result.output_file = output_file

        except subprocess.TimeoutExpired:
            result.error = "Download timeout"
        except Exception as e:
            result.error = str(e)

        return result

    @staticmethod
    def download_batch(urls: List[str], options: DownloadOptions) -> List[DownloadResult]:
        """Download multiple videos with error handling"""
        results = []
        failed_log = []

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")

            # Retry logic with exponential backoff
            for attempt in range(3):
                result = DownloadEngine.download_video(url, options)

                if result.success:
                    print(f"  ✓ Success: {result.output_file}")
                    if result.was_converted:
                        print(f"  ✓ Converted to standard MP4")
                    results.append(result)
                    break
                else:
                    # Check if error is retryable
                    retryable = any([
                        "timeout" in (result.error or "").lower(),
                        "network" in (result.error or "").lower(),
                        "503" in (result.error or ""),
                        "rate limit" in (result.error or "").lower(),
                    ])

                    if attempt < 2 and retryable:
                        wait_time = 2 ** attempt
                        print(f"  ⚠ Retryable error, waiting {wait_time}s... ({result.error})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ✗ Failed: {result.error}")
                        failed_log.append({"url": url, "error": result.error})
                        result.success = False
                        results.append(result)
                        break

        # Write failed log if any
        if failed_log:
            log_path = os.path.join(
                PathResolver.resolve(options.output_dir),
                "failed.log"
            )
            with open(log_path, "w") as f:
                f.write(f"Failed downloads - {datetime.now()}\n")
                f.write("=" * 50 + "\n")
                for entry in failed_log:
                    f.write(f"URL: {entry['url']}\n")
                    f.write(f"Error: {entry['error']}\n\n")
            print(f"\nFailed log saved to: {log_path}")

        return results


def print_summary(results: List[DownloadResult]):
    """Print batch download summary"""
    success = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    print("\n" + "=" * 50)
    print("Batch download complete:")
    print(f"  Success: {success} video(s)")
    print(f"  Failed: {failed} video(s)")
    print("=" * 50)


def parse_arguments() -> Tuple[Optional[str], DownloadOptions, Optional[ChannelOptions]]:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Download videos from websites using yt-dlp",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("urls", nargs="*", help="Video URL(s) to download")
    parser.add_argument("-o", "--output", default="~/Downloads/videos",
                        help="Output directory (supports natural language)")
    parser.add_argument("-a", "--audio-only", action="store_true",
                        help="Extract audio only (MP3)")
    parser.add_argument("-q", "--quality", choices=["1080p", "720p", "480p"],
                        help="Force video quality")
    parser.add_argument("-s", "--embed-subs", action="store_true", default=True,
                        help="Embed subtitles (default: True)")
    parser.add_argument("-n", "--no-convert", action="store_true",
                        help="Skip format conversion")
    parser.add_argument("-m", "--max-size", type=float, default=2.0,
                        help="Max file size in GB before quality downgrade (default: 2.0)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")

    # Cookie options
    cookie_group = parser.add_argument_group("Cookie Options")
    cookie_group.add_argument("--cookies-from-browser",
                              choices=["chrome", "firefox", "safari", "edge", "chromium", "brave"],
                              help="Load cookies from specified browser")
    cookie_group.add_argument("--cookies",
                              help="Path to cookie file (Netscape format)")
    cookie_group.add_argument("--no-cookies", action="store_true",
                              help="Skip cookie handling for sites that require login")

    # Channel download options
    channel_group = parser.add_argument_group("Channel Download")
    channel_group.add_argument("--channel", help="Channel/user homepage URL for batch download")
    channel_group.add_argument("--count", type=int, help="Download latest N videos")
    channel_group.add_argument("--parallel", type=int, default=1, help="Parallel download count")
    channel_group.add_argument("--min-views", type=int, help="Minimum view count filter")
    channel_group.add_argument("--date-after", help="Date filter (after YYYY-MM-DD)")
    channel_group.add_argument("--date-before", help="Date filter (before YYYY-MM-DD)")
    channel_group.add_argument("--resume", action="store_true", help="Resume previous task")

    args = parser.parse_args()

    options = DownloadOptions(
        output_dir=args.output,
        audio_only=args.audio_only,
        quality=args.quality,
        embed_subs=args.embed_subs,
        no_convert=args.no_convert,
        max_size_gb=args.max_size,
        verbose=args.verbose,
        cookies_from_browser=getattr(args, 'cookies_from_browser', None),
        cookies_file=getattr(args, 'cookies', None),
        no_cookies=getattr(args, 'no_cookies', False)
    )

    # Handle channel download mode
    channel_url = getattr(args, 'channel', None)
    if channel_url:
        channel_opts = ChannelOptions(
            count=getattr(args, 'count', None),
            date_after=getattr(args, 'date_after', None),
            date_before=getattr(args, 'date_before', None),
            min_views=getattr(args, 'min_views', None),
            parallel=getattr(args, 'parallel', 1),
            output_dir=args.output or "./output",
            cookies_from_browser=getattr(args, 'cookies_from_browser', None),
            cookies_file=getattr(args, 'cookies', None)
        )
        return channel_url, options, channel_opts

    # Single video download mode
    return None, options, None


def main():
    """Main entry point"""
    channel_url, options, channel_opts = parse_arguments()

    # Check dependencies
    if not DependencyManager.ensure_dependencies(options.verbose):
        print("Warning: Some dependencies are missing. Functionality may be limited.")
        if not DependencyManager.check_dependencies()["yt-dlp"]:
            print("Error: yt-dlp is required. Please install it first.")
            sys.exit(1)

    # Channel download mode
    if channel_opts is not None:
        downloader = ChannelDownloader(channel_opts)
        success = downloader.download_channel(channel_url)
        sys.exit(0 if success else 1)

    # Single video download mode (original logic)
    urls = channel_url or []  # channel_url may be None, treat as empty list
    if not urls:
        print("Error: No URLs provided. Use --channel for channel download or provide video URLs.")
        sys.exit(1)

    # Check if any URLs need cookies
    cookie_needed_urls = []
    for url in urls:
        needs_cookie, site_name = CookieManager.is_cookie_required(url)
        if needs_cookie and not options.no_cookies:
            if not options.cookies_from_browser and not options.cookies_file:
                cookie_needed_urls.append((url, site_name))

    # If cookies are needed but not provided, show help
    if cookie_needed_urls and not options.cookies_from_browser and not options.cookies_file:
        print("\n⚠ 检测到需要登录的网站:")
        for url, site_name in cookie_needed_urls:
            print(f"  - {site_name}: {url}")

        available_browsers = CookieManager.get_available_browsers()
        if available_browsers:
            print(f"\n💡 提示: 尝试使用 --cookies-from-browser {available_browsers[0]}")
        print()

    # Download
    if len(urls) == 1:
        result = DownloadEngine.download_video(urls[0], options)
        if result.success:
            print(f"\n✓ Downloaded: {result.output_file}")
            if result.was_converted:
                print("✓ Converted to standard MP4")
        else:
            print(f"\n✗ Failed: {result.error}")
            if result.needs_cookies:
                print("\n💡 此视频需要登录 cookies。请使用以下方法之一:")
                print("   --cookies-from-browser chrome  (从浏览器读取)")
                print("   --cookies /path/to/cookies.txt  (使用cookie文件)")
            sys.exit(1)
    else:
        results = DownloadEngine.download_batch(urls, options)
        print_summary(results)

        # Check if any failed due to cookies
        cookie_failed = [r for r in results if r.needs_cookies and not r.success]
        if cookie_failed:
            print("\n⚠ 以下视频需要登录 cookies:")
            for r in cookie_failed:
                needs_cookie, site_name = CookieManager.is_cookie_required(r.url)
                if site_name:
                    print(f"  - {site_name}: {r.url}")
            print("\n💡 请使用 --cookies-from-browser 或 --cookies 参数")

        if not any(r.success for r in results):
            sys.exit(1)


# ===== NEW CLASSES FOR CHANNEL DOWNLOAD =====

class ChannelExtractor:
    """从博主主页提取视频列表"""

    @staticmethod
    def detect_platform(url: str) -> Optional[str]:
        """检测平台类型"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'bilibili.com' in url:
            return 'bilibili'
        elif 'xiaohongshu.com' in url:
            return 'xhs'
        elif 'tiktok.com' in url:
            return 'tiktok'
        elif 'vimeo.com' in url:
            return 'vimeo'
        return None

    @staticmethod
    def extract_channel_youtube(url: str, verbose: bool = False) -> Tuple[ChannelInfo, List[VideoMetadata]]:
        """提取 YouTube 频道信息"""
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--flat-playlist',
            '--extractor-args', 'ignoreerrors',
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise Exception(f"Failed to extract channel info: {result.stderr}")

        videos = []
        info = None

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get('_type') == 'playlist':
                    # 频道信息
                    info = ChannelInfo(
                        platform='youtube',
                        channel_name=data.get('title') or data.get('channel'),
                        channel_url=data.get('webpage_url') or data.get('url'),
                        fan_count=data.get('fan_count'),
                        video_count=data.get('playlist_count', 0)
                    )
                elif data.get('_type') == 'video':
                    # 视频信息
                    video = VideoMetadata(
                        video_id=data.get('id'),
                        title=data.get('title'),
                        url=data.get('webpage_url') or data.get('url'),
                        duration=data.get('duration'),
                        upload_date=data.get('upload_date'),
                        view_count=data.get('view_count'),
                        like_count=data.get('like_count'),
                        comment_count=data.get('comment_count'),
                        thumbnail=data.get('thumbnail')
                    )
                    videos.append(video)
            except json.JSONDecodeError:
                continue

        if not info:
            raise Exception("No channel info found in response")

        return info, videos

    @staticmethod
    def extract_channel_bilibili(url: str, cookies_from_browser: Optional[str] = None, verbose: bool = False) -> Tuple[ChannelInfo, List[VideoMetadata]]:
        """提取 B站 UP 主信息"""
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--flat-playlist',
        ]

        # 添加 cookie 支持（如果有）
        if cookies_from_browser:
            cmd.extend(['--cookies-from-browser', cookies_from_browser])

        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise Exception(f"Failed to extract Bilibili channel info: {result.stderr}")

        videos = []
        info = None

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                if not info:
                    # B站频道信息
                    info = ChannelInfo(
                        platform='bilibili',
                        channel_name=data.get('uploader') or data.get('channel'),
                        channel_url=data.get('channel_url') or url,
                        fan_count=data.get('channel_follower_count'),
                        video_count=0  # 需要从视频列表计算
                    )
                # 视频信息
                video = VideoMetadata(
                    video_id=data.get('id'),
                    title=data.get('title'),
                    url=data.get('webpage_url') or data.get('url'),
                    duration=data.get('duration'),
                    upload_date=data.get('upload_date'),
                    view_count=data.get('view_count'),
                    like_count=data.get('like_count'),
                    comment_count=data.get('comment_count'),
                    repost_count=data.get('repost_count'),  # B站转发
                    coin_count=data.get('coin_count'),  # B站投币
                    favorite_count=data.get('favorite_count'),  # B站收藏
                    thumbnail=data.get('thumbnail')
                )
                videos.append(video)
            except json.JSONDecodeError:
                continue

        if not info:
            # 如果没有获取到频道信息，创建默认的
            info = ChannelInfo(
                platform='bilibili',
                channel_name='Bilibili UP主',
                channel_url=url,
                fan_count=None,
                video_count=len(videos)
            )
        else:
            info.video_count = len(videos)

        return info, videos

    @staticmethod
    def extract_channel_xhs(url: str, cookies_from_browser: Optional[str] = None, verbose: bool = False) -> Tuple[ChannelInfo, List[VideoMetadata]]:
        """提取小红书用户信息"""
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--flat-playlist',
        ]

        # 添加 cookie 支持（小红书需要登录）
        if cookies_from_browser:
            cmd.extend(['--cookies-from-browser', cookies_from_browser])

        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise Exception(f"Failed to extract XHS user info: {result.stderr}")

        videos = []
        info = None

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                if not info:
                    # 小红书用户信息
                    info = ChannelInfo(
                        platform='xhs',
                        channel_name=data.get('uploader') or data.get('channel'),
                        channel_url=data.get('channel_url') or url,
                        fan_count=data.get('channel_follower_count'),
                        video_count=0
                    )
                # 视频信息
                video = VideoMetadata(
                    video_id=data.get('id'),
                    title=data.get('title'),
                    url=data.get('webpage_url') or data.get('url'),
                    duration=data.get('duration'),
                    upload_date=data.get('upload_date'),
                    view_count=data.get('view_count'),
                    like_count=data.get('like_count'),
                    comment_count=data.get('comment_count'),
                    thumbnail=data.get('thumbnail')
                )
                videos.append(video)
            except json.JSONDecodeError:
                continue

        if not info:
            info = ChannelInfo(
                platform='xhs',
                channel_name='小红书用户',
                channel_url=url,
                fan_count=None,
                video_count=len(videos)
            )
        else:
            info.video_count = len(videos)

        return info, videos


class InteractiveSelector:
    """交互式选择下载范围"""

    @staticmethod
    def select_range(channel: ChannelInfo, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """交互式选择下载范围"""
        print(f"\n{'='*60}")
        print(f"博主信息:")
        print(f"  平台: {channel.platform}")
        print(f"  名称: {channel.channel_name}")
        print(f"  粉丝: {channel.fan_count or 'N/A'}")
        print(f"  总视频数: {len(videos)}")
        print(f"{'='*60}\n")

        # 显示最近5个视频预览
        print(f"最近视频预览:")
        for i, video in enumerate(videos[:5], 1):
            print(f"  [{i}] {video.title[:60]}...")

        if len(videos) > 5:
            print(f"  ... 还有 {len(videos)-5} 个视频")

        print(f"\n请选择下载方式:")
        print(f"  [1] 下载最新 N 个视频 (默认10个)")
        print(f"  [2] 下载全部视频")
        print(f"  [3] 自定义筛选")

        choice = input("\n请输入选项 [1-3]: ").strip() or "1"

        if choice == "1":
            count = int(input("下载最新几个视频？: ").strip() or "10")
            return videos[:count]
        elif choice == "2":
            return videos
        elif choice == "3":
            return InteractiveSelector._custom_filter(videos)

        return videos[:10]

    @staticmethod
    def _custom_filter(videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """自定义筛选"""
        print(f"\n自定义筛选:")

        # 日期范围
        date_after = input("起始日期 (YYYY-MM-DD, 回车跳过): ").strip()
        date_before = input("结束日期 (YYYY-MM-DD, 回车跳过): ").strip()

        # 最小播放量
        min_views = input("最小播放量 (数字, 回车跳过): ").strip()

        filtered = videos
        if date_after:
            filtered = [v for v in filtered if v.upload_date and v.upload_date >= date_after]
        if date_before:
            filtered = [v for v in filtered if v.upload_date and v.upload_date <= date_before]
        if min_views:
            filtered = [v for v in filtered if v.view_count and v.view_count >= int(min_views)]

        print(f"\n筛选结果: {len(filtered)} 个视频")
        return filtered


class AdaptiveRateLimiter:
    """自适应请求限流器"""

    def __init__(self, initial_delay: float = 3.0):
        self.current_delay = initial_delay
        self.min_delay = 1.0
        self.max_delay = 60.0
        self.success_count = 0
        self.failure_count = 0

    def wait(self):
        """等待当前延迟时间"""
        time.sleep(self.current_delay)

    def record_success(self):
        """记录成功请求，调整延迟"""
        self.success_count += 1
        self.failure_count = 0

        # 最近成功率检查
        if self.success_count > 10:
            if self.current_delay > self.min_delay:
                self.current_delay = max(self.min_delay, self.current_delay * 0.8)

    def record_failure(self, is_rate_limit: bool = False):
        """记录失败请求，增加延迟"""
        self.failure_count += 1
        self.success_count = 0

        if is_rate_limit:
            self.current_delay = min(self.max_delay, self.current_delay * 2)
        else:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)

        # 连续失败警告
        if self.failure_count >= 3:
            print(f"\n⚠ 检测到连续失败，已增加请求间隔到 {self.current_delay:.1f} 秒")

    def get_delay(self) -> float:
        """获取当前延迟"""
        return self.current_delay


class ConcurrencyController:
    """并发下载控制器"""

    def __init__(self, max_workers: int = 1):
        self.max_workers = max_workers
        self.semaphore = threading.Semaphore(max_workers)
        self.results_lock = threading.Lock()

    def download_batch(self, videos: List[VideoMetadata], download_func, options) -> List[DownloadResult]:
        """并发下载视频列表"""
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for video in videos:
                future = executor.submit(self._download_with_semaphore, download_func, video, options)
                futures[future] = video

            for future in as_completed(futures):
                result = future.result()
                with self.results_lock:
                    results.append(result)

                # 显示进度
                if hasattr(options, 'verbose') and options.verbose:
                    status = "✓" if result.success else "✗"
                    print(f"{status} [{len(results)}/{len(videos)}] {result.url}")

        return results

    def _download_with_semaphore(self, download_func, video: VideoMetadata, options) -> DownloadResult:
        """带信号量的下载"""
        self.semaphore.acquire()
        try:
            return download_func(video, options)
        finally:
            self.semaphore.release()


class DownloadStateManager:
    """下载状态管理器"""

    STATE_FILE = "download_state.json"

    def __init__(self, state_dir: str = "./output"):
        self.state_dir = state_dir
        self.state_file = os.path.join(self.state_dir, self.STATE_FILE)

    def save_state(self, state: Dict):
        """保存状态到文件"""
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def load_state(self) -> Optional[Dict]:
        """从文件加载状态"""
        if not os.path.exists(self.state_file):
            return None

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def ask_resume(self) -> bool:
        """询问用户是否恢复任务"""
        state = self.load_state()
        if not state or not state.get('channels'):
            return False

        print(f"\n发现未完成的下载任务:")
        for channel in state.get('channels', []):
            print(f"  - {channel['platform']}: {channel['channel_name']}")
            print(f"    进度: {len(channel.get('downloaded', []))}/{channel['total_videos']}")

        return input("\n是否恢复之前的任务？[y/N]: ").strip().lower() == 'y'


class CSVExporter:
    """CSV 数据导出器"""

    @staticmethod
    def export(channel: ChannelInfo, videos: List[VideoMetadata], results: List[DownloadResult], output_dir: str):
        """导出视频统计数据到 CSV"""

        csv_file = os.path.join(output_dir, f"{channel.channel_name}_videos.csv")

        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow([
                'platform', 'video_id', 'title', 'url', 'duration', 'upload_date',
                'view_count', 'like_count', 'comment_count', 'repost_count',
                'coin_count', 'favorite_count', 'thumbnail', 'download_date',
                'file_size', 'status'
            ])

            # 匹配结果和元数据
            result_map = {r.url: r for r in results}

            for video in videos:
                result = result_map.get(video.url)
                file_size = "N/A"
                status = "pending"

                if result and result.success:
                    if result.output_file and os.path.exists(result.output_file):
                        size_bytes = os.path.getsize(result.output_file)
                        file_size = f"{size_bytes / 1024 / 1024:.2f}MB"
                    status = "success"
                elif result:
                    status = "failed"

                writer.writerow([
                    channel.platform,
                    video.video_id,
                    video.title,
                    video.url,
                    video.duration or 0,
                    video.upload_date or "",
                    video.view_count or 0,
                    video.like_count or 0,
                    video.comment_count or 0,
                    video.repost_count or 0,
                    video.coin_count or 0,
                    video.favorite_count or 0,
                    video.thumbnail or "",
                    datetime.now().strftime("%Y-%m-%d"),
                    file_size,
                    status
                ])

        print(f"\n✓ CSV 文件已保存: {csv_file}")


class ReportGenerator:
    """下载报告生成器"""

    @staticmethod
    def generate(channel: ChannelInfo, videos: List[VideoMetadata], results: List[DownloadResult]):
        """生成完整下载报告"""

        success_count = sum(1 for r in results if r.success)
        failed_count = sum(1 for r in results if not r.success)

        # 计算统计数据
        total_views = sum(v.view_count or 0 for v in videos)
        total_likes = sum(v.like_count or 0 for v in videos)
        total_comments = sum(v.comment_count or 0 for v in videos)

        # 计算总文件大小
        total_size = 0
        for r in results:
            if r.success and r.output_file and os.path.exists(r.output_file):
                total_size += os.path.getsize(r.output_file)

        print(f"\n{'='*60}")
        print(f"频道下载完成报告")
        print(f"{'='*60}")
        print(f"\n博主信息:")
        print(f"  平台: {channel.platform}")
        print(f"  名称: {channel.channel_name}")
        print(f"  粉丝: {channel.fan_count or 'N/A'}")

        print(f"\n下载统计:")
        print(f"  总视频数: {len(videos)}")
        print(f"  成功下载: {success_count} 个")
        print(f"  下载失败: {failed_count} 个")
        print(f"  总文件大小: {total_size / 1024 / 1024:.2f} MB")

        print(f"\n数据汇总:")
        print(f"  总播放量: {total_views:,}")
        print(f"  总点赞数: {total_likes:,}")
        print(f"  总评论数: {total_comments:,}")

        if len(videos) > 0:
            print(f"\n  平均数据:")
            avg_duration = sum(v.duration or 0 for v in videos) / len(videos)
            avg_views = total_views / len(videos) if total_views > 0 else 0
            avg_likes = total_likes / len(videos) if total_likes > 0 else 0

            print(f"    - 平均时长: {avg_duration:.0f} 秒 ({avg_duration/60:.1f} 分钟)")
            print(f"    - 平均播放量: {avg_views:,.0f}")
            print(f"    - 平均点赞: {avg_likes:,.0f}")

        # 失败详情
        if failed_count > 0:
            print(f"\n失败详情:")
            for i, r in enumerate(results, 1):
                if not r.success:
                    print(f"  [{i}] {r.url}")
                    print(f"      错误: {r.error}")

        print(f"\n{'='*60}")


class ChannelDownloader:
    """频道下载器主控制器"""

    def __init__(self, options: ChannelOptions):
        self.options = options
        self.state_manager = DownloadStateManager(options.output_dir)
        self.limiter = AdaptiveRateLimiter()
        self.extractor = ChannelExtractor()

    def download_channel(self, channel_url: str) -> bool:
        """下载整个频道"""
        # 检测平台
        platform = self.extractor.detect_platform(channel_url)
        if not platform:
            print(f"❌ 不支持的平台: {channel_url}")
            return False

        print(f"\n检测到平台: {platform}")

        # 提取频道信息
        try:
            if platform == 'youtube':
                channel, videos = self.extractor.extract_channel_youtube(channel_url)
            elif platform == 'bilibili':
                # B站需要 cookie 支持
                cookies = getattr(self.options, 'cookies_from_browser', None) or 'chrome'
                print(f"💡 提示: B站建议使用 --cookies-from-browser {cookies}")
                channel, videos = self.extractor.extract_channel_bilibili(channel_url, cookies)
            elif platform == 'xhs':
                # 小红书需要 cookie 支持
                cookies = getattr(self.options, 'cookies_from_browser', None) or 'chrome'
                print(f"💡 提示: 小红书建议使用 --cookies-from-browser {cookies}")
                channel, videos = self.extractor.extract_channel_xhs(channel_url, cookies)
            else:
                print(f"❌ 暂不支持该平台，请先实现 {platform} 提取器")
                return False
        except Exception as e:
            print(f"❌ 提取频道信息失败: {e}")
            return False

        # 交互式选择
        selected_videos = InteractiveSelector.select_range(channel, videos)

        if not selected_videos:
            print("未选择任何视频")
            return False

        # 创建输出目录
        safe_name = self.sanitize_name(channel.channel_name)
        date_suffix = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(self.options.output_dir, platform, f"{safe_name}_{date_suffix}")
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n下载目录: {output_dir}")

        # 并发下载
        controller = ConcurrencyController(max_workers=self.options.parallel)

        def download_func(video, opts):
            self.limiter.wait()
            return self._download_single(video, opts, output_dir)

        results = controller.download_batch(selected_videos, download_func, self.options)

        # 导出 CSV
        CSVExporter.export(channel, selected_videos, results, output_dir)

        # 生成报告
        ReportGenerator.generate(channel, selected_videos, results)

        return True

    @staticmethod
    def sanitize_name(name: str) -> str:
        """清理名称用于文件夹命名"""
        # 移除文件系统非法字符
        clean = re.sub(r'[\\/*?<>|:"<>|?*]', '_', name.strip())
        # 限制长度
        if len(clean) > 100:
            clean = clean[:100]
        return clean

    def _download_single(self, video: VideoMetadata, options: ChannelOptions, output_dir: str) -> DownloadResult:
        """下载单个视频"""
        # 转换 ChannelOptions 到 DownloadOptions
        download_opts = DownloadOptions(
            output_dir=output_dir,
            verbose=False  # 可根据需要调整
        )
        # 复用现有的 DownloadEngine 逻辑
        return DownloadEngine.download_video(video.url, download_opts)


if __name__ == "__main__":
    main()
