"""Registry các điểm nối (slot) giữa tính năng và lõi.

- Mỗi tính năng tự ĐĂNG KÝ bản mặc định của mình bằng define(slot, default). Bản mặc định là code
  hardcode của prototype, nên khi chưa nối gì thì hệ thống vẫn chạy.
- Khi tích hợp, người phụ trách gọi connect(slot, impl) ở services/engine.py. Không sửa code tính năng khác.
- get(slot) trả về bản đã nối nếu có, nếu không thì bản mặc định.

Hợp đồng (chữ ký, dữ liệu vào/ra) của từng slot: xem contracts/CONTRACTS.md.
"""
_defaults = {}
_connected = {}


def define(slot, default):
    _defaults[slot] = default


def connect(slot, impl):
    if slot not in _defaults:
        raise KeyError(f"slot chưa được định nghĩa: {slot}")
    _connected[slot] = impl


def disconnect(slot):
    _connected.pop(slot, None)


def get(slot):
    if slot in _connected:
        return _connected[slot]
    if slot in _defaults:
        return _defaults[slot]
    raise KeyError(f"slot chưa được định nghĩa: {slot}")


def status():
    """Trạng thái từng slot: 'nối' (đang dùng bản thật) hoặc 'mặc định' (hardcode prototype)."""
    return {s: ("nối" if s in _connected else "mặc định") for s in sorted(_defaults)}
