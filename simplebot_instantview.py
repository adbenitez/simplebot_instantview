"""Hooks, commands and filters."""

import functools
import io
import re

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
    _getdefault(bot, "nitter_instance", "https://nitter.cc")
    _getdefault(bot, "invidious_instance", "https://invidious.snopyta.org")
    _getdefault(bot, "teddit_instance", "https://teddit.net")


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

    url = _prepare_url(match.group(), bot)
    kwargs = dict(quote=message)

    with session.get(url, stream=True) as resp:
        resp.raise_for_status()
        url = resp.url
        max_size = int(_getdefault(bot, "max_size"))
        size = int(resp.headers.get("content-size") or -1)
        if size < max_size:
            size = 0
            for chunk in resp.iter_content(chunk_size=102400):
                size += len(chunk)
                if size > max_size:
                    break
        content_type = resp.headers.get("content-type", "").lower()
        if size > max_size or (
            "text/html" not in content_type and "image/" not in content_type
        ):
            if int(resp.headers.get("content-size") or -1) == -1 and size > max_size:
                label = f">{_sizeof_fmt(max_size)}"
            else:
                label = _sizeof_fmt(size)
            ctype = resp.headers.get("content-type", "").split(";")[0] or "-"
            kwargs["text"] = f"Type: {ctype}\nSize: {label}"
        elif "text/html" in content_type:
            kwargs["text"], kwargs["html"] = _prepare_html(url, resp.text)
        elif "image/" in content_type:
            kwargs["filename"] = "image." + re.search(  # type: ignore
                r"image/(\w+)", content_type
            ).group(1)
            kwargs["bytefile"] = io.BytesIO(resp.content)

    replies.add(**kwargs)


def _prepare_html(url: str, html: str) -> tuple:
    soup = bs4.BeautifulSoup(html, "html5lib")
    for tag in soup("script"):
        tag.extract()
    if soup.title:
        text = soup.title.get_text().strip()
    else:
        text = "Page without title"
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

    return text, str(soup)


def _prepare_url(url: str, bot: DeltaBot) -> str:
    if url.startswith("https://twitter.com/"):
        return url.replace(
            "https://twitter.com", _getdefault(bot, "nitter_instance"), count=1
        )
    if url.startswith("https://mobile.twitter.com/"):
        return url.replace(
            "https://mobile.twitter.com", _getdefault(bot, "nitter_instance"), count=1
        )
    if url.startswith("https://youtube.com/"):
        return url.replace(
            "https://youtube.com", _getdefault(bot, "invidious_instance"), count=1
        )
    if url.startswith("https://youtu.be/"):
        return url.replace(
            "https://youtu.be", _getdefault(bot, "invidious_instance"), count=1
        )
    if url.startswith("https://www.reddit.com/"):
        return url.replace(
            "https://www.reddit.com", _getdefault(bot, "teddit_instance"), count=1
        )

    return url


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
        requests_mock.get("https://fsf.org", text="html body")

        msgs = mocker.get_replies("Hello world")
        assert not msgs

        msg = mocker.get_one_reply("check out https://fsf.org it is nice")
        assert msg.has_html()
        assert msg.html == "html body"
