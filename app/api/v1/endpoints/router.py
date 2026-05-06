from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query
from app.services.earthquake_service import DisasterService
from app.core.database import Database

api_router = APIRouter()

@api_router.get("/disasters/live")
async def get_live_disasters():
    """
    API nội bộ: Trả về dữ liệu thiên tai đã được Server cache sẵn.
    Nhanh hơn gấp 10 lần so với gọi trực tiếp USGS/NASA.
    """
    data = DisasterService.get_latest_data()
    return {
        "source": "UPT_GUARDIAN_CACHE",
        "count": len(data),
        "data": data
    }


@api_router.get("/stats/summary")
async def get_stats_summary():
    """Dashboard: Tổng quan thống kê từ MongoDB."""
    col = Database.get_collection("raw_logs")

    # Fallback khi không có DB hoặc chưa có dữ liệu lịch sử
    live = DisasterService.get_latest_data()
    type_counts = {"QUAKE": 0, "FIRE": 0, "VOLCANO": 0, "STORM": 0, "OTHER": 0}
    for e in live:
        t = e.get("type", "")
        if "EARTHQUAKE" in t:    type_counts["QUAKE"] += 1
        elif "WILDFIRE" in t:    type_counts["FIRE"] += 1
        elif "VOLCANO" in t:     type_counts["VOLCANO"] += 1
        elif "STORM" in t:       type_counts["STORM"] += 1
        else:                    type_counts["OTHER"] += 1

    if col is None:
        return {
            "total_snapshots": 0,
            "total_events_recorded": len(live),
            "max_magnitude_ever": max((e.get("raw_val", 0) for e in live), default=0),
            "snapshots_last_24h": 0,
            "type_counts": type_counts,
            "source": "live_fallback"
        }

    try:
        cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        total_snapshots   = col.count_documents({})
        snapshots_last_24h = col.count_documents({"timestamp": {"$gte": cutoff_24h}})

        # Max magnitude ever
        best = col.find_one(
            {"max_magnitude": {"$exists": True}},
            sort=[("max_magnitude", -1)]
        )
        max_mag = round(best["max_magnitude"], 1) if best else 0

        # Total events summed across all snapshots (approximate from last 200)
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$limit": 200},
            {"$group": {"_id": None, "total": {"$sum": "$total_events"}}}
        ]
        agg = list(col.aggregate(pipeline))
        total_events = agg[0]["total"] if agg else len(live)

        return {
            "total_snapshots": total_snapshots,
            "total_events_recorded": total_events,
            "max_magnitude_ever": max_mag,
            "snapshots_last_24h": snapshots_last_24h,
            "type_counts": type_counts,
            "source": "mongodb"
        }
    except Exception as e:
        return {"error": str(e), "type_counts": type_counts, "source": "error"}


@api_router.get("/stats/trend")
async def get_stats_trend(hours: int = Query(default=24, ge=1, le=168)):
    """Dashboard: Chuỗi thời gian để vẽ biểu đồ xu hướng."""
    col = Database.get_collection("raw_logs")
    live = DisasterService.get_latest_data()

    if col is None:
        # Fallback: trả về 1 điểm dữ liệu hiện tại
        return {
            "points": [{"time": datetime.now(timezone.utc).isoformat(), "total": len(live), "max_mag": 0}],
            "source": "live_fallback"
        }

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cursor = col.find(
            {"timestamp": {"$gte": cutoff}},
            {"timestamp": 1, "total_events": 1, "max_magnitude": 1, "_id": 0}
        ).sort("timestamp", 1).limit(500)

        points = []
        for doc in cursor:
            ts = doc.get("timestamp")
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            points.append({
                "time": ts.isoformat() if ts else "",
                "total": doc.get("total_events", 0),
                "max_mag": round(doc.get("max_magnitude", 0), 1)
            })

        return {"points": points, "hours": hours, "count": len(points), "source": "mongodb"}
    except Exception as e:
        return {"error": str(e), "points": [], "source": "error"}