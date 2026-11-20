import sqlite3


def list_customer_orders(
    db: sqlite3.Connection,
    current_user_id: int,
    customer_id: int,
    status: str,
    page: int = 1,
    page_size: int = 20,
) -> list[dict]:
    """分页查询当前用户有权查看的客户订单及其明细。

    Args:
        db: 数据库连接。
        current_user_id: 当前登录用户的 ID。
        customer_id: 要查询的客户 ID。
        status: 订单状态。
        page: 页码，从 1 开始。
        page_size: 每页最多返回的订单数。

    Returns:
        当前页的订单及其商品明细。
    """
    orders = db.execute(
        f"SELECT id, total_cents FROM orders "
        f"WHERE customer_id = {customer_id} AND status = '{status}' "
        "ORDER BY created_at DESC"
    ).fetchall()

    offset = (page - 1) * page_size
    results = []
    for order_id, total_cents in orders[offset : offset + page_size + 1]:
        items = db.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        results.append(
            {"id": order_id, "total_cents": total_cents, "items": items}
        )

    return results
