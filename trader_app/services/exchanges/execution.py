"""Execution-log helpers used by web routes and auto sender."""

import json

from trader_app.services.runtime import db, log


def record_execution_event(
    user_id=None,
    exchange_connection_id=None,
    signal_id=None,
    symbol=None,
    side=None,
    order_type=None,
    quantity=None,
    entry_expected=None,
    entry_filled=None,
    slippage=None,
    fees=None,
    exchange_order_id=None,
    status="SKIPPED",
    skip_reason=None,
    response_summary=None,
):
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO execution_log (
                user_id, exchange_connection_id, signal_id, symbol, side,
                order_type, quantity, entry_expected, entry_filled, slippage,
                fees, exchange_order_id, status, skip_reason, response_summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                exchange_connection_id,
                signal_id,
                symbol,
                side,
                order_type,
                quantity,
                entry_expected,
                entry_filled,
                slippage,
                fees,
                exchange_order_id,
                status,
                skip_reason,
                json.dumps(response_summary or {}, ensure_ascii=False)[:2000],
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        log(f"execution_log write skipped: {exc}")
        return False

