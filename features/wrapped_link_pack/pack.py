from __future__ import annotations

import base64
import binascii
from dataclasses import replace

from app.i18n import N
from app.models.pack import FeaturePack, TaskParser, UriScheme
from app.models.task import Task, TaskError, TaskOptions, toScheme
from .config import wrappedLinkConfig

SCHEMES = {"thunder", "flashget", "qqdl"}


def toInnerUrl(url: str) -> str:
    scheme, _, payload = url.strip().partition("://")
    payload = payload.split("&", 1)[0].rstrip("/")
    try:
        raw = base64.b64decode(payload + "=" * (-len(payload) % 4))
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("gbk")
    except (binascii.Error, UnicodeDecodeError) as e:
        raise TaskError('Unable to parse specified link') from e

    match scheme.lower():
        case "thunder":
            if not (text.startswith("AA") and text.endswith("ZZ")):
                raise TaskError('Unable to parse specified link')
            text = text[2:-2]
        case "flashget":
            text = text.removeprefix("[FLASHGET]").removesuffix("[FLASHGET]").removesuffix("[/FLASHGET]")

    innerScheme = toScheme(text)
    if innerScheme in SCHEMES:
        raise TaskError('Links wrapped in multiple layers are not supported')
    if not innerScheme:
        raise TaskError('Unable to parse specified link')
    return text.strip()


class WrappedLinkParser(TaskParser):
    priority = 10

    def match(self, options: TaskOptions) -> bool:
        return toScheme(options.url) in SCHEMES

    async def parse(self, options: TaskOptions) -> Task:
        return await self.pack.parse(replace(options, url=toInnerUrl(options.url)))


class WrappedLinkPack(FeaturePack):
    packId = "wrapped_link"
    capturedLinks = N("WrappedLinkPack", 'Thunder, FlashGet, and QQ Xuanfeng proprietary links')
    config = wrappedLinkConfig
    parsers = [WrappedLinkParser]

    def uriSchemes(self) -> list[UriScheme]:
        return [
            UriScheme("thunder", N("WrappedLinkPack", 'Thunder')),
            UriScheme("flashget", N("WrappedLinkPack", 'FlashGet')),
            UriScheme("qqdl", N("WrappedLinkPack", 'QQ Xuanfeng')),
        ]
