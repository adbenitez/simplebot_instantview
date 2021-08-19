"""Hooks, commands and filters."""

import functools
import io
import re
from urllib.parse import quote_plus

import bs4
import requests
import simplebot
from deltachat import Message
from pkg_resources import DistributionNotFound, get_distribution
from simplebot.bot import DeltaBot, Replies

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"
session = requests.Session()
session.headers.update(
    {
        "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }
)
session.request = functools.partial(session.request, timeout=60)  # type: ignore


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    _getdefault(bot, "max_size", str(1024 ** 2 * 10))
    _getdefault(bot, "twitter_proxy", "https://twiiit.com")
    _getdefault(bot, "youtube_proxy", "https://invidious.snopyta.org")
    _getdefault(bot, "reddit_proxy", "https://teddit.net")


@simplebot.filter
def filter_links(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Send me any message containing a link/URL and I will send you back a preview of the site."""
    match = re.search(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|"
        r"(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        message.text,
    )
    if not match:
        return

    url = prepare_url(match.group(), bot)
    kwargs = dict(quote=message)

    with session.get(url, stream=True) as resp:
        resp.raise_for_status()
        url = resp.url
        content_type = resp.headers.get("content-type", "").lower()
        has_preview = "text/html" in content_type or "image/" in content_type
        max_size = int(_getdefault(bot, "max_size"))
        size = int(resp.headers.get("content-size") or -1)
        content = b""
        if size < max_size:
            size = 0
            for chunk in resp.iter_content(chunk_size=102400):
                size += len(chunk)
                if size > max_size:
                    del content
                    break
                if has_preview:
                    content += chunk
        if size > max_size or not has_preview:
            if int(resp.headers.get("content-size") or -1) == -1 and size > max_size:
                label = f">{_sizeof_fmt(max_size)}"
            else:
                label = _sizeof_fmt(size)
            ctype = resp.headers.get("content-type", "").split(";")[0] or "-"
            kwargs["text"] = f"Type: {ctype}\nSize: {label}"
        elif "text/html" in content_type:
            kwargs["text"], kwargs["html"] = prepare_html(
                bot.self_contact.addr, url, content
            )
        elif "image/" in content_type:
            kwargs["filename"] = "image." + re.search(  # type: ignore
                r"image/(\w+)", content_type
            ).group(1)
            kwargs["bytefile"] = io.BytesIO(content)

    replies.add(**kwargs)


def prepare_html(bot_addr: str, url: str, content: bytes) -> tuple:
    """Sanitize HTML.

    Returns a tuple with page title and sanitized HTML.
    """
    soup = bs4.BeautifulSoup(content, "html5lib")

    _remove_unused_tags(soup)

    # fix URLs
    index = url.find("/", 8)
    if index == -1:
        root = url
    else:
        root = url[:index]
        url = url.rsplit("/", 1)[0]
    tags = (
        ("a", "href", "mailto:"),
        ("img", "src", "data:"),
        ("source", "src", "data:"),
        ("link", "href", None),
    )
    for tag, attr, iprefix in tags:
        for element in soup(tag, attrs={attr: True}):
            if iprefix and element[attr].startswith(iprefix):
                continue
            element[attr] = re.sub(
                r"^(//.*)", r"{}:\1".format(root.split(":", 1)[0]), element[attr]
            )
            element[attr] = re.sub(r"^(/.*)", r"{}\1".format(root), element[attr])
            if not re.match(r"^https?://", element[attr]):
                element[attr] = "{}/{}".format(url, element[attr])
            if tag == "a":
                element[
                    "href"
                ] = f"mailto:{bot_addr}?body={quote_plus(element['href'])}"

    return (
        soup.title.get_text().strip() if soup.title else "Page without title",
        str(soup),
    )


def prepare_url(url: str, bot: DeltaBot) -> str:
    """Convert Twitter, YouTube and Reddit links to alternative non-JS frontends."""
    if url.startswith("https://twitter.com/"):
        return url.replace("https://twitter.com", _getdefault(bot, "twitter_proxy"), 1)
    if url.startswith("https://mobile.twitter.com/"):
        return url.replace(
            "https://mobile.twitter.com", _getdefault(bot, "twitter_proxy"), 1
        )
    if url.startswith("https://youtube.com/"):
        return url.replace("https://youtube.com", _getdefault(bot, "youtube_proxy"), 1)
    if url.startswith("https://youtu.be/"):
        return url.replace("https://youtu.be", _getdefault(bot, "youtube_proxy"), 1)
    if url.startswith("https://www.reddit.com/"):
        return url.replace(
            "https://www.reddit.com", _getdefault(bot, "reddit_proxy"), 1
        )

    return url


def _remove_unused_tags(soup: bs4.BeautifulSoup) -> None:
    for tag in soup("script"):
        tag.extract()
    for tag in soup(["button", "input"]):
        if tag.has_attr("type") and tag["type"] == "hidden":
            tag.extract()
    for tag in soup.find_all(text=lambda text: isinstance(text, bs4.Comment)):
        tag.extract()


def _getdefault(bot: DeltaBot, key: str, value: str = None) -> str:
    val = bot.get(key, scope=__name__)
    if val is None and value is not None:
        bot.set(key, value, scope=__name__)
        val = value
    return val


def _sizeof_fmt(num: float) -> str:
    suffix = "B"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


class TestPlugin:
    """Offline tests"""

    def test_filter(self, mocker, requests_mock) -> None:
        msgs = mocker.get_replies("Hello world")
        assert not msgs

        requests_mock.get(
            "https://html.example.org",
            text="html body",
            headers={"Content-Type": "text/html"},
        )
        msg = mocker.get_one_reply("check out https://html.example.org it is nice")
        assert msg.has_html()
        assert "html body" in msg.html

        requests_mock.get("https://binary.example.org", content=b"data")
        msg = mocker.get_one_reply("check out https://binary.example.org it is nice")
        assert not msg.has_html()
        assert msg.text
