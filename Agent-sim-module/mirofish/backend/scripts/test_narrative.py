"""Quick test of feed_narrative parsing."""
from feed_narrative import build_narrative

test1 = 'After refreshing, you see some posts [{"post_id": 1, "user_id": 5, "content": "Apple buying NeuraTech for 2B", "num_likes": 3, "num_dislikes": 0, "num_shares": 1, "num_reports": 0}]'
print("Test 1:", repr(build_narrative(test1)))

test2 = 'After refreshing, you see some posts []'
print("Test 2:", repr(build_narrative(test2)))

test3 = "After refreshing, you see some posts [{'post_id': 1, 'user_id': 5, 'content': 'Apple buying NeuraTech', 'num_likes': 0, 'num_dislikes': 0, 'num_shares': 0, 'num_reports': 0}]"
print("Test 3:", repr(build_narrative(test3)))
