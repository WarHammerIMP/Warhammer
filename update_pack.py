# update_pack.py
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Any


# === НАСТРОЙКИ ПОД ТВОЙ РЕПО ===
PACK_DIR_NAME = "dynam"
CONTENT_REL_PATH = "dynam/c.json"
REPO_JSON = "dynamicmcpack.repo.json"
REPO_BUILD = "dynamicmcpack.repo.build"

# Какие файлы пропускаем (мусор ОС)
SKIP_NAMES = {
    "Thumbs.db", "desktop.ini", ".DS_Store"
}

# Для этих расширений нормализуем CRLF -> LF, чтобы SHA1 был стабильнее
TEXT_EXTS = {
    ".json", ".mcmeta", ".properties", ".txt", ".lang", ".mcfunction", ".jem", ".jpm"
}


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha1_file(path: Path) -> str:
    return sha1_bytes(path.read_bytes())


def maybe_normalize_text_file(path: Path) -> None:
    """
    Иногда из-за CRLF/LF можно ловить 'hash mismatch' при разных настройках Git/редакторов.
    Нормализуем только "текстовые" расширения и только если реально есть CRLF.
    """
    if path.suffix.lower() not in TEXT_EXTS:
        return
    raw = path.read_bytes()
    if b"\r\n" not in raw:
        return
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return
    text_norm = text.replace("\r\n", "\n")
    if text_norm != text:
        path.write_text(text_norm, encoding="utf-8")


def build_content(pack_dir: Path, remote_parent: str) -> Dict[str, Any]:
    files_map: Dict[str, Dict[str, Any]] = {}

    for p in sorted(pack_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name in SKIP_NAMES:
            continue

        # Нормализация для текстовых файлов (по желанию)
        maybe_normalize_text_file(p)

        rel = p.relative_to(pack_dir).as_posix()
        data = p.read_bytes()
        files_map[rel] = {
            "hash": sha1_bytes(data),
            "size": len(data),
        }

    return {
        "formatVersion": 1,
        "content": {
            "parent": "",
            "remote_parent": remote_parent,
            "files": files_map,
        },
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parent

    pack_dir = repo_root / PACK_DIR_NAME
    if not pack_dir.exists():
        raise SystemExit(f"Не найдена папка ресурспака: {pack_dir}")

    content_path = repo_root / CONTENT_REL_PATH
    content_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Собираем новый c.json
    content_obj = build_content(pack_dir, remote_parent=PACK_DIR_NAME)
    content_path.write_text(
        json.dumps(content_obj, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

    # 2) Считаем SHA1 именно того c.json, который будет опубликован
    content_hash = sha1_file(content_path)

    # 3) Обновляем dynamicmcpack.repo.json + build
    repo_json_path = repo_root / REPO_JSON
    repo_obj = json.loads(repo_json_path.read_text(encoding="utf-8"))

    # Берём build из repo.json (если есть), иначе из repo.build
    old_build = int(repo_obj.get("build", 0) or 0)
    build_path = repo_root / REPO_BUILD
    if old_build == 0 and build_path.exists():
        try:
            old_build = int(build_path.read_text(encoding="utf-8").strip())
        except ValueError:
            old_build = 0

    new_build = old_build + 1

    repo_obj["build"] = new_build
    if "contents" not in repo_obj or not repo_obj["contents"]:
        raise SystemExit("В dynamicmcpack.repo.json нет contents[0]. Не знаю, куда писать hash.")
    repo_obj["contents"][0]["hash"] = content_hash

    # (опционально) убедимся, что url совпадает с тем, куда мы пишем content-файл
    repo_obj["contents"][0]["url"] = CONTENT_REL_PATH.replace("\\", "/")

    repo_json_path.write_text(
        json.dumps(repo_obj, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

    # 4) Обновляем dynamicmcpack.repo.build
    build_path.write_text(str(new_build), encoding="utf-8")

    # 5) (опционально, но полезно) проставим current.build внутри пакета
    dyn_path = pack_dir / "dynamicmcpack.json"
    if dyn_path.exists():
        dyn_obj = json.loads(dyn_path.read_text(encoding="utf-8"))
        if "current" not in dyn_obj or not isinstance(dyn_obj["current"], dict):
            dyn_obj["current"] = {}
        dyn_obj["current"]["build"] = new_build
        dyn_path.write_text(
            json.dumps(dyn_obj, ensure_ascii=False, indent=4),
            encoding="utf-8"
        )

    print("✅ Готово!")
    print(f"   build: {old_build} -> {new_build}")
    print(f"   content: {CONTENT_REL_PATH}")
    print(f"   content sha1: {content_hash}")


if __name__ == "__main__":
    main()