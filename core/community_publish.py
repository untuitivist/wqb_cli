from __future__ import annotations

import hashlib
import json
import re
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

import requests

from .community_client import CommunityClient, CommunityError, SUPPORT_ORIGIN


MAX_IMAGE_BYTES = 2_000_000
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
ATTRIBUTES = re.compile(r"""([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""")


class PostPage(HTMLParser):
    def __init__(self, body: str, *, fragment: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.body_depth = 0
        self.body_count = 0
        self.title_depth = 0
        self.body_text: list[str] = []
        self.titles: list[str] = []
        self.images: list[str] = []
        self.feed('<div class="post-body">' + body + "</div>" if fragment else body)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self.body_depth:
            if tag not in VOID_TAGS:
                self.body_depth += 1
        elif "post-body" in (attributes.get("class") or "").split():
            self.body_depth = 1
            self.body_count += 1
        if tag == "h1":
            self.title_depth = 1
            self.titles.append("")
        elif self.title_depth and tag not in VOID_TAGS:
            self.title_depth += 1
        if self.body_depth and tag == "img":
            self.images.append(urljoin(SUPPORT_ORIGIN, attributes.get("src") or ""))

    def handle_endtag(self, tag: str) -> None:
        if tag not in VOID_TAGS:
            self.body_depth = max(0, self.body_depth - 1)
            self.title_depth = max(0, self.title_depth - 1)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.body_depth:
            self.body_text.append(data)
        if self.title_depth:
            self.titles[-1] += data


def verify_post_page(client: CommunityClient, post: dict[str, Any]) -> dict[str, Any]:
    reply = client.post_page(post["html_url"], str(post["id"]))
    result = {"ok": False, "source": "html", "url": post["html_url"], "http_status": reply.status_code}
    if reply.status_code != 200:
        return result
    actual = PostPage(reply.text)
    expected = PostPage(post["details"], fragment=True)
    normalized = lambda value: re.sub(r"\s+", "", value)
    result.update({"title_matches": normalized(post["title"]) in [normalized(title) for title in actual.titles],
                   "body_matches": actual.body_count == 1 and normalized("".join(actual.body_text)) == normalized("".join(expected.body_text)),
                   "images_match": actual.images == expected.images})
    result["ok"] = result["title_matches"] and result["body_matches"] and result["images_match"]
    return result


def image_file(path: Path) -> tuple[dict[str, Any], bytes]:
    content = path.read_bytes()
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Community images must contain 1..2000000 bytes: " + str(path))
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"
    elif content.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
    elif content.startswith((b"GIF87a", b"GIF89a")):
        content_type = "image/gif"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        content_type = "image/webp"
    else:
        raise ValueError("Unsupported community image; use PNG, JPEG, GIF or WebP: " + str(path))
    return {"file": str(path), "content_type": content_type, "file_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest()}, content


def upload_image(client: CommunityClient, path: Path) -> dict[str, Any]:
    metadata, content = image_file(path)
    context = client.write_context()
    created = client.call("POST", "/api/v2/guide/user_images/uploads",
                          json_body={"content_type": metadata["content_type"], "file_size": len(content)})
    if not created["ok"]:
        raise CommunityError(f"Image upload preparation failed (HTTP {created['response']['status_code']})")
    upload = created["response"]["body"]["upload"]
    target = urlsplit(upload["url"])
    hostname = target.hostname or ""
    if (target.scheme != "https" or target.port not in (None, 443) or target.username or target.password or target.fragment
            or not (hostname.endswith(".amazonaws.com") or hostname in {"support.worldquantbrain.com", "worldquantbrain.zendesk.com"})):
        raise CommunityError("The forum returned an unexpected image upload destination")
    headers = upload.get("headers") or {}
    if any(name.lower() in {"authorization", "cookie", "host"} or "\r" in str(value) or "\n" in str(value)
           for name, value in headers.items()):
        raise CommunityError("The forum returned unexpected image upload headers")
    transfer = requests.Session()
    transfer.trust_env = client.session.trust_env
    try:
        transferred = transfer.put(upload["url"], data=content, headers=headers, timeout=client.timeout, allow_redirects=False)
    except requests.RequestException as error:
        raise CommunityError("Image byte upload outcome is unknown: " + type(error).__name__) from None
    finally:
        transfer.close()
    if not 200 <= transferred.status_code < 300:
        raise CommunityError(f"Image byte upload failed (HTTP {transferred.status_code})")
    registered = client.call("POST", "/api/v2/guide/user_images",
                             json_body={"token": upload["token"], "brand_id": context["brand_id"]})
    if not registered["ok"]:
        raise CommunityError(f"Image registration failed (HTTP {registered['response']['status_code']})")
    image = registered["response"]["body"]["user_image"]
    image_path = image.get("path", "")
    if not image_path.startswith("/hc/user_images/") or urlsplit(image_path).query or ".." in image_path.split("/"):
        raise CommunityError("The forum returned an unexpected public image path")
    return {**metadata, "path": image_path, "url": urljoin(SUPPORT_ORIGIN, image_path), "brand_id": context["brand_id"],
            "http_status": registered["response"]["status_code"]}


class HtmlImages(HTMLParser):
    def __init__(self, body: str) -> None:
        super().__init__(convert_charrefs=True)
        self.body = body
        self.sources: list[str] = []
        self.references: list[tuple[int, int, str]] = []
        self.offsets = [0]
        for line in body.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.feed(body)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in {"img", "a"}:
            return
        if tag == "img":
            source = dict(attrs).get("src")
            if not source or "srcset" in dict(attrs):
                raise ValueError("Each post image needs one src URL; srcset is not supported")
            self.sources.append(source)
        line, column = self.getpos()
        offset = self.offsets[line - 1] + column
        for match in ATTRIBUTES.finditer(self.get_starttag_text()):
            if match.group(1).lower() != ("src" if tag == "img" else "href"):
                continue
            group = next(index for index in (2, 3, 4) if match.group(index) is not None)
            self.references.append((offset + match.start(group), offset + match.end(group), unescape(match.group(group))))

    handle_startendtag = handle_starttag

    def rewrite(self, replacements: dict[str, str]) -> str:
        body = self.body
        for start, end, source in reversed(self.references):
            if source in replacements:
                body = body[:start] + escape(replacements[source], quote=True) + body[end:]
        return body


def plan_images(body: str, base_directory: Path, *, upload_local: bool) -> tuple[HtmlImages, list[dict[str, Any]], dict[str, str]]:
    parsed = HtmlImages(body)
    images = []
    replacements = {}
    root = base_directory.resolve()
    for source in dict.fromkeys(parsed.sources):
        address = urlsplit(source)
        if source.startswith("/hc/user_images/") and not address.netloc and ".." not in address.path.split("/"):
            continue
        if address.scheme == "https" and address.netloc == "support.worldquantbrain.com" and address.path.startswith("/hc/user_images/"):
            replacements[source] = address.path
            continue
        if address.scheme or address.netloc or address.path.startswith("/"):
            raise ValueError("Post images must be local files or registered /hc/user_images/ URLs: " + source)
        if not upload_local:
            raise ValueError("Local post images require --html or --upload-images")
        path = (root / unquote(address.path)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("A local post image is outside the HTML/input directory: " + source)
        metadata, content = image_file(path)
        images.append({"source": source, **metadata})
    return parsed, images, replacements


def materialize_images(client: CommunityClient, body: str, base_directory: Path, manifest_path: Path, *, upload_local: bool) -> tuple[str, list[dict[str, Any]]]:
    parsed, images, replacements = plan_images(body, base_directory, upload_local=upload_local)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"version": 1, "images": {}}
    if manifest.get("version") != 1 or not isinstance(manifest.get("images"), dict):
        raise ValueError("Unsupported image manifest")
    used = []
    for metadata in images:
        image = manifest["images"].get(metadata["sha256"])
        if image:
            if image.get("sha256") != metadata["sha256"] or not str(image.get("path", "")).startswith("/hc/user_images/"):
                raise ValueError("Invalid cached image receipt")
        else:
            image = upload_image(client, Path(metadata["file"]))
            manifest["images"][metadata["sha256"]] = image
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = manifest_path.with_name(manifest_path.name + ".tmp")
            temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(manifest_path)
        replacements[metadata["source"]] = image["path"]
        used.append(image)
    return parsed.rewrite(replacements), used
