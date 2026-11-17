"""Lưu trạng thái prototype trong một file JSON (đủ cho demo, không dùng cho production).

Ghi chú: mọi thay đổi chạy trong `transaction()`: làm việc trên bản sao, chỉ commit khi
không có exception. Thư mục runtime đặt được bằng biến môi trường PROTO_RUNTIME_DIR (dùng cho test).
"""
import copy
import datetime as dt
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from .common import fingerprint

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RUNTIME_DIR = Path(os.environ.get("PROTO_RUNTIME_DIR", ROOT / ".runtime"))
STATE_FILE = RUNTIME_DIR / "state.json"
DEFAULT_NOW = "2026-11-16T10:00:00+07:00"

_lock = threading.RLock()
_cache = None


def _seed_state():
    raw_forms = json.loads((DATA_DIR / "form_registry" / "forms.json").read_text(encoding="utf-8"))
    forms = {}
    for fid, f in raw_forms.items():
        forms[fid] = {
            "form_id": fid, **f, "status": "active", "version": 1,
            "fingerprint": fingerprint(f["title"], f["fields"]), "history": [],
        }
    pdata = json.loads((DATA_DIR / "patients_mock" / "patients.json").read_text(encoding="utf-8"))
    return {
        "clock": DEFAULT_NOW, "forms": forms, "users": pdata["users"],
        "patients": pdata["patients"], "records": pdata["records"],
        "rulesets": [], "docs": {}, "audit": [],
    }


def _write(state):
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _load():
    global _cache
    if _cache is None:
        if STATE_FILE.exists():
            _cache = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        else:
            _cache = _seed_state()
            _write(_cache)
    return _cache


@contextmanager
def transaction():
    global _cache
    with _lock:
        work = copy.deepcopy(_load())
        yield work
        _cache = work
        _write(work)


def read():
    with _lock:
        return copy.deepcopy(_load())


def reset():
    global _cache
    with _lock:
        _cache = None
        if STATE_FILE.exists():
            STATE_FILE.unlink()


def now(state):
    return dt.datetime.fromisoformat(state["clock"])


def audit(state, kind, detail):
    state["audit"].append({
        "id": len(state["audit"]) + 1, "at": state["clock"], "kind": kind, "detail": detail,
    })
