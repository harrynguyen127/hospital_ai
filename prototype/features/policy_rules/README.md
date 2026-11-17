# Tính năng 4 – Lọc policy thành rule

**Làm gì:** văn bản quy định → cắt theo khoản `x.y` → bóc luật bằng mẫu câu (regex) → kiểm tra 6 lớp → diff → chạy thử tác động → phát hành phiên bản `vN` bất biến → hoàn tác được.
**Slot:** `policy.ingest`, `policy.rollback`.
**Mặc định:** `policy.py` (regex, không gọi LLM).
**Phụ thuộc:** `shared/common.py`. Tác động theo người dùng do lõi truyền vào qua `impact_fn`, nên không cần `services/reminder`.

## Chạy test độc lập

```bash
python features/policy_rules/test_policy.py
```

## Nối bản thật

Thay bộ bóc luật (ví dụ LLM có structured output + cache). Output phải đúng dạng `rule` của `policy.py` để qua 6 lớp kiểm tra. Nối bằng:

```python
registry.connect("policy.ingest", my_ingest)
```

Dữ liệu mẫu: `data/regulations/`. Khoản mơ hồ (“khoảng”, “hoặc”, “tối đa”) → `needs_clarification`, không áp dụng.
