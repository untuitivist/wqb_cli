from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..core.community_client import CommunityClient, load_community_registry, prepare_community_request
from ..core.community_publish import image_file, materialize_images, plan_images, upload_image, verify_post_page
from ..core.io import parse_key_values, read_json_file, write_json
from ..core.registry import EndpointRegistry


def add_community_parser(subparsers: argparse._SubParsersAction) -> None:
    community = subparsers.add_parser("community", help="Online BRAIN forum API; local data uses sqlitecom")
    community_sub = community.add_subparsers(dest="community_command", required=True)
    routes = {
        "list": ("GET", "/api/v2/community/posts.json", (), "List online posts, newest first"),
        "topics": ("GET", "/api/v2/community/topics.json", (), "List accessible forum sections"),
        "topic": ("GET", "/api/v2/community/topics/{topic_id}.json", ("topic_id",), "Read a forum section"),
        "get": ("GET", "/api/v2/community/posts/{post_id}.json", ("post_id",), "Read a post and its HTML"),
        "comments": ("GET", "/api/v2/community/posts/{post_id}/comments.json", ("post_id",), "Read a page of comments"),
        "search": ("GET", "/api/v2/help_center/community_posts/search.json", ("query",), "Search online posts; offline search is sqlitecom search"),
        "user-posts": ("GET", "/api/v2/community/users/{user_id}/posts.json", ("user_id",), "List a user's posts; me is supported"),
        "user-comments": ("GET", "/api/v2/community/users/{user_id}/comments.json", ("user_id",), "List a user's comments"),
        "create": ("POST", "/api/v2/community/posts.json", (), "Publish a post from HTML or JSON, including local images"),
        "update": ("PUT", "/api/v2/community/posts/{post_id}.json", ("post_id",), "Update a post from HTML or JSON"),
        "delete": ("DELETE", "/api/v2/community/posts/{post_id}.json", ("post_id",), "Explicitly delete a post"),
        "comment-create": ("POST", "/api/v2/community/posts/{post_id}/comments.json", ("post_id",), "Explicitly publish a comment from JSON"),
        "comment-update": ("PUT", "/api/v2/community/posts/{post_id}/comments/{comment_id}.json", ("post_id", "comment_id"), "Explicitly update a comment"),
        "comment-delete": ("DELETE", "/api/v2/community/posts/{post_id}/comments/{comment_id}.json", ("post_id", "comment_id"), "Explicitly delete a comment"),
    }
    for name, (method, path, variables, help_text) in routes.items():
        command = community_sub.add_parser(name, help=help_text)
        command.set_defaults(community_method=method, community_path=path)
        for variable in variables:
            command.add_argument(variable)
        if method == "GET":
            command.add_argument("--page", type=int, default=1)
            command.add_argument("--limit", type=int, default=25, help="Results per page; next-page links are preserved")
        if name in {"list", "search", "user-posts"}:
            command.add_argument("--sort", choices=["created_at", "updated_at", "recent_activity", "votes", "comments"], default="created_at")
            command.add_argument("--order", choices=["asc", "desc"], default="desc")
        if name in {"list", "search"}:
            command.add_argument("--topic", dest="section_id", help="Forum section ID")
        if method in {"POST", "PUT"}:
            body = command.add_mutually_exclusive_group(required=True)
            body.add_argument("--input", help="JSON request body file")
            body.add_argument("--json", help="Inline JSON request body")
            if name in {"create", "update"}:
                body.add_argument("--html", help="UTF-8 HTML file; uploads local images from its directory")
                command.add_argument("--title", help="Post title; required with create --html")
                command.add_argument("--topic", dest="post_topic", type=int, help="Forum section ID; required with create --html")
                command.add_argument("--notify-subscribers", action="store_true", help="Notify subscribers when publishing an HTML file")
                command.add_argument("--upload-images", action="store_true", help="Upload local images referenced by a JSON input")
                command.add_argument("--assets-manifest", help="Durable image receipts; defaults beside the HTML/JSON input")
                command.add_argument("--prepared-output", help="Write the exact JSON body with uploaded image paths before sending")
        _request_options(command)
    image = community_sub.add_parser("image-upload", help="Upload one image and return its forum image path")
    image.add_argument("file", help="PNG, JPEG, GIF or WebP image, at most 2 MB")
    _request_options(image)
    api = community_sub.add_parser("api", help="Inspect the forum API inventory or issue a raw request")
    api_sub = api.add_subparsers(dest="community_api_command", required=True)
    for name in ("stats", "list", "show", "params", "call"):
        command = api_sub.add_parser(name)
        if name in {"show", "params", "call"}:
            if name == "call":
                command.add_argument("method")
            command.add_argument("path")
        if name == "call":
            command.add_argument("--var", action="append")
            command.add_argument("--input", help="JSON containing path_vars, params and json")
            command.add_argument("--json")
            _request_options(command)
        else:
            command.add_argument("--output")


def _request_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", dest="config_path", help="BRAIN authentication configuration")
    parser.add_argument("--param", action="append", help="Query parameter KEY=VALUE")
    parser.add_argument("--dry-run", action="store_true", help="Preview without authentication or HTTP")
    parser.add_argument("--max-wait-seconds", type=float, default=300, help="Read retry sleep budget; writes are never retried")
    parser.add_argument("--output", help="Write JSON result to file")


def handle_community(args: argparse.Namespace) -> int:
    import json

    if args.community_command == "image-upload":
        path = Path(args.file).resolve()
        metadata, content = image_file(path)
        if args.dry_run:
            write_json({"ok": True, "dry_run": True, "image": metadata, "mutating": True}, args.output)
        else:
            write_json({"ok": True, "image": upload_image(_client(args), path)}, args.output)
        return 0
    registry = load_community_registry()
    params: dict[str, Any] = {}
    variables: dict[str, Any] = {}
    json_body = None
    if args.community_command == "api":
        operation = args.community_api_command
        if operation != "call":
            if operation == "stats":
                result = registry.stats()
            elif operation == "list":
                result = [endpoint.raw for endpoint in registry.list()]
            else:
                endpoint = registry.get(args.path)
                result = endpoint.raw if operation == "show" else {"path": endpoint.path, "variables": endpoint.variables, "params": endpoint.params, "request_body": endpoint.request_body}
            write_json(result, args.output)
            return 0
        payload = read_json_file(args.input)
        variables.update(payload.get("path_vars") or {})
        variables.update(parse_key_values(args.var))
        params.update(payload.get("params") or {})
        json_body = payload.get("json")
        method, path = args.method, args.path
    else:
        method, path = args.community_method, args.community_path
        for name in registry.get(path).variables:
            variables[name] = getattr(args, name)
        if method == "GET":
            if not 1 <= args.limit <= 100 or args.page < 1:
                raise ValueError("limit must be 1..100 and page must be positive")
            params.update({"per_page": args.limit, "page": args.page, "include": "users,topics"})
        if hasattr(args, "sort"):
            if args.community_command == "search" and args.sort not in {"created_at", "updated_at"}:
                raise ValueError("Online search supports only created_at or updated_at sorting")
            params.update({"sort_by": args.sort, "sort_order": args.order})
        if args.community_command == "search":
            params["query"] = args.query
            if args.section_id:
                params["topic"] = args.section_id
        elif args.community_command == "list" and args.section_id:
            path = "/api/v2/community/topics/{topic_id}/posts.json"
            variables["topic_id"] = args.section_id
        if getattr(args, "input", None):
            json_body = read_json_file(args.input)
    if getattr(args, "json", None):
        json_body = json.loads(args.json)
    html_path = getattr(args, "html", None)
    if html_path:
        if args.community_command == "create" and (not args.title or not args.post_topic):
            raise ValueError("create --html requires --title and --topic")
        json_body = {"post": {"details": Path(html_path).read_text(encoding="utf-8")}}
        if args.title:
            json_body["post"]["title"] = args.title
        if args.post_topic:
            json_body["post"]["topic_id"] = args.post_topic
        if args.community_command == "create":
            json_body["notify_subscribers"] = args.notify_subscribers
    params.update(parse_key_values(args.param))
    prepared = prepare_community_request(registry, method, path, path_vars=variables, params=params, json_body=json_body)
    image_plan = []
    post = json_body.get("post") if isinstance(json_body, dict) else None
    prepare_images = args.community_command in {"create", "update"} and isinstance(post, dict) and isinstance(post.get("details"), str)
    if prepare_images:
        source_path = Path(html_path or getattr(args, "input", None) or "community-post.json").resolve()
        upload_local = bool(html_path or args.upload_images)
        parsed, image_plan, replacements = plan_images(post["details"], source_path.parent, upload_local=upload_local)
    if args.dry_run:
        write_json({"ok": True, "dry_run": True, "request": prepared, "images": image_plan}, args.output)
        return 0
    client = _client(args)
    uploaded = []
    if prepare_images:
        manifest = Path(args.assets_manifest) if args.assets_manifest else source_path.with_name(source_path.name + ".assets.json")
        post["details"], uploaded = materialize_images(client, post["details"], source_path.parent, manifest, upload_local=upload_local)
    if getattr(args, "prepared_output", None):
        write_json(json_body, args.prepared_output)
    result = client.call(prepared["method"], prepared["url"], params=prepared["params"], json_body=prepared["json"])
    if prepare_images:
        result["images"] = uploaded
        saved = (result["response"].get("body") or {}).get("post") or {}
        if result["ok"] and saved.get("id"):
            try:
                result["verification"] = client.call("GET", f"/api/v2/community/posts/{saved['id']}.json")
            except Exception as error:
                result["verification"] = {"ok": False, "error_type": type(error).__name__,
                                          "message": "The post was saved; retry only its GET to verify publication."}
            if not result["verification"].get("ok") and saved.get("html_url"):
                try:
                    result["page_verification"] = verify_post_page(client, saved)
                except Exception as error:
                    result["page_verification"] = {"ok": False, "error_type": type(error).__name__,
                                                    "message": "The post was saved; inspect its page without creating another post."}
    write_json(result, args.output)
    return 0 if result["ok"] else 1


def _client(args: argparse.Namespace) -> CommunityClient:
    return CommunityClient(cookies_path=args.cookies, config_path=args.config_path,
                           brain_registry=EndpointRegistry.load(args.registry), max_wait_seconds=args.max_wait_seconds)
