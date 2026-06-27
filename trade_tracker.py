import json
import os
from datetime import datetime

TRACK_FILE = "trades.json"


# ================= LOAD =================
def load_trades():
    if not os.path.exists(TRACK_FILE):
        return []
    try:
        with open(TRACK_FILE, "r") as f:
            return json.load(f)
    except:
        return []


# ================= SAVE =================
def save_trades(trades):
    try:
        with open(TRACK_FILE, "w") as f:
            json.dump(trades, f, indent=2)
    except Exception as e:
        print(f"save_trades error: {e}")


# ================= ADD =================
def add_trade(signal):
    try:
        trades = load_trades()

        trade = {
            "pair": signal["pair"],
            "direction": signal["direction"],
            "entry": float(signal["entry"]),
            "tp": float(signal["tp"]),
            "sl": float(signal["sl"]),
            "confidence": float(signal["confidence"]),
            "rr": float(signal.get("risk_reward", signal.get("rr", 0))),
            "market_regime": signal.get("market_regime"),
            "setup_type": signal.get("setup_type"),
            "final_score": signal.get("final_score"),
            "support": signal.get("support"),
            "resistance": signal.get("resistance"),
            "status": "OPEN",
            "pnl": 0,
            "sent_result": False,
            "created_at": datetime.utcnow().isoformat()
        }

        trades.append(trade)
        save_trades(trades)

    except Exception as e:
        print(f"Tracker add_trade error: {e}")


# ================= PNL =================
def calculate_pnl(trade, price):
    try:
        entry = float(trade["entry"])
        direction = trade["direction"]

        if entry <= 0:
            return 0

        if direction == "LONG":
            return round(((price - entry) / entry) * 100, 2)

        elif direction == "SHORT":
            return round(((entry - price) / entry) * 100, 2)

        return 0
    except:
        return 0


# ================= UPDATE =================
def update_trades(get_price_func):
    try:
        trades = load_trades()
        updated = False

        for trade in trades:
            if trade["status"] != "OPEN":
                continue

            price = get_price_func(trade["pair"])

            if not price:
                continue

            # ================= LONG =================
            if trade["direction"] == "LONG":

                if price >= trade["tp"]:
                    trade["status"] = "TP"
                    trade["close_reason"] = "TP Hit"
                    trade["closed_at"] = datetime.utcnow().isoformat()
                    trade["pnl"] = calculate_pnl(trade, trade["tp"])
                    updated = True
                    if not trade.get("sent_result"):
                        from auto_sender import notify_trade_result
                        notify_trade_result(trade)
                        trade["sent_result"] = True

                elif price <= trade["sl"]:
                    trade["status"] = "SL"
                    trade["close_reason"] = "SL Hit"
                    trade["closed_at"] = datetime.utcnow().isoformat()
                    trade["pnl"] = calculate_pnl(trade, trade["sl"])
                    updated = True
                    if not trade.get("sent_result"):
                       from auto_sender import notify_trade_result
                       notify_trade_result(trade)
                       trade["sent_result"] = True

            # ================= SHORT =================
            elif trade["direction"] == "SHORT":

                if price <= trade["tp"]:
                    trade["status"] = "TP"
                    trade["close_reason"] = "TP Hit"
                    trade["closed_at"] = datetime.utcnow().isoformat()
                    trade["pnl"] = calculate_pnl(trade, trade["tp"])
                    updated = True
                    if not trade.get("sent_result"):
                       from auto_sender import notify_trade_result
                       notify_trade_result(trade)
                       trade["sent_result"] = True
                elif price >= trade["sl"]:
                    trade["status"] = "SL"
                    trade["close_reason"] = "SL Hit"
                    trade["closed_at"] = datetime.utcnow().isoformat()
                    trade["pnl"] = calculate_pnl(trade, trade["sl"])
                    updated = True
                    if not trade.get("sent_result"):
                       from auto_sender import notify_trade_result
                       notify_trade_result(trade)
                       trade["sent_result"] = True

        if updated:
            save_trades(trades)

    except Exception as e:
        print(f"Tracker update error: {e}")


# ================= STATS =================
def get_stats():
    trades = load_trades()

    wins = [t for t in trades if t["status"] == "TP"]
    losses = [t for t in trades if t["status"] == "SL"]

    total_closed = len(wins) + len(losses)

    total_pnl = sum(t.get("pnl", 0) for t in trades)

    if total_closed == 0:
        return {
            "win_rate": 0,
            "total_trades": len(trades),
            "closed_trades": 0,
            "total_pnl_%": 0
        }

    return {
        "win_rate": round((len(wins) / total_closed) * 100, 2),
        "total_trades": len(trades),
        "closed_trades": total_closed,
        "total_pnl_%": round(total_pnl, 2)
    }