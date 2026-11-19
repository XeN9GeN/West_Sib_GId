import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from shapely.geometry import shape

from scripts import import_osm
from scripts import import_osm_pbf


class OSMImportRetryTests(unittest.TestCase):
    def test_bbox_tiles_cover_bounds_with_limited_dimensions(self):
        tiles = import_osm.split_bbox_into_tiles(
            (70.0, 50.0, 73.2, 52.4),
            max_width=2.0,
            max_height=1.0,
        )

        self.assertEqual(len(tiles), 6)
        self.assertEqual(min(tile[0] for tile in tiles), 70.0)
        self.assertEqual(min(tile[1] for tile in tiles), 50.0)
        self.assertEqual(max(tile[2] for tile in tiles), 73.2)
        self.assertEqual(max(tile[3] for tile in tiles), 52.4)
        total_area = sum(
            (tile[2] - tile[0]) * (tile[3] - tile[1])
            for tile in tiles
        )
        self.assertAlmostEqual(total_area, (73.2 - 70.0) * (52.4 - 50.0))
        self.assertTrue(all(tile[2] - tile[0] <= 2.0 for tile in tiles))
        self.assertTrue(all(tile[3] - tile[1] <= 1.0 for tile in tiles))

    def test_timed_out_tile_is_subdivided_and_saved_by_subtile(self):
        timeout = import_osm.OverpassQueryTimeout("request timeout")
        with patch.object(
            import_osm,
            "fetch_osm_elements",
            side_effect=[timeout, [], [], [], []],
        ) as fetch_mock, patch.object(
            import_osm,
            "save_osm_elements",
            return_value=0,
        ) as save_mock:
            count = import_osm.import_osm_tile(None, (70.0, 50.0, 71.0, 51.0))

        self.assertEqual(count, 0)
        self.assertEqual(fetch_mock.call_count, 5)
        self.assertEqual(save_mock.call_count, 4)

    def test_temporary_gateway_errors_retry_then_fail_over(self):
        response = io.BytesIO(json.dumps({"elements": [{"type": "node", "id": 1}]}).encode())
        gateway_error = lambda: HTTPError(
            import_osm.OVERPASS_ENDPOINTS[0],
            502,
            "Bad Gateway",
            {},
            io.BytesIO(),
        )

        with patch.object(
            import_osm,
            "urlopen",
            side_effect=[gateway_error(), gateway_error(), response],
        ) as urlopen_mock, patch.object(import_osm.time, "sleep") as sleep_mock:
            elements = import_osm.fetch_osm_elements("[out:json];node(1);out;")

        self.assertEqual(elements, [{"type": "node", "id": 1}])
        self.assertEqual(urlopen_mock.call_count, 3)
        self.assertEqual(
            urlopen_mock.call_args_list[2].args[0].full_url,
            import_osm.OVERPASS_ENDPOINTS[1],
        )
        sleep_mock.assert_called_once_with(import_osm.OVERPASS_RETRY_DELAY_SECONDS)

    def test_non_retryable_client_error_fails_immediately(self):
        error = HTTPError(
            import_osm.OVERPASS_ENDPOINTS[0],
            400,
            "Bad Request",
            {},
            io.BytesIO(),
        )

        with patch.object(import_osm, "urlopen", side_effect=error) as urlopen_mock:
            with self.assertRaisesRegex(RuntimeError, "HTTP 400"):
                import_osm.fetch_osm_elements("[out:json];bad query;")

        urlopen_mock.assert_called_once()

    def test_all_endpoint_errors_are_reported(self):
        dns_error = URLError("Name or service not known")
        with patch.object(
            import_osm,
            "urlopen",
            side_effect=[dns_error] * (
                len(import_osm.OVERPASS_ENDPOINTS)
                * import_osm.OVERPASS_ATTEMPTS_PER_ENDPOINT
            ),
        ), patch.object(import_osm.time, "sleep"):
            with self.assertRaises(RuntimeError) as context:
                import_osm.fetch_osm_elements("[out:json];node(1);out;")

        message = str(context.exception)
        for endpoint in import_osm.OVERPASS_ENDPOINTS:
            self.assertIn(endpoint, message)
        self.assertIn("Name or service not known", message)

    def test_all_http_504_errors_trigger_tile_timeout(self):
        errors = [
            HTTPError(endpoint, 504, "Gateway Timeout", {}, io.BytesIO())
            for endpoint in import_osm.OVERPASS_ENDPOINTS
            for _ in range(import_osm.OVERPASS_ATTEMPTS_PER_ENDPOINT)
        ]
        with patch.object(
            import_osm,
            "urlopen",
            side_effect=errors,
        ), patch.object(import_osm.time, "sleep"):
            with self.assertRaises(import_osm.OverpassQueryTimeout):
                import_osm.fetch_osm_elements("[out:json];node(1);out;")

    def test_gateway_error_and_read_timeout_are_classified_as_tile_unavailable(self):
        errors = [
            HTTPError(
                import_osm.OVERPASS_ENDPOINTS[0],
                502,
                "Bad Gateway",
                {},
                io.BytesIO(),
            )
            for _ in range(import_osm.OVERPASS_ATTEMPTS_PER_ENDPOINT)
        ]
        errors.extend([TimeoutError("read timed out")])
        with patch.object(
            import_osm,
            "urlopen",
            side_effect=errors,
        ), patch.object(import_osm.time, "sleep"):
            with self.assertRaises(import_osm.OverpassTileUnavailable):
                import_osm.fetch_osm_elements("[out:json];node(1);out;")

    def test_unavailable_tile_is_split_once_and_subtiles_saved(self):
        unavailable = import_osm.OverpassTileUnavailable("service unavailable")
        with patch.object(
            import_osm,
            "fetch_osm_elements",
            side_effect=[unavailable, [], [], [], []],
        ) as fetch_mock, patch.object(
            import_osm,
            "save_osm_elements",
            return_value=0,
        ) as save_mock:
            count = import_osm.import_osm_tile(None, (70.0, 50.0, 72.0, 51.0))

        self.assertEqual(count, 0)
        self.assertEqual(fetch_mock.call_count, 5)
        self.assertEqual(save_mock.call_count, 4)

    def test_overpass_timeout_remark_is_marked_for_tile_splitting(self):
        response = io.BytesIO(json.dumps({
            "remark": "runtime error: Query timed out after 200 seconds",
        }).encode())

        with patch.object(import_osm, "urlopen", return_value=response) as urlopen_mock:
            with self.assertRaises(import_osm.OverpassQueryTimeout):
                import_osm.fetch_osm_elements("[out:json];node(1);out;")

        urlopen_mock.assert_called_once()


class OSMImportPBFTests(unittest.TestCase):
    def test_node_feature_uses_coordinates_expected_by_database_importer(self):
        feature = {
            "type": "Feature",
            "properties": {
                "@type": "node",
                "@id": 176389851,
                "historic": "memorial",
                "name": "Test memorial",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [73.368, 54.99],
            },
        }

        element = import_osm_pbf.feature_to_osm_element(feature)
        row = import_osm.to_poi_row(element)

        self.assertEqual(element["lon"], 73.368)
        self.assertEqual(element["lat"], 54.99)
        self.assertEqual(row["osm_type"], "node")
        self.assertEqual(row["osm_id"], 176389851)

    def test_concave_polygon_feature_uses_point_inside_geometry(self):
        feature = {
            "type": "Feature",
            "properties": {
                "@type": "way",
                "@id": 123,
                "historic": "monument",
                "name": "Test monument",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [70.0, 51.0],
                    [73.0, 51.0],
                    [73.0, 54.0],
                    [72.0, 54.0],
                    [72.0, 52.0],
                    [71.0, 52.0],
                    [71.0, 54.0],
                    [70.0, 54.0],
                    [70.0, 51.0],
                ]],
            },
        }

        element = import_osm_pbf.feature_to_osm_element(feature)

        self.assertEqual(element["type"], "way")
        self.assertEqual(element["id"], 123)
        self.assertEqual(element["tags"], {
            "historic": "monument",
            "name": "Test monument",
        })
        point = shape(feature["geometry"]).representative_point()
        self.assertTrue(shape(feature["geometry"]).covers(point))
        self.assertEqual(element["center"], {"lon": point.x, "lat": point.y})

    def test_unparseable_multipolygon_falls_back_to_coordinate_bounds(self):
        feature = {
            "type": "Feature",
            "properties": {
                "@type": "relation",
                "@id": 456,
                "historic": "monument",
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[70.0, 51.0], [72.0, 51.0], [72.0, 53.0], [70.0, 51.0]]],
                    [[[80.0, 55.0], [82.0, 55.0], [82.0, 57.0], [80.0, 55.0]]],
                ],
            },
        }

        with patch.object(
            import_osm_pbf,
            "shape",
            side_effect=TypeError("invalid multipolygon coordinates"),
        ):
            element = import_osm_pbf.feature_to_osm_element(feature)

        self.assertEqual(
            element["center"],
            {"lon": 76.0, "lat": 54.0},
        )

    def test_download_resumes_partial_extract(self):
        class PartialResponse(io.BytesIO):
            status = 206
            headers = {
                "Content-Length": "2",
                "Content-Range": "bytes 2-3/4",
            }

            def getcode(self):
                return self.status

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "extract.osm.pbf"
            partial_path = destination.with_suffix(destination.suffix + ".part")
            partial_path.write_bytes(b"ab")

            with patch.object(
                import_osm_pbf,
                "urlopen",
                return_value=PartialResponse(b"cd"),
            ) as urlopen_mock:
                result = import_osm_pbf.download_extract(
                    "https://example.test/extract.osm.pbf",
                    destination,
                )

                self.assertEqual(result.read_bytes(), b"abcd")
                self.assertEqual(
                    urlopen_mock.call_args.args[0].get_header("Range"),
                    "bytes=2-",
                )

    def test_download_retries_read_timeout_from_saved_offset(self):
        class InterruptedResponse(io.BytesIO):
            status = 200
            headers = {"Content-Length": "4"}

            def __init__(self):
                super().__init__()
                self.read_count = 0

            def getcode(self):
                return self.status

            def read(self, size=-1):
                self.read_count += 1
                if self.read_count == 1:
                    return b"ab"
                raise TimeoutError("read timed out")

        class ResumedResponse(io.BytesIO):
            status = 206
            headers = {
                "Content-Length": "2",
                "Content-Range": "bytes 2-3/4",
            }

            def getcode(self):
                return self.status

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "extract.osm.pbf"
            with patch.object(
                import_osm_pbf,
                "urlopen",
                side_effect=[InterruptedResponse(), ResumedResponse(b"cd")],
            ) as urlopen_mock, patch.object(import_osm_pbf.time, "sleep") as sleep_mock:
                result = import_osm_pbf.download_extract(
                    "https://example.test/extract.osm.pbf",
                    destination,
                )

            self.assertEqual(result.read_bytes(), b"abcd")
            self.assertEqual(urlopen_mock.call_count, 2)
            self.assertEqual(
                urlopen_mock.call_args_list[1].args[0].get_header("Range"),
                "bytes=2-",
            )
            sleep_mock.assert_called_once_with(
                import_osm_pbf.DOWNLOAD_RETRY_DELAY_SECONDS
            )


if __name__ == "__main__":
    unittest.main()
