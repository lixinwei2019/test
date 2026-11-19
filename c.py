import sqlite3


def list_customer_orders(
    db: sqlite3.Connection,
    current_user_id: int,
    customer_id: int,
    status: str,
    page: int = 1,
    page_size: int = 20,
) -> list[dict]:
    """分页查询当前用户所属客户的订单及其明细。

    Args:
        db: 数据库连接，客户归属通过 customers.user_id 关联用户。
        current_user_id: 从登录会话获取的当前用户 ID。
        customer_id: 要查询的客户 ID。
        status: 订单状态。
        page: 页码，从 1 开始。
        page_size: 每页最多返回的订单数，必须大于零。

    Returns:
        当前页的订单及其商品明细，无权访问或没有订单时返回空列表。

    Raises:
        ValueError: 页码或每页订单数小于 1。
    """
    if page < 1 or page_size < 1:
        raise ValueError("page 和 page_size 必须大于等于 1")

    offset = (page - 1) * page_size

    # 先对有权查看的订单分页，再关联明细，避免明细数量影响订单分页。
    rows = db.execute(
        """
        WITH page_orders AS (
            SELECT o.id, o.total_cents, o.created_at
            FROM orders AS o
            JOIN customers AS c ON c.id = o.customer_id
            WHERE c.user_id = ? AND o.customer_id = ? AND o.status = ?
            ORDER BY o.created_at DESC, o.id DESC
            LIMIT ? OFFSET ?
        )
        SELECT p.id, p.total_cents, i.product_id, i.quantity
        FROM page_orders AS p
        LEFT JOIN order_items AS i ON i.order_id = p.id
        ORDER BY p.created_at DESC, p.id DESC, i.product_id
        """,
        (current_user_id, customer_id, status, page_size, offset),
    ).fetchall()

    orders_by_id = {}
    for order_id, total_cents, product_id, quantity in rows:
        if order_id not in orders_by_id:
            orders_by_id[order_id] = {
                "id": order_id,
                "total_cents": total_cents,
                "items": [],
            }

        # LEFT JOIN 保留没有明细的订单，空关联不能生成虚假的商品条目。
        if product_id is not None:
            orders_by_id[order_id]["items"].append((product_id, quantity))

    return list(orders_by_id.values())
