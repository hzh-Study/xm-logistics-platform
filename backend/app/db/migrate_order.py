"""运输订单发布迁移（v5）：在既有 orders 表上追加货物 / 快照 / 要求 / 报价列。"""

import sqlite3

# orders 是可变业务实体，只做追加列；发货 / 收货快照发布后由触发器锁定不可改写。
_ORDER_SCHEMA = [
    "-- 货物类型\nALTER TABLE orders ADD COLUMN cargo_type TEXT NOT NULL DEFAULT ''",
    "-- 货物数量描述\nALTER TABLE orders ADD COLUMN quantity TEXT NOT NULL DEFAULT ''",
    "-- 货物重量描述\nALTER TABLE orders ADD COLUMN weight TEXT NOT NULL DEFAULT ''",
    "-- 货物体积描述\nALTER TABLE orders ADD COLUMN volume TEXT NOT NULL DEFAULT ''",
    "-- 包装方式\nALTER TABLE orders ADD COLUMN packaging TEXT NOT NULL DEFAULT ''",
    "-- 货物照片相对路径 JSON 数组\nALTER TABLE orders ADD COLUMN cargo_photos TEXT NOT NULL DEFAULT '[]'",
    "-- 货物备注\nALTER TABLE orders ADD COLUMN cargo_remarks TEXT NOT NULL DEFAULT ''",
    "-- 发货来源：仓库/临时地址\nALTER TABLE orders ADD COLUMN ship_source TEXT NOT NULL DEFAULT '临时地址' CHECK(ship_source IN ('仓库','临时地址'))",
    "-- 发货来源仓库 id，临时地址为空\nALTER TABLE orders ADD COLUMN ship_warehouse_id INTEGER",
    "-- 发货快照：地点名称\nALTER TABLE orders ADD COLUMN ship_name TEXT NOT NULL DEFAULT ''",
    "-- 发货快照：联系人\nALTER TABLE orders ADD COLUMN ship_contact TEXT NOT NULL DEFAULT ''",
    "-- 发货快照：联系电话\nALTER TABLE orders ADD COLUMN ship_phone TEXT NOT NULL DEFAULT ''",
    "-- 发货快照：省份\nALTER TABLE orders ADD COLUMN ship_province TEXT NOT NULL DEFAULT ''",
    "-- 发货快照：城市\nALTER TABLE orders ADD COLUMN ship_city TEXT NOT NULL DEFAULT ''",
    "-- 发货快照：区县\nALTER TABLE orders ADD COLUMN ship_district TEXT NOT NULL DEFAULT ''",
    "-- 发货快照：详细地址\nALTER TABLE orders ADD COLUMN ship_detail_address TEXT NOT NULL DEFAULT ''",
    "-- 发货快照：地点类型\nALTER TABLE orders ADD COLUMN ship_type TEXT NOT NULL DEFAULT ''",
    "-- 收货快照：地点名称\nALTER TABLE orders ADD COLUMN recv_name TEXT NOT NULL DEFAULT ''",
    "-- 收货快照：联系人\nALTER TABLE orders ADD COLUMN recv_contact TEXT NOT NULL DEFAULT ''",
    "-- 收货快照：联系电话\nALTER TABLE orders ADD COLUMN recv_phone TEXT NOT NULL DEFAULT ''",
    "-- 收货快照：省份\nALTER TABLE orders ADD COLUMN recv_province TEXT NOT NULL DEFAULT ''",
    "-- 收货快照：城市\nALTER TABLE orders ADD COLUMN recv_city TEXT NOT NULL DEFAULT ''",
    "-- 收货快照：区县\nALTER TABLE orders ADD COLUMN recv_district TEXT NOT NULL DEFAULT ''",
    "-- 收货快照：详细地址\nALTER TABLE orders ADD COLUMN recv_detail_address TEXT NOT NULL DEFAULT ''",
    "-- 车型要求\nALTER TABLE orders ADD COLUMN vehicle_type TEXT NOT NULL DEFAULT ''",
    "-- 车长要求\nALTER TABLE orders ADD COLUMN vehicle_length TEXT NOT NULL DEFAULT ''",
    "-- 载重要求\nALTER TABLE orders ADD COLUMN load_requirement TEXT NOT NULL DEFAULT ''",
    "-- 冷链要求：0/1\nALTER TABLE orders ADD COLUMN cold_chain INTEGER NOT NULL DEFAULT 0 CHECK(cold_chain IN (0,1))",
    "-- 防雨要求：0/1\nALTER TABLE orders ADD COLUMN rain_protection INTEGER NOT NULL DEFAULT 0 CHECK(rain_protection IN (0,1))",
    "-- 厢式车身要求：0/1\nALTER TABLE orders ADD COLUMN enclosed_body INTEGER NOT NULL DEFAULT 0 CHECK(enclosed_body IN (0,1))",
    "-- 特殊装载要求：0/1\nALTER TABLE orders ADD COLUMN special_loading INTEGER NOT NULL DEFAULT 0 CHECK(special_loading IN (0,1))",
    "-- 其他服务要求\nALTER TABLE orders ADD COLUMN other_services TEXT NOT NULL DEFAULT ''",
    "-- 运输要求备注\nALTER TABLE orders ADD COLUMN transport_remarks TEXT NOT NULL DEFAULT ''",
    "-- 运费报价方式：固定/可协商/其他\nALTER TABLE orders ADD COLUMN quote_method TEXT NOT NULL DEFAULT '可协商' CHECK(quote_method IN ('固定','可协商','其他'))",
    "-- 运费报价金额，单位：分\nALTER TABLE orders ADD COLUMN quote_amount_cents INTEGER NOT NULL DEFAULT 0",
    "-- 接受议价展示标记：0/1，V1 无议价流程\nALTER TABLE orders ADD COLUMN accept_bargain INTEGER NOT NULL DEFAULT 0 CHECK(accept_bargain IN (0,1))",
    "-- 运费报价备注（其他方式说明）\nALTER TABLE orders ADD COLUMN quote_remarks TEXT NOT NULL DEFAULT ''",
    "CREATE INDEX IF NOT EXISTS idx_orders_shipper_status ON orders(shipper_id, status, id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_shipper_created ON orders(shipper_id, created_at, id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_shipper_cargo ON orders(shipper_id, cargo_name, id)",
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_snapshot_immutable
    BEFORE UPDATE ON orders
    WHEN NEW.ship_source IS NOT OLD.ship_source
      OR NEW.ship_warehouse_id IS NOT OLD.ship_warehouse_id
      OR NEW.ship_name IS NOT OLD.ship_name
      OR NEW.ship_contact IS NOT OLD.ship_contact
      OR NEW.ship_phone IS NOT OLD.ship_phone
      OR NEW.ship_province IS NOT OLD.ship_province
      OR NEW.ship_city IS NOT OLD.ship_city
      OR NEW.ship_district IS NOT OLD.ship_district
      OR NEW.ship_detail_address IS NOT OLD.ship_detail_address
      OR NEW.ship_type IS NOT OLD.ship_type
      OR NEW.recv_name IS NOT OLD.recv_name
      OR NEW.recv_contact IS NOT OLD.recv_contact
      OR NEW.recv_phone IS NOT OLD.recv_phone
      OR NEW.recv_province IS NOT OLD.recv_province
      OR NEW.recv_city IS NOT OLD.recv_city
      OR NEW.recv_district IS NOT OLD.recv_district
      OR NEW.recv_detail_address IS NOT OLD.recv_detail_address
    BEGIN SELECT RAISE(ABORT, 'shipping/receiving snapshot is immutable'); END
    """,
]


def migrate_order(conn: sqlite3.Connection) -> None:
    """在已开启的事务内追加订单发布字段并锁定快照。"""
    for statement in _ORDER_SCHEMA:
        conn.execute(statement)
