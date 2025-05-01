import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path

LOG_PATH = Path("analytics/usage-events.jsonl")

def load_events():
    with open(LOG_PATH) as f:
        return [json.loads(line) for line in f]

def compute_time_between_sessions(events):
    # Organize events by user
    user_sessions = defaultdict(list)
    for e in events:
        try:
            ts = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
            user_sessions[e['user_id']].append(ts)
        except Exception:
            continue

    # Compute sorted session deltas
    user_gaps = {}
    for user, timestamps in user_sessions.items():
        timestamps.sort()
        if len(timestamps) < 2:
            continue
        deltas = [(t2 - t1).total_seconds() for t1, t2 in zip(timestamps, timestamps[1:])]
        user_gaps[user] = {
            "avg_gap_seconds": sum(deltas) / len(deltas),
            "last_gap_seconds": deltas[-1] if deltas else None,
            "sessions": len(timestamps)
        }
    return user_gaps

def main():
    events = load_events()
    gaps = compute_time_between_sessions(events)
    for user, data in gaps.items():
        print(f"User: {user}, Sessions: {data['sessions']}, Avg gap: {data['avg_gap_seconds']:.1f}s, Last gap: {data['last_gap_seconds']:.1f}s")

if __name__ == "__main__":
    main()