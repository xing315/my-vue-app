import pytest

from app.publisher import SupabasePublisher


def test_preview_snapshot_cannot_be_published():
    publisher = SupabasePublisher("https://example.supabase.co", "test-key")
    with pytest.raises(ValueError, match="live"):
        publisher.publish({"mode": "preview", "stocks": []})


def test_small_snapshot_cannot_be_published():
    publisher = SupabasePublisher("https://example.supabase.co", "test-key")
    with pytest.raises(ValueError, match="覆盖数"):
        publisher.publish({"mode": "live", "updatedAt": "2026-08-02T16:45:00+08:00", "stocks": []})
