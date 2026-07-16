from core.geo import haversine_distance


class TestHaversine:
    def test_same_point_zero_distance(self):
        dist = haversine_distance(19.0760, 72.8777, 19.0760, 72.8777)
        assert dist == 0.0

    def test_mumbai_to_delhi(self):
        dist = haversine_distance(19.0760, 72.8777, 28.6139, 77.2090)
        assert 1100 < dist < 1500

    def test_nyc_to_la(self):
        dist = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3900 < dist < 4000

    def test_london_to_tokyo(self):
        dist = haversine_distance(51.5074, -0.1278, 35.6762, 139.6503)
        assert 9500 < dist < 9600

    def test_returns_float(self):
        dist = haversine_distance(0, 0, 10, 10)
        assert isinstance(dist, float)

    def test_small_distance_reasonable(self):
        dist = haversine_distance(19.0760, 72.8777, 19.0860, 72.8877)
        assert 0 < dist < 10
